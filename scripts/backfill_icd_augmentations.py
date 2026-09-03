"""Backfill SNOMED->ICD entries in code_augmentations.json via UMLS crosswalk.

Why: ~40 phenotypes' test cases carry only SNOMED codes, so the offline MIMIC
gold (mimic_phenotype_counts / recompute_mimic_gold) finds zero patients for
them -- MIMIC Conditions are ICD-9/ICD-10 only. This script crosswalks each
phenotype's Condition-context SNOMED codes to ICD-10-CM and ICD-9-CM using the
UMLS REST crosswalk (UMLS verified, no guessing) and appends the results to
data/code_augmentations.json additively.

Only test cases whose expected_query targets the Condition resource contribute
SNOMED codes; negation cases are skipped (they reference the EXCLUDED cohort).

Usage:
    python scripts/backfill_icd_augmentations.py [--phenotypes p1 p2 ...] [--dry-run]

Requires UMLS_API_KEY (env or .env). Idempotent: SNOMED codes that already
have an ICD entry in the augmentations file are skipped.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TEST_CASES = REPO / "test-cases" / "phekb"
AUGMENTATIONS = REPO / "data" / "code_augmentations.json"
REPORT = REPO / "data" / "icd_backfill_report.json"
UMLS_BASE = "https://uts-ws.nlm.nih.gov/rest"

ICD_SYSTEMS = {
    "ICD10CM": "http://hl7.org/fhir/sid/icd-10-cm",
    "ICD9CM": "http://hl7.org/fhir/sid/icd-9-cm",
}
SNOMED = "http://snomed.info/sct"

sys.path.insert(0, str(REPO / "scripts"))
from mimic_phenotype_counts import PHENOTYPES, _valid_icd  # noqa: E402


def collect_condition_snomed(phenotype: str) -> dict:
    """{snomed_code: display} from the phenotype's Condition-query test cases."""
    out: dict = {}
    for fn in sorted(glob.glob(str(TEST_CASES / f"phekb-{phenotype}-*.json")) +
                     glob.glob(str(TEST_CASES / f"phekb-{phenotype}.json"))):
        d = json.load(open(fn, encoding="utf-8"))
        meta = d.get("metadata", {}) or {}
        if meta.get("negation"):
            continue
        eq = d.get("expected_query") or {}
        if eq.get("resource_type") != "Condition":
            continue
        for rc in meta.get("required_codes", []) or []:
            if SNOMED in rc.get("system", "") and rc.get("code"):
                out[str(rc["code"])] = rc.get("display", "")
    return out


def _load_api_key() -> str:
    key = os.environ.get("UMLS_API_KEY")
    if not key:
        env = REPO / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("UMLS_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        sys.exit("UMLS_API_KEY not found in environment or .env")
    return key


def crosswalk(snomed_code: str, target: str, api_key: str) -> list:
    """UMLS crosswalk SNOMEDCT_US -> target vocabulary. Returns [(code, name)]."""
    url = (f"{UMLS_BASE}/crosswalk/current/source/SNOMEDCT_US/"
           f"{urllib.parse.quote(snomed_code)}?"
           f"targetSource={target}&pageSize=200&apiKey={api_key}")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:  # no mapping exists
            return []
        raise
    seen, out = set(), []
    for item in body.get("result", []):
        code, name = item.get("ui", ""), item.get("name", "")
        if code and code not in seen:
            seen.add(code)
            out.append((code, name))
    return out


def has_icd_entry(entries: list) -> bool:
    return any("icd-10-cm" in e.get("system", "") or "icd-9-cm" in e.get("system", "")
               for e in entries)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phenotypes", nargs="*", default=PHENOTYPES)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.15)
    args = ap.parse_args(argv)

    api_key = _load_api_key()
    aug = json.load(AUGMENTATIONS.open(encoding="utf-8"))
    report, n_calls, n_added = {}, 0, 0

    for ph in args.phenotypes:
        snomeds = collect_condition_snomed(ph)
        if not snomeds:
            continue
        ph_rows = []
        for code, display in snomeds.items():
            if has_icd_entry(aug.get(code, [])):
                continue  # already crosswalked
            row = {"snomed": code, "display": display, "icd10cm": [], "icd9cm": []}
            for target, system in ICD_SYSTEMS.items():
                results = crosswalk(code, target, api_key)
                n_calls += 1
                time.sleep(args.sleep)
                key = "icd10cm" if target == "ICD10CM" else "icd9cm"
                for icd, name in results:
                    if not _valid_icd(key, icd):  # range notation, proc codes
                        continue
                    row[key].append(icd)
                    aug.setdefault(code, []).append(
                        {"system": system, "code": icd, "display": name})
                    n_added += 1
            ph_rows.append(row)
        if ph_rows:
            report[ph] = ph_rows

    print(f"{n_calls} UMLS calls, {n_added} ICD entries added")
    for ph, rows in report.items():
        for r in rows:
            print(f"  {ph:34s} {r['snomed']:>12s} {r['display'][:32]:32s} "
                  f"icd10={','.join(r['icd10cm']) or '-'} icd9={','.join(r['icd9cm']) or '-'}")
    if args.dry_run:
        print("(dry run: nothing written)")
        return 0
    json.dump(aug, AUGMENTATIONS.open("w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    json.dump(report, REPORT.open("w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"wrote {AUGMENTATIONS} and {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
