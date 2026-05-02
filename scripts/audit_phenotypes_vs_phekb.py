"""
Audit each Synthea module against the corresponding PheKB raw documents.

For each phenotype module in synthea/modules/custom/phekb_*.json:
  1. Extract codes used in the module
  2. Find matching PheKB raw dir (fuzzy slug match)
  3. Extract codes + clinical_criteria + algorithm_summary from document_analysis.json
  4. Score: PheKB-available (Y/N), code coverage (module-codes ∩ phekb-codes), complexity gap

Output: docs/PHENOTYPE-AUDIT.md
"""
from __future__ import annotations
import json
import re
import sys
import io
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
MODULES_DIR = REPO / "synthea" / "modules" / "custom"
PHEKB_RAW = REPO / "data" / "phekb-raw"
OUT = REPO / "docs" / "PHENOTYPE-AUDIT.md"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def module_phenotypes() -> list[Path]:
    return sorted(p for p in MODULES_DIR.glob("phekb_*.json") if "_control" not in p.stem)


def module_codes(path: Path) -> dict[str, set[str]]:
    """Pull all (system, code) pairs from the module."""
    with path.open(encoding="utf-8") as f:
        text = f.read()
    snomed = set(re.findall(r'"system":\s*"SNOMED-CT?",?\s*"code":\s*"(\d+)"', text))
    rxnorm = set(re.findall(r'"system":\s*"RxNorm",?\s*"code":\s*"(\d+)"', text))
    loinc = set(re.findall(r'"system":\s*"LOINC",?\s*"code":\s*"([\w-]+)"', text))
    return {"SNOMED": snomed, "RXNORM": rxnorm, "LOINC": loinc}


