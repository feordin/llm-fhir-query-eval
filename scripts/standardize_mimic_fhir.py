"""Standardize MIMIC-IV-on-FHIR codes additively.

MIMIC-on-FHIR carries codes under MIMIC-local CodeSystem URIs with undotted ICD
values (and local lab item ids). This transform ADDS a standard coding alongside
each original (never replaces), so our standard-system FHIR queries work while
MIMIC provenance is preserved. Mirrors scripts/augment_fhir_codes.py.

  - Condition / Procedure : add dotted ICD-10-CM / ICD-9-CM / ICD-10-PCS coding
  - Lab Observation       : add LOINC coding via the srdc labitems->LOINC map
  - Medication            : left untouched (handled via skill server-awareness)

Core logic (redot_icd, add_standard_codings) is unit-tested in
scripts/test_standardize_mimic.py.
"""
from __future__ import annotations

# Standard CodeSystem URIs we target.
ICD10CM = "http://hl7.org/fhir/sid/icd-10-cm"
ICD9CM = "http://hl7.org/fhir/sid/icd-9-cm"
ICD10PCS = "http://hl7.org/fhir/sid/icd-10-pcs"
LOINC = "http://loinc.org"

# MIMIC-local system substrings -> (target standard system, dotting kind).
_MIMIC_ICD = {
    "mimic-diagnosis-icd10": (ICD10CM, "diagnosis-icd10"),
    "mimic-diagnosis-icd9": (ICD9CM, "diagnosis-icd9"),
    "mimic-procedure-icd9": (ICD9CM, "procedure-icd9"),
    "mimic-procedure-icd10": (ICD10PCS, "procedure-icd10"),
}
_MIMIC_LAB = "mimic-d-labitems"


def redot_icd(code: str, kind: str) -> str:
    """Insert the conventional decimal point into an undotted ICD code.

    kind is one of: diagnosis-icd10, diagnosis-icd9, procedure-icd9,
    procedure-icd10. Idempotent: an already-dotted code is returned unchanged.
    """
    if not code or "." in code:
        return code
    if kind == "diagnosis-icd10":
        return code[:3] + "." + code[3:] if len(code) > 3 else code
    if kind == "diagnosis-icd9":
        if code[0] in ("E", "e"):  # external-cause: dot after 4th char
            return code[:4] + "." + code[4:] if len(code) > 4 else code
        # numeric or V-code: dot after 3rd char
        return code[:3] + "." + code[3:] if len(code) > 3 else code
    if kind == "procedure-icd9":
        return code[:2] + "." + code[2:] if len(code) > 2 else code
    if kind == "procedure-icd10":  # ICD-10-PCS is never dotted
        return code
    return code


def _standard_coding_for(coding: dict, loinc_map: dict) -> dict | None:
    """Compute the standard coding to add for one MIMIC coding, or None."""
    system = coding.get("system", "")
    code = coding.get("code", "")
    display = coding.get("display")
    for sub, (target_system, kind) in _MIMIC_ICD.items():
        if sub in system:
            std = {"system": target_system, "code": redot_icd(code, kind)}
            if display:
                std["display"] = display
            return std
    if _MIMIC_LAB in system:
        loinc = loinc_map.get(code)
        if loinc:
            std = {"system": LOINC, "code": loinc}
            if display:
                std["display"] = display
            return std
    return None


def add_standard_codings(resource: dict, loinc_map: dict) -> dict:
    """Return the resource with standard codings appended additively.

    Looks at every CodeableConcept-bearing field we standardize (code,
    medicationCodeableConcept) and appends a standard coding next to each
    recognized MIMIC coding. Existing codings are preserved. Idempotent: a
    standard coding that is already present is not duplicated.
    """
    for field in ("code", "medicationCodeableConcept"):
        cc = resource.get(field)
        if not isinstance(cc, dict):
            continue
        codings = cc.get("coding")
        if not isinstance(codings, list):
            continue
        existing = {(c.get("system"), c.get("code")) for c in codings}
        additions = []
        for coding in list(codings):
            std = _standard_coding_for(coding, loinc_map)
            if std and (std["system"], std["code"]) not in existing:
                additions.append(std)
                existing.add((std["system"], std["code"]))
        codings.extend(additions)
    return resource


# ---------------------------------------------------------------------------
# Streaming CLI (I/O around the tested core)
# ---------------------------------------------------------------------------
import argparse  # noqa: E402
import csv  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
from collections import Counter  # noqa: E402
from pathlib import Path  # noqa: E402

# Files that carry codes we standardize (Chartevents excluded by default: 534 MB
# of ICU vitals our phenotype algorithms rarely need).
DEFAULT_FILES = [
    "MimicCondition.ndjson", "MimicConditionED.ndjson",
    "MimicProcedure.ndjson", "MimicProcedureED.ndjson", "MimicProcedureICU.ndjson",
    "MimicObservationLabevents.ndjson", "MimicObservationED.ndjson",
]


def load_loinc_map(path: Path) -> dict:
    """itemid -> LOINC from the srdc labitems-to-loinc.csv (source_code/target_code)."""
    m = {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            code = (r.get("source_code") or "").strip()
            loinc = (r.get("target_code") or "").strip()
            if code and loinc:
                m[code] = loinc
    return m


def standardize_file(src: Path, dst: Path, loinc_map: dict, limit: int | None = None) -> Counter:
    stats = Counter()
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open(encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
        for i, line in enumerate(fin):
            if limit is not None and i >= limit:
                break
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            before = _coding_count(r)
            add_standard_codings(r, loinc_map)
            stats["resources"] += 1
            stats["codings_added"] += _coding_count(r) - before
            fout.write(json.dumps(r) + "\n")
    return stats


def _coding_count(resource: dict) -> int:
    n = 0
    for field in ("code", "medicationCodeableConcept"):
        cc = resource.get(field)
        if isinstance(cc, dict) and isinstance(cc.get("coding"), list):
            n += len(cc["coding"])
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description="Additively standardize MIMIC-on-FHIR codes.")
    ap.add_argument("--input-dir", required=True, help="MIMIC .../fhir directory")
    ap.add_argument("--output-dir", required=True, help="destination for standardized NDJSON")
    ap.add_argument("--loinc-map", default="data/mimic-mappings/srdc-labitems-to-loinc.csv")
    ap.add_argument("--files", nargs="*", default=DEFAULT_FILES,
                    help="NDJSON filenames to transform (default: ICD + lab files)")
    ap.add_argument("--limit", type=int, default=None, help="cap resources per file (smoke test)")
    args = ap.parse_args(argv)

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    loinc_map = load_loinc_map(Path(args.loinc_map))
    print(f"LOINC map: {len(loinc_map)} itemid->LOINC entries")

    total = Counter()
    for fn in args.files:
        src = in_dir / fn
        if not src.exists():
            print(f"  SKIP (missing): {fn}")
            continue
        st = standardize_file(src, out_dir / fn, loinc_map, args.limit)
        total.update(st)
        print(f"  {fn}: {st['resources']} resources, +{st['codings_added']} standard codings")
    print(f"TOTAL: {total['resources']} resources, +{total['codings_added']} standard codings")
    print(f"wrote standardized NDJSON to {out_dir}")


if __name__ == "__main__":
    sys.exit(main())
