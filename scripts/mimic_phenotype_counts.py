"""Offline per-phenotype patient counts against standardized MIMIC-on-FHIR.

Counts distinct MIMIC patients matching each phenotype's ICD dx codes (the
high-confidence "headline" number) and procedure codes, by matching our
phenotype code lists against the STANDARDIZED MIMIC Conditions/Procedures
(see standardize_mimic_fhir.py). No FHIR server required.

Matching is hierarchical: a phenotype category code (e.g. ICD-10 `E11`) matches
any MIMIC subcode (`E11.9`), mirroring FHIR token search semantics.

Core logic (normalize_icd, icd_matches) is unit-tested in
scripts/test_mimic_counts.py.
"""
from __future__ import annotations

ICD10CM = "http://hl7.org/fhir/sid/icd-10-cm"
ICD9CM = "http://hl7.org/fhir/sid/icd-9-cm"
ICD10PCS = "http://hl7.org/fhir/sid/icd-10-pcs"


def normalize_icd(code: str) -> str:
    """Strip the decimal point and uppercase, for hierarchical comparison."""
    return code.replace(".", "").strip().upper()


def icd_matches(mimic_code: str, pheno_codes: set) -> bool:
    """True if any phenotype code is a (normalized) prefix of the MIMIC code."""
    m = normalize_icd(mimic_code)
    for p in pheno_codes:
        pn = normalize_icd(p)
        if pn and m.startswith(pn):
            return True
    return False


import re as _re  # noqa: E402

_VQ = _re.compile(r"([a-z]{2})(-?\d+\.?\d*)")


def parse_value_quantity(s: str) -> tuple:
    """Parse a FHIR value-quantity token '<comp><value>|system|unit' -> (comp, value).

    >>> parse_value_quantity("ge6.5||%")
    ('ge', 6.5)
    >>> parse_value_quantity("le-2.5")
    ('le', -2.5)
    """
    m = _VQ.match(s.strip())
    if not m:
        raise ValueError(f"unparseable value-quantity: {s!r}")
    return m.group(1), float(m.group(2).rstrip("."))


def value_meets(value: float, comparator: str, threshold: float) -> bool:
    """Apply a FHIR quantity comparator (ge/gt/le/lt/eq/ne)."""
    return {
        "ge": value >= threshold,
        "gt": value > threshold,
        "le": value <= threshold,
        "lt": value < threshold,
        "eq": value == threshold,
        "ne": value != threshold,
    }.get(comparator, False)


# ---------------------------------------------------------------------------
# Data loading + counting
# ---------------------------------------------------------------------------
import argparse  # noqa: E402
import glob  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
from collections import defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
TEST_CASES = REPO / "test-cases" / "phekb"
AUGMENTATIONS = REPO / "data" / "code_augmentations.json"

# Canonical 108 phenotypes (NEW 73 + OLD 35), longest-first for prefix mapping.
PHENOTYPES = [
    "abdominal-aortic-aneurysm", "ace-inhibitor-cough", "adhd", "alcohol-use-disorder",
    "appendicitis", "asthma-response-inhaled-steroids", "autism", "autoimmune-disease",
    "bladder-cancer", "bone-scan-utilization", "bph", "breast-cancer", "ca-mrsa",
    "cardiac-conduction-qrs", "cardiorespiratory-fitness", "carotid-atherosclerosis",
    "cataracts", "cervical-cancer", "chronic-rhinosinusitis", "clopidogrel-poor-metabolizers",
    "clostridium-difficile", "colorectal-cancer", "cystic-fibrosis",
    "developmental-language-disorder", "diabetic-retinopathy", "digital-rectal-exam",
    "diverticulitis", "down-syndrome", "drug-induced-liver-injury", "endometriosis",
    "esophageal-cancer", "familial-hypercholesterolemia", "febrile-neutropenia-pediatric",
    "functional-seizures", "glaucoma", "glioblastoma", "hearing-loss", "hepatitis-c",
    "herpes-zoster", "hiv", "influenza", "intellectual-disability", "leukemia", "liver-cancer",
    "liver-cancer-staging", "lung-cancer", "lyme-disease", "lymphoma", "melanoma",
    "multimodal-analgesia", "multiple-myeloma", "nafld", "neonatal-abstinence-syndrome",
    "ovarian-cancer", "pancreatic-cancer", "peanut-allergy", "peripheral-arterial-disease",
    "polycystic-kidney-disease", "post-event-pain", "prostate-cancer", "renal-cancer",
    "resistant-hypertension", "sepsis", "severe-childhood-obesity", "sickle-cell-disease",
    "sleep-apnea", "statins-and-mace", "steroid-induced-avn", "stomach-cancer", "thyroid-cancer",
    "tuberculosis", "urinary-incontinence", "warfarin-dose-response",
    "anxiety", "asthma", "atrial-fibrillation", "bipolar-disorder", "ckd", "copd",
    "coronary-heart-disease", "crohns-disease", "dementia", "depression", "epilepsy", "gerd",
    "heart-failure", "hypertension", "hyperthyroidism", "hypothyroidism", "migraine",
    "rheumatoid-arthritis", "stroke", "type-1-diabetes", "type-2-diabetes",
    "acute-kidney-injury", "atopic-dermatitis", "fibromyalgia", "gout",
    "iron-deficiency-anemia", "multiple-sclerosis", "osteoporosis", "parkinsons-disease",
    "pneumonia", "psoriasis", "schizophrenia", "systemic-lupus-erythematosus",
    "ulcerative-colitis", "venous-thromboembolism",
]


