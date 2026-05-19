"""Throwaway: write the combined Q1+Q4 audit + proposed mimickers as markdown."""
import json
import glob
from pathlib import Path


def detect_paths(state_names):
    has_a = any("_WithDx" in s or "Path_A" in s for s in state_names)
    has_b = any("NoMeds" in s or "Path_B" in s for s in state_names)
    has_c = any("_NoDx" in s or "Path_C" in s for s in state_names)
    has_d = any("LabsOnly" in s or "Path_D" in s or "Labs_Only" in s for s in state_names)
    return has_a, has_b, has_c, has_d


# Curated clinical differentials per phenotype (where I have confident clinical knowledge).
MIMICKERS = {
    "asthma": ["COPD", "Chronic bronchitis", "Eosinophilic bronchitis", "Vocal cord dysfunction"],
    "copd": ["Asthma", "Bronchiectasis", "Heart failure", "Pulmonary fibrosis"],
    "type_1_diabetes": ["Type 2 diabetes", "MODY", "LADA"],
    "type_2_diabetes": ["Type 1 diabetes", "Gestational diabetes", "Prediabetes"],
    "hypertension": ["White coat hypertension", "Secondary HTN (renal)", "Preeclampsia"],
    "heart_failure": ["COPD", "Pulmonary embolism", "Liver cirrhosis", "CKD"],
    "coronary_heart_disease": ["GERD", "Costochondritis", "Pericarditis", "Aortic dissection"],
    "atrial_fibrillation": ["Atrial flutter", "MAT", "SVT", "Sinus tachycardia"],
    "stroke": ["TIA", "Migraine with aura", "Bell palsy", "Hypoglycemia", "Seizure"],
    "depression": ["Bipolar disorder", "Adjustment disorder", "Hypothyroidism", "Anemia"],
    "anxiety": ["Hyperthyroidism", "Pheochromocytoma", "Cardiac arrhythmia"],
    "bipolar_disorder": ["Major depression (unipolar)", "Cyclothymia", "Borderline PD", "Substance-induced mood"],
    "schizophrenia": ["Schizoaffective disorder", "Bipolar with psychosis", "Substance-induced psychosis"],
    "dementia": ["Mild cognitive impairment", "Depression (pseudodementia)", "Delirium", "Normal aging"],
    "ckd": ["AKI", "Polycystic kidney disease", "Glomerulonephritis"],
    "acute_kidney_injury": ["CKD", "Dehydration", "Urinary obstruction"],
    "rheumatoid_arthritis": ["Osteoarthritis", "Psoriatic arthritis", "Lupus", "Fibromyalgia"],
    "systemic_lupus_erythematosus": ["RA", "Sjogren syndrome", "MCTD"],
    "crohns_disease": ["UC", "IBS", "Celiac disease", "Microscopic colitis"],
    "ulcerative_colitis": ["Crohn disease", "Infectious colitis", "Ischemic colitis", "IBS"],
    "gerd": ["Peptic ulcer", "Eosinophilic esophagitis", "Functional dyspepsia", "Cardiac chest pain"],
    "migraine": ["Tension headache", "Cluster headache", "MOH", "Sinusitis"],
    "epilepsy": ["Syncope", "PNES", "TIA", "Migraine"],
    "parkinsons_disease": ["Essential tremor", "Drug-induced parkinsonism", "Lewy body dementia"],
    "multiple_sclerosis": ["Neuromyelitis optica", "ADEM", "Migraine", "B12 deficiency"],
    "hypothyroidism": ["Depression", "Anemia", "CFS", "Sick euthyroid"],
    "hyperthyroidism": ["Anxiety disorder", "Pheochromocytoma", "Substance use"],
    "iron_deficiency_anemia": ["Anemia of chronic disease", "Thalassemia trait", "B12 deficiency"],
    "osteoporosis": ["Osteopenia", "Osteomalacia", "Multiple myeloma"],
    "fibromyalgia": ["CFS", "Polymyalgia rheumatica", "Hypothyroidism"],
    "gout": ["Pseudogout (CPPD)", "Septic arthritis", "RA"],
    "venous_thromboembolism": ["Cellulitis", "Baker cyst", "Muscle strain"],
    "pneumonia": ["Bronchitis", "COPD exacerbation", "Asthma exacerbation", "Heart failure"],
    "atopic_dermatitis": ["Contact dermatitis", "Psoriasis", "Seborrheic dermatitis"],
    "psoriasis": ["Atopic dermatitis", "Seborrheic dermatitis", "Tinea corporis"],
}


