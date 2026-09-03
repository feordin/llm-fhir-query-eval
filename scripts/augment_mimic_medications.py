"""Additively add RxNorm codings to MIMIC Medication resources.

MIMIC Medications carry only NDC under a MIMIC-local system. Using the
RxNav-built maps (data/ndc_rxnorm_map.json product level,
data/rxcui_ingredients.json ingredient level), append RxNorm codings —
product RxCUI + each ingredient RxCUI — beside the NDC. Original codings are
preserved; idempotent.

Writes fresh files (never in place: the upload dir holds HARDLINKS to the
raw files — writing through them would corrupt the raw data).

Usage:
    python scripts/augment_mimic_medications.py \
        --raw-dir  C:/Users/jaerwin/Downloads/mimic-in-fhir/raw \
        --out-dir  C:/Users/jaerwin/Downloads/mimic-in-fhir/upload
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"
FILES = ["MimicMedication.ndjson", "MimicMedicationMix.ndjson"]


def augment(resource: dict, ndc_map: dict, ing_map: dict) -> int:
    cc = resource.get("code")
    if not isinstance(cc, dict) or not isinstance(cc.get("coding"), list):
        return 0
    codings = cc["coding"]
    existing = {(c.get("system"), c.get("code")) for c in codings}
    added = 0
    for cd in list(codings):
        if "ndc" not in (cd.get("system") or ""):
            continue
        hit = ndc_map.get(cd.get("code") or "")
        if not hit:
            continue
        cands = [{"system": RXNORM, "code": hit["rxcui"], "display": hit.get("name", "")}]
        for ing in ing_map.get(hit["rxcui"], []) or []:
            cands.append({"system": RXNORM, "code": ing["rxcui"], "display": ing.get("name", "")})
        for c in cands:
            key = (c["system"], c["code"])
            if key not in existing:
                codings.append(c)
                existing.add(key)
                added += 1
    return added


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)

    ndc_map = json.load((REPO / "data/ndc_rxnorm_map.json").open(encoding="utf-8"))
    ing_map = json.load((REPO / "data/rxcui_ingredients.json").open(encoding="utf-8"))
    for fn in FILES:
        src = Path(args.raw_dir) / fn
        dst = Path(args.out_dir) / fn
        if dst.exists():
            os.remove(dst)  # break the hardlink before writing
        n = added = 0
        with src.open(encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
            for line in fin:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                added += augment(r, ndc_map, ing_map)
                n += 1
                fout.write(json.dumps(r) + "\n")
        print(f"{fn}: {n} resources, +{added} RxNorm codings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