def _load_augmentations() -> dict:
    if AUGMENTATIONS.exists():
        return json.load(AUGMENTATIONS.open(encoding="utf-8"))
    return {}


_URL_CODE = re.compile(r"(icd-10-cm|icd-9-cm|icd-10-pcs)\|([^,&\s]+)")


def load_phenotype_icd_codes(phenotype: str, augmentations: dict) -> dict:
    """Gather a phenotype's ICD dx + procedure codes from its test cases.

    Pulls structured `metadata.required_codes`, inline `expected_query` URLs, and
    crosswalks any SNOMED codes through code_augmentations.json to recover ICD.
    Returns {"icd10cm": set, "icd9cm": set, "icd10pcs": set}.
    """
    out = {"icd10cm": set(), "icd9cm": set(), "icd10pcs": set()}
    sys_key = {ICD10CM: "icd10cm", ICD9CM: "icd9cm", ICD10PCS: "icd10pcs",
               "icd-10-cm": "icd10cm", "icd-9-cm": "icd9cm", "icd-10-pcs": "icd10pcs"}

    for fn in glob.glob(str(TEST_CASES / f"phekb-{phenotype}-*.json")) + \
              glob.glob(str(TEST_CASES / f"phekb-{phenotype}.json")):
        d = json.load(open(fn, encoding="utf-8"))
        meta = d.get("metadata", {}) or {}
        for rc in meta.get("required_codes", []) or []:
            sysu = rc.get("system", "")
            code = str(rc.get("code", ""))
            key = next((sys_key[k] for k in sys_key if k in sysu), None)
            if key and code:
                out[key].add(code)
            # crosswalk SNOMED -> ICD via augmentations
            if "snomed" in sysu and code in augmentations:
                for aug in augmentations[code]:
                    k2 = next((sys_key[k] for k in sys_key if k in aug.get("system", "")), None)
                    if k2:
                        out[k2].add(str(aug.get("code", "")))
        # inline URL codes
        url = json.dumps(d.get("expected_query", {})) + json.dumps(meta.get("expected_queries", []))
        for sysshort, code in _URL_CODE.findall(url):
            out[sys_key[sysshort]].add(code)
    return out


def build_patient_index(standardized_dir: Path) -> dict:
    """patient_id -> {'icd10cm', 'icd9cm', 'icd10pcs'} of normalized codes.

    dx buckets (icd10cm/icd9cm) are populated ONLY from Condition resources;
    procedure codes (icd10pcs, and ICD-9 procedures) come ONLY from Procedure
    resources. This prevents an ICD-9 procedure code from spuriously matching a
    phenotype's ICD-9 diagnosis category (both share the icd-9-cm system URI).
    """
    idx = defaultdict(lambda: {"icd10cm": set(), "icd9cm": set(), "icd10pcs": set()})
    for fn in ["MimicCondition.ndjson", "MimicConditionED.ndjson",
               "MimicProcedure.ndjson", "MimicProcedureED.ndjson"]:
        path = standardized_dir / fn
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                rtype = r.get("resourceType")
                ref = (r.get("subject") or {}).get("reference", "")
                pid = ref.split("/")[-1] if ref else None
                if not pid:
                    continue
                for cd in r.get("code", {}).get("coding", []):
                    system, code = cd.get("system"), cd.get("code")
                    if not code:
                        continue
                    if rtype == "Condition" and system == ICD10CM:
                        idx[pid]["icd10cm"].add(normalize_icd(code))
                    elif rtype == "Condition" and system == ICD9CM:
                        idx[pid]["icd9cm"].add(normalize_icd(code))
                    elif rtype == "Procedure" and system == ICD10PCS:
                        idx[pid]["icd10pcs"].add(normalize_icd(code))
    return idx


def _lab_criteria_from_url(url: str) -> list:
    """Extract (loinc, comparator, threshold) criteria from a FHIR query URL.

    Handles both the composite `code-value-quantity=SYS|LOINC$<comp><val>` form
    and the separate `code=SYS|LOINC ... value-quantity=<comp><val>` form.
    Only threshold-bearing criteria are returned.
    """
    crits = []
    for m in re.finditer(r"code-value-quantity=([^&]+)", url):
        for part in m.group(1).split(","):
            if "$" in part and "|" in part:
                codepart, vq = part.split("$", 1)
                loinc = codepart.split("|")[-1]
                try:
                    comp, val = parse_value_quantity(vq)
                    crits.append((loinc, comp, val))
                except ValueError:
                    pass
    last_loinc = None
    for tok in re.split(r"[&?]", url):
        if tok.startswith("code=") and "loinc" in tok.lower():
            last_loinc = tok.split("|")[-1].split(",")[0]
        elif tok.startswith("value-quantity=") and last_loinc:
            try:
                comp, val = parse_value_quantity(tok[len("value-quantity="):])
                crits.append((last_loinc, comp, val))
            except ValueError:
                pass
            last_loinc = None
    return crits