def main():
    rows = []
    for f in sorted(glob.glob("synthea/modules/custom/phekb_*.json")):
        name = Path(f).stem
        if name.endswith("_control"):
            continue
        pheno = name.replace("phekb_", "")
        pos = json.load(open(f, encoding="utf-8"))
        state_names = list(pos.get("states", {}).keys())
        has_a, has_b, has_c, has_d = detect_paths(state_names)

        ctrl_path = Path("synthea/modules/custom") / f"phekb_{pheno}_control.json"
        existing_ctrls = []
        if ctrl_path.exists():
            ctrl = json.load(open(ctrl_path, encoding="utf-8"))
            for s in ctrl.get("states", {}).values():
                if s.get("type") == "ConditionOnset":
                    for c in s.get("codes", []):
                        existing_ctrls.append(c.get("display", "?"))
        rows.append((pheno, has_a, has_b, has_c, has_d, existing_ctrls,
                     MIMICKERS.get(pheno)))

    lines = [
        "# Test-data rigor audit -- 2026-05-17",
        "",
        "Surfaced while investigating asthma-comprehensive == asthma-meds == 76.",
        "",
        "## Q1 -- Path B (dx-only) coverage across phenotype modules",
        "",
        "The 3-path Synthea template (A: dx+meds, B: dx-only, C: meds-only, D: labs-only)",
        "is the mechanism for generating realistic messy records. Where Path B is absent,",
        "every diagnosed patient is also on meds, so dx is a subset of meds and",
        "`comprehensive == meds` for those phenotypes.",
        "",
        "| Phenotype | A | B | C | D | Notes |",
        "|---|:-:|:-:|:-:|:-:|---|",
    ]
    for pheno, a, b, c, d, _, _ in rows:
        missing = ''.join(p for p, on in zip("ABC", (a, b, c)) if not on)
        note = "" if not missing else f"missing path(s): {missing}"
        flags = ('A' if a else '-') + ('B' if b else '-') + ('C' if c else '-') + ('D' if d else '-')
        lines.append(f"| `{pheno}` | {'y' if a else '-'} | {'y' if b else '-'} | {'y' if c else '-'} | {'y' if d else '-'} | {note} |")

    lines += [
        "",
        "## Q4 -- Control rigor: existing comorbidities + proposed mimicker upgrades",
        "",
        "Of 108 control modules, 94 have NO conditions modeled (pure-healthy).",
        "F1 scores against pure-healthy controls overstate true model skill: broad",
        "queries cannot be falsely matched if controls have nothing to match.",
        "",
        "Proposed mimickers are clinically recognized differential diagnoses;",
        "SNOMED codes still need UMLS/VSAC lookup before module edits.",
        "",
        "| Phenotype | Current control conditions | Proposed mimickers to add |",
        "|---|---|---|",
    ]
    for pheno, _, _, _, _, existing, proposed in rows:
        e = ", ".join(existing) if existing else "*(pure-healthy)*"
        p = ", ".join(proposed) if proposed else "*(needs research)*"
        lines.append(f"| `{pheno}` | {e} | {p} |")

    lines += [
        "",
        "## Summary stats",
        "",
        f"- Phenotypes missing Path B: {sum(1 for r in rows if not r[2])}",
        f"- Phenotypes missing Path C: {sum(1 for r in rows if not r[3])}",
        f"- Phenotypes with pure-healthy controls: {sum(1 for r in rows if not r[5])}",
        f"- Phenotypes with proposed mimicker pack: {sum(1 for r in rows if r[6])}",
        f"- Phenotypes still needing mimicker research: {sum(1 for r in rows if not r[6])}",
        "",
    ]
    out = Path("docs/audits/2026-05-17-test-data-rigor-audit.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