def module_complexity(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    states = data.get("states", {})
    has_med = any(s.get("type") == "MedicationOrder" for s in states.values())
    has_obs = any(s.get("type") == "Observation" for s in states.values())
    has_proc = any(s.get("type") == "Procedure" for s in states.values())
    has_choose_path = any("Choose_Patient_Path" in k for k in states)
    paths = []
    if has_choose_path:
        for k, v in states.items():
            if "Choose_Patient_Path" in k:
                paths = [t.get("transition") for t in v.get("distributed_transition", [])]
    return {
        "has_med": has_med,
        "has_obs": has_obs,
        "has_proc": has_proc,
        "path_count": len(paths) if paths else (1 if not has_choose_path else 0),
        "states": len(states),
    }


EXPLICIT_ALIASES = {
    "abdominal-aortic-aneurysm": "abdominal-aortic-aneurysm-aaa",
    "ace-inhibitor-cough": "ace-inhibitor-ace-i-induced-cough",
    "acute-kidney-injury": "acute-kidney-injury-aki",
    "adhd": "adhd-phenotype-algorithm",
    "anxiety": "anxiety-algorithm",
    "atopic-dermatitis": "atopic-dermatitis-algorithm",
    "atrial-fibrillation": "atrial-fibrillation-demonstration-project",
    "bph": "phema-bph-benign-prostatic-hyperplasia-cases",
    "ca-mrsa": "camrsa",
    "carotid-atherosclerosis": "caad-carotid-artery-atherosclerosis-disease",
    "chronic-rhinosinusitis": "crs-chronic-rhinosinusitis",
    "ckd": "chronic-kidney-disease",
    "clostridium-difficile": "clostridium-difficile-colitis",
    "colorectal-cancer": "colorectal-cancer-crc",
    "coronary-heart-disease": "coronary-heart-disease-chd",
    "crohns-disease": "crohns-disease-demonstration-project",
    "diverticulitis": "diverticulosis-and-diverticulitis",
    "epilepsy": "epilepsyantiepileptic-drug-response-algorithm",
    "familial-hypercholesterolemia": "electronic-health-record-based-phenotyping-algorithm-familial-hypercholesterolemia",
    "fibromyalgia": "identification-fibromyalgia-patients-rheumatoid-arthritis-cohort",
    "gerd": "gastroesophageal-reflux-disease-gerd-phenotype-algorithm",
    "heart-failure": "heart-failure-hf-differentiation-between-preserved-and-reduced-ejection-fraction",
    "hypertension": "blood-pressure",  # closest semantic match; resistant-hypertension is a distinct entry
    "lung-cancer": "computable-phenotypes-identifying-patients-lung-and-gastroenteropancreatic-neuroendocrine",
    "multiple-sclerosis": "multiple-sclerosis-demonstration-project",
    "nafld": "non-alcoholic-fatty-liver-disease-nalfd-alcoholic-fatty-liver-disease-ald",
    "neonatal-abstinence-syndrome": "opioid-exposed-infants",
    "ovarian-cancer": "ovarianuterine-cancer-ovutca",
    "peripheral-arterial-disease": "peripheral-arterial-disease-2012",
    "pneumonia": "pneumonia-vumc-emerge-v51",
    "prostate-cancer": "prostate-cancer-0",
    "rheumatoid-arthritis": "rheumatoid-arthritis-demonstration-project",
    "severe-childhood-obesity": "severe-early-childhood-obesity",
    "sickle-cell-disease": "sickle-cell-disease-0",
    "sle": "sle-systemic-lupus-erythematosus-using-slicc-systemic-lupus-internation-collaborating",
    "systemic-lupus-erythematosus": "sle-systemic-lupus-erythematosus-using-slicc-systemic-lupus-internation-collaborating",
    "steroid-induced-avn": "steroid-induced-osteonecrosis",
    "type-1-diabetes": "type-1-and-type-2-diabetes-mellitus",
    "type-2-diabetes": "type-2-diabetes-t2d",
    "venous-thromboembolism": "venous-thromboembolism-vte",
    # Batch 26-31 PheKB-aligned phenotypes
    "autoimmune-disease": "autoimmune-disease-phenotype",
    "bone-scan-utilization": "bone-scan-utilization-0",
    "cardiorespiratory-fitness": "cardiorespiratory-fitness-algorithm-emerge-mayo-network-phenotype",
    "liver-cancer-staging": "liver-cancer-staging-project",
    "post-event-pain": "post-event-pain-algorithm",
    "warfarin-dose-response": "warfarin-doseresponse",
    # Phenotypes that have NO PheKB doc — explicit None to suppress fuzzy mismatches
    "alcohol-use-disorder": None,
    "bipolar-disorder": None,
    "esophageal-cancer": None,
    "liver-cancer": None,
    "multiple-myeloma": None,
    "pancreatic-cancer": None,
    "polycystic-kidney-disease": None,
    "thyroid-cancer": None,
    "ulcerative-colitis": None,
    "stomach-cancer": None,
    "gastric-cancer": None,
    "hcc": None,
    "renal-cancer": None,
    "rcc": None,
    "stroke": None,
    "tuberculosis": None,
    "tb": None,
    "schizophrenia": None,
    "gout": None,
    "iron-deficiency-anemia": None,
    "cervical-cancer": None,
    "hearing-loss": None,
    "sepsis": None,
    "cystic-fibrosis": None,
    "bladder-cancer": None,
    "down-syndrome": None,
    "leukemia": None,
    "lymphoma": None,
    "hyperthyroidism": None,
    "influenza": None,
    "lyme-disease": None,
    "copd": None,
    "endometriosis": None,
    "parkinsons-disease": None,
    "psoriasis": None,
    "ca-mrsa": "camrsa",  # already above but keep
    "functional-seizures": "functional-seizures",
    "intellectual-disability": "intellectual-disability",
    "urinary-incontinence": "urinary-incontinence",
    "drug-induced-liver-injury": "drug-induced-liver-injury",
    "resistant-hypertension": "resistant-hypertension",
    "dementia": "dementia",
    "depression": "depression",
    "appendicitis": "appendicitis",
    "asthma": "asthma",
    "autism": "autism",
    "breast-cancer": "breast-cancer",
    "cataracts": "cataracts",
    "diabetic-retinopathy": "diabetic-retinopathy",
    "glaucoma": None,
    "glioblastoma": None,
    "hepatitis-c": None,
    "herpes-zoster": "herpes-zoster",
    "hiv": "hiv",
    "hypothyroidism": "hypothyroidism",
    "melanoma": None,
    "migraine": "migraine",
    "osteoporosis": None,
    "peanut-allergy": "peanut-allergy",
    "sleep-apnea": "sleep-apnea-phenotype",
    "type-2-diabetes": "type-2-diabetes-t2d",
}


def phekb_dir_for(slug_name: str) -> Path | None:
    """Map module slug to PheKB raw dir using explicit aliases first, then exact."""
    if not PHEKB_RAW.exists():
        return None
    if slug_name in EXPLICIT_ALIASES:
        target = EXPLICIT_ALIASES[slug_name]
        if target is None:
            return None
        candidate = PHEKB_RAW / target
        return candidate if candidate.is_dir() else None
    # exact fall-through
    candidate = PHEKB_RAW / slug_name
    return candidate if candidate.is_dir() else None


def phekb_summary(d: Path) -> dict:
    out = {"codes_by_system": defaultdict(int), "clinical_criteria": [], "algorithm_summary": "", "files": []}
    da = d / "document_analysis.json"
    if da.exists():
        with da.open(encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                data = {}
        for c in data.get("extracted_codes", []):
            out["codes_by_system"][c.get("system", "?")] += 1
        out["clinical_criteria"] = data.get("clinical_criteria", []) or []
        out["algorithm_summary"] = data.get("algorithm_summary", "") or ""
        out["files"] = data.get("analyzed_files", []) or []
    return out


def tier(module_complex: dict, phekb_data: dict | None) -> str:
    if phekb_data is None:
        return "T3-no-phekb"
    pcodes = sum(phekb_data["codes_by_system"].values())
    has_thresholds = bool(phekb_data["clinical_criteria"]) or any(
        kw in phekb_data["algorithm_summary"].lower() for kw in ["threshold", "x uln", ">=", "≥", "ratio"]
    )
    has_temporal = "temporal" in phekb_data["algorithm_summary"].lower() or "prior to" in phekb_data["algorithm_summary"].lower()
    if pcodes >= 8 or has_thresholds or has_temporal:
        return "T1-significant-gap"
    if pcodes >= 3:
        return "T2-minor-gap"
    return "T3-aligned"


def main():
    rows = []
    for mod in module_phenotypes():
        name = mod.stem.replace("phekb_", "").replace("_", "-")
        m_codes = module_codes(mod)
        m_complex = module_complexity(mod)
        p_dir = phekb_dir_for(name)
        p_data = phekb_summary(p_dir) if p_dir else None
        t = tier(m_complex, p_data)
        rows.append({
            "name": name,
            "module": mod.name,
            "module_codes": m_codes,
            "module_complex": m_complex,
            "phekb_dir": p_dir.name if p_dir else None,
            "phekb_data": p_data,
            "tier": t,
        })

    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        f.write("# Phenotype Audit vs PheKB Raw Docs\n\n")
        f.write(f"Generated: comparing {len(rows)} modules in `synthea/modules/custom/` against `data/phekb-raw/`.\n\n")
        f.write("**Tier definitions:**\n")
        f.write("- **T1-significant-gap**: PheKB doc lists >=8 codes OR has lab thresholds OR has temporal logic. Module likely under-models the algorithm.\n")
        f.write("- **T2-minor-gap**: PheKB doc lists 3-7 codes. Module probably covers the basics but may miss some code variants.\n")
        f.write("- **T3-aligned**: PheKB doc has 0-2 codes (or matches module complexity).\n")
        f.write("- **T3-no-phekb**: No matching PheKB raw dir — clinical-knowledge-only phenotype.\n\n")
        # tier counts
        tier_counts = defaultdict(int)
        for r in rows:
            tier_counts[r["tier"]] += 1
        f.write("## Tier counts\n\n")
        for k in sorted(tier_counts):
            f.write(f"- **{k}**: {tier_counts[k]}\n")
        f.write("\n")

        # Sort: T1 first, then T2, T3-aligned, T3-no-phekb
        order = {"T1-significant-gap": 0, "T2-minor-gap": 1, "T3-aligned": 2, "T3-no-phekb": 3}
        rows.sort(key=lambda r: (order.get(r["tier"], 9), r["name"]))

        f.write("## Phenotype-by-phenotype\n\n")
        f.write("| # | Phenotype | Tier | Module codes | Module paths | PheKB dir | PheKB codes | PheKB has labs/thresholds? | PheKB has temporal? |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for i, r in enumerate(rows, 1):
            mc = r["module_codes"]
            mc_str = f"S:{len(mc['SNOMED'])} R:{len(mc['RXNORM'])} L:{len(mc['LOINC'])}"
            mcx = r["module_complex"]
            paths_str = f"{mcx['path_count']}p {'M' if mcx['has_med'] else ''}{'L' if mcx['has_obs'] else ''}{'P' if mcx['has_proc'] else ''}".strip()
            if r["phekb_data"]:
                pcodes = r["phekb_data"]["codes_by_system"]
                pc_str = ", ".join(f"{s}:{n}" for s, n in sorted(pcodes.items(), key=lambda x: -x[1]))
                summary = r["phekb_data"]["algorithm_summary"].lower()
                has_thresh = "yes" if any(kw in summary for kw in ["threshold", "x uln", ">=", "≥", "ratio"]) else "no"
                has_temp = "yes" if any(kw in summary for kw in ["temporal", "prior to", "within"]) else "no"
                phekb_dir_disp = r["phekb_dir"]
            else:
                pc_str = "—"
                has_thresh = "—"
                has_temp = "—"
                phekb_dir_disp = "—"
            f.write(f"| {i} | {r['name']} | {r['tier']} | {mc_str} | {paths_str} | {phekb_dir_disp} | {pc_str} | {has_thresh} | {has_temp} |\n")

        # Detail section for T1
        f.write("\n## T1 Significant-Gap Details\n\n")
        for r in rows:
            if r["tier"] != "T1-significant-gap":
                continue
            f.write(f"### {r['name']}\n\n")
            f.write(f"- PheKB dir: `data/phekb-raw/{r['phekb_dir']}/`\n")
            pcodes = r["phekb_data"]["codes_by_system"]
            f.write(f"- PheKB codes: {dict(pcodes)}\n")
            f.write(f"- Module codes: SNOMED={sorted(r['module_codes']['SNOMED'])}, RxNorm={sorted(r['module_codes']['RXNORM'])}, LOINC={sorted(r['module_codes']['LOINC'])}\n")
            files = r["phekb_data"].get("files", [])
            if files:
                f.write(f"- PheKB files to read: {files}\n")
            summary = r["phekb_data"]["algorithm_summary"]
            if summary:
                f.write(f"- Algorithm summary: {summary[:300]}{'...' if len(summary) > 300 else ''}\n")
            f.write("\n")

    print(f"Wrote {OUT}")
    print(f"Rows: {len(rows)}")
    for k in sorted(tier_counts):
        print(f"  {k}: {tier_counts[k]}")


if __name__ == "__main__":
    main()