def load_phenotype_lab_criteria(phenotype: str) -> list:
    """Distinct (loinc, comparator, threshold) lab criteria for a phenotype."""
    crits = set()
    for fn in glob.glob(str(TEST_CASES / f"phekb-{phenotype}-*.json")) + \
              glob.glob(str(TEST_CASES / f"phekb-{phenotype}.json")):
        d = json.load(open(fn, encoding="utf-8"))
        blob = json.dumps(d.get("expected_query", {})) + json.dumps((d.get("metadata") or {}).get("expected_queries", []))
        for c in _lab_criteria_from_url(blob):
            crits.add(c)
    return list(crits)


def build_patient_lab_index(standardized_dir: Path) -> dict:
    """patient_id -> list of (loinc_code, numeric_value) from standardized labs."""
    idx = defaultdict(list)
    for fn in ["MimicObservationLabevents.ndjson", "MimicObservationED.ndjson"]:
        path = standardized_dir / fn
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                ref = (r.get("subject") or {}).get("reference", "")
                pid = ref.split("/")[-1] if ref else None
                vq = r.get("valueQuantity") or {}
                val = vq.get("value")
                if not pid or not isinstance(val, (int, float)):
                    continue
                for cd in r.get("code", {}).get("coding", []):
                    if cd.get("system") == "http://loinc.org" and cd.get("code"):
                        idx[pid].append((cd["code"], float(val)))
    return idx


def count_phenotype_labs(criteria: list, lab_index: dict) -> int:
    """Distinct patients with a lab observation meeting any criterion."""
    by_loinc = defaultdict(list)
    for loinc, comp, thr in criteria:
        by_loinc[loinc].append((comp, thr))
    if not by_loinc:
        return 0
    hits = set()
    for pid, obs in lab_index.items():
        for loinc, val in obs:
            for comp, thr in by_loinc.get(loinc, ()):
                if value_meets(val, comp, thr):
                    hits.add(pid)
                    break
            else:
                continue
            break
    return len(hits)


def count_phenotype(pheno_codes: dict, patient_index: dict) -> dict:
    """Return {'dx': n_patients, 'procedure': n_patients} for one phenotype."""
    dx_codes = {"icd10cm": pheno_codes["icd10cm"], "icd9cm": pheno_codes["icd9cm"]}
    pcs_codes = pheno_codes["icd10pcs"]
    dx_hits, proc_hits = set(), set()
    for pid, pcodes in patient_index.items():
        # dx: any condition ICD-10/9 matches
        for sysk in ("icd10cm", "icd9cm"):
            if dx_codes[sysk] and any(icd_matches(mc, dx_codes[sysk]) for mc in pcodes[sysk]):
                dx_hits.add(pid)
                break
        # procedure: ICD-10-PCS match
        if pcs_codes and any(icd_matches(mc, pcs_codes) for mc in pcodes["icd10pcs"]):
            proc_hits.add(pid)
    return {"dx": len(dx_hits), "procedure": len(proc_hits)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Count MIMIC patients per phenotype (offline).")
    ap.add_argument("--standardized-dir", required=True)
    ap.add_argument("--phenotypes", nargs="*", default=PHENOTYPES)
    ap.add_argument("--min-dx", type=int, default=0, help="only print phenotypes with >= this dx count")
    args = ap.parse_args(argv)

    aug = _load_augmentations()
    sdir = Path(args.standardized_dir)
    print("Building patient indexes from standardized MIMIC...", file=sys.stderr)
    pidx = build_patient_index(sdir)
    lidx = build_patient_lab_index(sdir)
    print(f"  {len(pidx)} patients w/ conditions+procedures, {len(lidx)} w/ labs", file=sys.stderr)

    rows = []
    for ph in args.phenotypes:
        codes = load_phenotype_icd_codes(ph, aug)
        res = count_phenotype(codes, pidx)
        lab = count_phenotype_labs(load_phenotype_lab_criteria(ph), lidx)
        rows.append((ph, res["dx"], res["procedure"], lab))

    rows.sort(key=lambda r: (-max(r[1], r[3]), -r[1]))
    print(f"\n{'phenotype':36s} {'dx_pts':>7s} {'proc_pts':>9s} {'lab_pts':>8s}")
    print("-" * 64)
    for ph, dx, proc, lab in rows:
        if max(dx, proc, lab) >= args.min_dx:
            print(f"{ph:36s} {dx:7d} {proc:9d} {lab:8d}")
    total_any = sum(1 for _, dx, proc, lab in rows if dx or proc or lab)
    print(f"\n{total_any}/{len(rows)} phenotypes have >=1 matching MIMIC patient (dx, procedure, or lab).")


if __name__ == "__main__":
    sys.exit(main())
