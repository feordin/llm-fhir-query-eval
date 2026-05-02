"""
One-shot populator for data/code_augmentations.json.

For every Synthea module (synthea/modules/custom/phekb_*.json), find the
matching PheKB raw dir, read document_analysis.json's extracted_codes, and
for each SNOMED code emitted by the module, propose ICD-9/ICD-10/CPT/etc.
crosswalks where the PheKB-listed display name matches semantically.

Heuristic: token overlap >= 0.4 AND no conflicting modifier (e.g.,
"ruptured" vs "without rupture" disagreement disqualifies a match).

Output is conservative — review before running augment_fhir_codes.py
against bundles. Existing entries in code_augmentations.json are merged,
not overwritten (so manual additions survive re-runs).

Usage:
  python scripts/build_code_augmentations.py
  python scripts/build_code_augmentations.py --phenotype abdominal-aortic-aneurysm
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
MODULES = REPO / "synthea" / "modules" / "custom"
PHEKB_RAW = REPO / "data" / "phekb-raw"
OUT = REPO / "data" / "code_augmentations.json"

sys.path.insert(0, str(REPO / "scripts"))
from audit_phenotypes_vs_phekb import EXPLICIT_ALIASES  # noqa: E402

SYSTEM_URI = {
    "ICD-10-CM": "http://hl7.org/fhir/sid/icd-10-cm",
    "ICD-9-CM": "http://hl7.org/fhir/sid/icd-9-cm",
    "CPT": "http://www.ama-assn.org/go/cpt",
    "HCPCS": "http://www.ama-assn.org/go/hcpcs",
    "RxNorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "LOINC": "http://loinc.org",
    "SNOMED CT": "http://snomed.info/sct",
}

# These tokens disambiguate clinical concepts. If one display has the token
# and the other doesn't, they're describing different things and shouldn't match.
DISAMBIGUATING_MODIFIERS = [
    "ruptured", "rupture",
    "without", "with",
    "unspecified",
    "open", "endovascular", "laparoscopic", "percutaneous",
    "left", "right", "bilateral",
    "acute", "chronic",
    "primary", "secondary",
    "mild", "moderate", "severe",
    "type 1", "type 2",
    "stage 1", "stage 2", "stage 3", "stage 4",
    "drug-induced",
    "alcoholic", "non-alcoholic",
]

STOPWORDS = {"of", "the", "a", "an", "and", "or", "to", "in", "by", "for", "with", "on"}


def tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower())) - STOPWORDS


def has_modifier_conflict(d1: str, d2: str) -> bool:
    t1, t2 = d1.lower(), d2.lower()
    for mod in DISAMBIGUATING_MODIFIERS:
        if (mod in t1) != (mod in t2):
            return True
    return False


def score_match(snomed_display: str, candidate_display: str) -> float:
    t1 = tokens(snomed_display)
    t2 = tokens(candidate_display)
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / max(len(t1), len(t2))


def get_phekb_dir(slug_name: str) -> Path | None:
    if slug_name in EXPLICIT_ALIASES:
        target = EXPLICIT_ALIASES[slug_name]
        if target is None:
            return None
        d = PHEKB_RAW / target
        return d if d.is_dir() else None
    d = PHEKB_RAW / slug_name
    return d if d.is_dir() else None


def extract_module_codes(mod_path: Path) -> list[tuple[str, str, str]]:
    """Returns list of (system_label, code, display) for codes in the module."""
    text = mod_path.read_text(encoding="utf-8")
    pattern = (
        r'"system":\s*"([^"]+)"\s*,\s*'
        r'"code":\s*"([^"]+)"\s*,\s*'
        r'"display":\s*"([^"]+)"'
    )
    return re.findall(pattern, text)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--phenotype", help="Limit to a single phenotype slug")
    p.add_argument("--threshold", type=float, default=0.4, help="Min token overlap (default 0.4)")
    args = p.parse_args()

    # Load existing map (preserve manual edits)
    existing: dict[str, list[dict]] = {}
    if OUT.exists():
        with OUT.open(encoding="utf-8") as f:
            existing = json.load(f)
    crosswalk: dict[str, list[dict]] = {k: list(v) for k, v in existing.items()}

    target_slug = args.phenotype
    per_phenotype_added: dict[str, int] = defaultdict(int)

    for mod_path in sorted(MODULES.glob("phekb_*.json")):
        if "_control" in mod_path.stem:
            continue
        slug = mod_path.stem.replace("phekb_", "").replace("_", "-")
        if target_slug and slug != target_slug:
            continue
        phekb_dir = get_phekb_dir(slug)
        if not phekb_dir:
            continue
        analysis = phekb_dir / "document_analysis.json"
        if not analysis.exists():
            continue
        with analysis.open(encoding="utf-8") as f:
            doc = json.load(f)
        phekb_codes = doc.get("extracted_codes", [])
        if not phekb_codes:
            continue

        # Bucket PheKB doc codes by system
        by_system: dict[str, list[dict]] = defaultdict(list)
        for c in phekb_codes:
            sysname = c.get("system", "")
            if sysname in ("SNOMED CT", "SNOMED-CT"):
                continue
            by_system[sysname].append(c)

        module_codes = extract_module_codes(mod_path)
        snomed_codes = [(code, display) for sys_lbl, code, display in module_codes
                        if sys_lbl in ("SNOMED-CT", "SNOMED CT")]

        for snomed_code, snomed_display in snomed_codes:
            for system, candidates in by_system.items():
                ranked = []
                for c in candidates:
                    cand_display = c.get("display", "")
                    if has_modifier_conflict(snomed_display, cand_display):
                        continue
                    score = score_match(snomed_display, cand_display)
                    if score >= args.threshold:
                        ranked.append((score, c))
                ranked.sort(key=lambda x: -x[0])
                if not ranked:
                    continue
                best = ranked[0][1]
                sys_uri = SYSTEM_URI.get(system, system)
                entry = {"system": sys_uri, "code": best["code"], "display": best["display"]}
                bucket = crosswalk.setdefault(snomed_code, [])
                if not any(e["system"] == entry["system"] and e["code"] == entry["code"] for e in bucket):
                    bucket.append(entry)
                    per_phenotype_added[slug] += 1

    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(crosswalk, f, indent=2)
    print(f"Wrote {OUT}")
    print(f"SNOMED keys total: {len(crosswalk)}")
    print(f"Total crosswalk entries: {sum(len(v) for v in crosswalk.values())}")
    if per_phenotype_added:
        print(f"\nPhenotypes contributing new entries this run:")
        for slug, n in sorted(per_phenotype_added.items(), key=lambda x: -x[1]):
            print(f"  {slug}: +{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
