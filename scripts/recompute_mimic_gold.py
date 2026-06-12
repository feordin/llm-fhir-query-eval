"""Compute per-phenotype GOLD patient cohorts on MIMIC-IV (the dx + labs paths).

Why this exists: MIMIC uses real granular ICD codes (E11.9, E11.42, ...) and the
FHIR server does exact token matching with no `code:below` hierarchy. So a
synthetic test case's gold (SNOMED codes, or a category code like `E11`) returns
the wrong cohort -- or nothing -- on MIMIC. The TRUE MIMIC cohort is "patients
whose Condition carries any ICD code under the phenotype's category" -- exactly
the hierarchical prefix match that `mimic_phenotype_counts.py` already implements
and unit-tests.

This script reuses that proven logic to emit the gold PATIENT SETS (not just
counts) per phenotype, for the MIMIC-evaluable paths:
  - dx           : patients matching the phenotype's ICD-10/ICD-9 dx codes (prefix)
  - labs         : patients with a lab Observation meeting the phenotype's threshold
  - comprehensive: dx ∪ labs (meds=NDC and procedures=ICD-10-PCS don't crosswalk to
                   our RxNorm/CPT-SNOMED codes, so they're excluded -- reported)

Patient ids are the raw MIMIC Patient ids (from `subject.reference`), which match
the live server ids when queried with resolve_stable_ids=False (no Synthea remap).

Usage:
    python scripts/recompute_mimic_gold.py \
        --standardized-dir "C:/Users/.../mimic-.../fhir-standardized" \
        --out data/mimic-gold.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from mimic_phenotype_counts import (  # noqa: E402
    build_patient_index, build_patient_lab_index, load_phenotype_icd_codes,
    load_phenotype_lab_criteria, icd_matches, value_meets, _load_augmentations,
    PHENOTYPES,
)


def dx_patient_set(pheno_codes: dict, pidx: dict) -> set:
    """Patients whose Condition ICD-10/ICD-9 codes prefix-match the phenotype's."""
    hits = set()
    for pid, pcodes in pidx.items():
        for sysk in ("icd10cm", "icd9cm"):
            if pheno_codes[sysk] and any(icd_matches(mc, pheno_codes[sysk])
                                         for mc in pcodes[sysk]):
                hits.add(pid)
                break
    return hits


def lab_patient_set(criteria: list, lidx: dict) -> set:
    """Patients with a lab Observation meeting any (loinc, comparator, threshold)."""
    by_loinc = defaultdict(list)
    for loinc, comp, thr in criteria:
        by_loinc[loinc].append((comp, thr))
    if not by_loinc:
        return set()
    hits = set()
    for pid, obs in lidx.items():
        for loinc, val in obs:
            for comp, thr in by_loinc.get(loinc, ()):
                if value_meets(val, comp, thr):
                    hits.add(pid)
                    break
            else:
                continue
            break
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--standardized-dir", required=True,
                    help="MIMIC fhir-standardized dir (Condition/Procedure/Observation ndjson)")
    ap.add_argument("--out", default="data/mimic-gold.json")
    ap.add_argument("--phenotypes", nargs="*", default=PHENOTYPES)
    ap.add_argument("--min-cohort", type=int, default=1,
                    help="only keep phenotypes whose largest path cohort >= this")
    args = ap.parse_args(argv)

    aug = _load_augmentations()
    sdir = Path(args.standardized_dir)
    print("Building MIMIC patient indexes (offline)...", file=sys.stderr)
    pidx = build_patient_index(sdir)
    lidx = build_patient_lab_index(sdir)
    print(f"  {len(pidx)} patients w/ conditions/procedures, {len(lidx)} w/ labs",
          file=sys.stderr)

    gold = {}
    for ph in args.phenotypes:
        codes = load_phenotype_icd_codes(ph, aug)
        dx = dx_patient_set(codes, pidx)
        labs = lab_patient_set(load_phenotype_lab_criteria(ph), lidx)
        comp = dx | labs
        if max(len(dx), len(labs), len(comp)) < args.min_cohort:
            continue
        gold[ph] = {
            "dx": sorted(dx),
            "labs": sorted(labs),
            "comprehensive": sorted(comp),
            "counts": {"dx": len(dx), "labs": len(labs), "comprehensive": len(comp)},
        }

    out_path = REPO / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(gold, indent=1), encoding="utf-8")
    n_dx = sum(1 for g in gold.values() if g["counts"]["dx"])
    n_lab = sum(1 for g in gold.values() if g["counts"]["labs"])
    print(f"wrote {out_path.relative_to(REPO)}: {len(gold)} phenotypes "
          f"({n_dx} with a dx cohort, {n_lab} with a labs cohort)")
    # quick leaderboard for sanity vs the offline counter
    top = sorted(gold.items(), key=lambda kv: -kv[1]["counts"]["dx"])[:12]
    print("Top dx cohorts:", file=sys.stderr)
    for ph, g in top:
        print(f"  {ph:34} dx={g['counts']['dx']:4} labs={g['counts']['labs']:4} "
              f"comp={g['counts']['comprehensive']:4}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
