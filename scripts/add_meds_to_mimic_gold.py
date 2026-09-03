"""Add the medication path to the MIMIC gold (ingredient-level RxNorm match).

Phenotype med codes are SCD/product-level RxNorm; MIMIC products (via the
NDC->RxCUI map) are different products of the same drugs. Exact product
matching would under-match, so BOTH sides are normalized to ingredient
RxCUIs:

  phenotype side: test-case RxNorm codes -> ingredients (RxNav, cached in
                  data/rxcui_ingredients.json; a code that IS an ingredient
                  maps to itself)
  patient side:   MedicationRequest.medicationReference -> Medication ->
                  NDC -> product RxCUI -> ingredients

meds cohort = patients whose ingredient set intersects the phenotype's.
Writes gold v2 with meds + comprehensive = dx ∪ labs ∪ meds.

Usage:
    python scripts/add_meds_to_mimic_gold.py \
        --raw-dir C:/Users/jaerwin/Downloads/mimic-in-fhir/raw \
        --gold data/mimic-full-gold.json --out data/mimic-full-gold-v2.json
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TC_DIR = REPO / "test-cases" / "phekb"
RXNORM = "rxnorm"
_URL_RX = re.compile(r"rxnorm\|(\d+)")


def load_phenotype_rxnorm(phenotype: str) -> set:
    """RxNorm codes from the phenotype's test cases (skip negation cases)."""
    out = set()
    for fn in glob.glob(str(TC_DIR / f"phekb-{phenotype}-*.json")) + \
              glob.glob(str(TC_DIR / f"phekb-{phenotype}.json")):
        d = json.load(open(fn, encoding="utf-8"))
        meta = d.get("metadata", {}) or {}
        if meta.get("negation"):
            continue
        for rc in meta.get("required_codes", []) or []:
            if RXNORM in rc.get("system", "") and str(rc.get("code", "")).isdigit():
                out.add(str(rc["code"]))
        blob = json.dumps(d.get("expected_query", {})) + json.dumps(meta.get("expected_queries", []))
        out.update(_URL_RX.findall(blob))
    return out


def ensure_ingredients(cuis: set, cache_path: Path, sleep: float = 0.07) -> dict:
    """rxcui -> [ingredient rxcuis]; fetch any missing from RxNav, update cache."""
    cache = json.load(cache_path.open(encoding="utf-8")) if cache_path.exists() else {}
    todo = [c for c in cuis if c not in cache]
    if todo:
        print(f"fetching ingredients for {len(todo)} phenotype RxCUIs...", file=sys.stderr)
    for cui in todo:
        try:
            url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{cui}/related.json?tty=IN"
            with urllib.request.urlopen(url, timeout=30) as r:
                d = json.load(r)
            ins = [p["rxcui"] for g in (d.get("relatedGroup") or {}).get("conceptGroup") or []
                   for p in g.get("conceptProperties") or []]
            cache[cui] = [{"rxcui": i} for i in ins]
        except Exception as e:
            print(f"  ERR {cui}: {e}", file=sys.stderr)
            cache[cui] = []
        time.sleep(sleep)
    if todo:
        json.dump(cache, cache_path.open("w", encoding="utf-8"), indent=0)
    return {c: {i["rxcui"] for i in v} for c, v in cache.items()}


def to_ingredients(codes: set, ing: dict) -> set:
    """Normalize a set of RxNorm codes to ingredient level (self if no map)."""
    out = set()
    for c in codes:
        ings = ing.get(c) or set()
        out |= ings if ings else {c}
    return out


def build_patient_ingredient_index(raw_dir: Path, ndc_map: dict, ing: dict) -> dict:
    """patient_id -> set of ingredient rxcuis, via Medication + MedicationRequest."""
    med_ings = {}
    for fn in ("MimicMedication.ndjson", "MimicMedicationMix.ndjson"):
        with (raw_dir / fn).open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                cuis = set()
                for cd in (r.get("code") or {}).get("coding", []):
                    hit = ndc_map.get(cd.get("code") or "") if "ndc" in (cd.get("system") or "") else None
                    if hit:
                        cuis |= to_ingredients({hit["rxcui"]}, ing)
                if cuis:
                    med_ings[r["id"]] = cuis
    print(f"  {len(med_ings)} Medications with ingredients", file=sys.stderr)
    pidx = defaultdict(set)
    n = 0
    with (raw_dir / "MimicMedicationRequest.ndjson").open(encoding="utf-8") as f:
        for line in f:
            n += 1
            if n % 2_000_000 == 0:
                print(f"  {n/1e6:.0f}M MedicationRequests scanned", file=sys.stderr)
            r = json.loads(line)
            ref = (r.get("medicationReference") or {}).get("reference", "")
            mid = ref.split("/")[-1] if ref else None
            cuis = med_ings.get(mid)
            if not cuis:
                continue
            pref = (r.get("subject") or {}).get("reference", "")
            pid = pref.split("/")[-1] if pref else None
            if pid:
                pidx[pid] |= cuis
    return pidx


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--gold", default="data/mimic-full-gold.json")
    ap.add_argument("--out", default="data/mimic-full-gold-v2.json")
    args = ap.parse_args(argv)

    gold = json.load((REPO / args.gold).open(encoding="utf-8"))
    ndc_map = json.load((REPO / "data/ndc_rxnorm_map.json").open(encoding="utf-8"))

    pheno_rx = {ph: load_phenotype_rxnorm(ph) for ph in gold}
    all_cuis = set().union(*pheno_rx.values()) | \
               {v["rxcui"] for v in ndc_map.values() if v}
    ing = ensure_ingredients(all_cuis, REPO / "data/rxcui_ingredients.json")

    print("building patient ingredient index (15.4M MedicationRequests)...", file=sys.stderr)
    pidx = build_patient_ingredient_index(Path(args.raw_dir), ndc_map, ing)
    print(f"  {len(pidx)} patients with mapped medications", file=sys.stderr)

    n_meds = 0
    for ph, g in gold.items():
        target = to_ingredients(pheno_rx[ph], ing)
        meds = sorted(pid for pid, cuis in pidx.items() if cuis & target) if target else []
        comp = sorted(set(g.get("dx", [])) | set(g.get("labs", [])) | set(meds))
        g["meds"] = meds
        g["comprehensive"] = comp
        g["counts"]["meds"] = len(meds)
        g["counts"]["comprehensive"] = len(comp)
        if meds:
            n_meds += 1
    json.dump(gold, (REPO / args.out).open("w", encoding="utf-8"))
    print(f"wrote {args.out}: {n_meds}/{len(gold)} phenotypes with a meds cohort")
    top = sorted(gold.items(), key=lambda kv: -kv[1]["counts"]["meds"])[:10]
    for ph, g in top:
        c = g["counts"]
        print(f"  {ph:36s} meds={c['meds']:6d} dx={c['dx']:6d} comp={c['comprehensive']:6d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
