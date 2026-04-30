"""Surgically add SNOMED code variation to a Synthea module.

Strategy: take the single ConditionOnset state ``original_diagnose`` and
replace it with a router that distributes patients across ``variants``.

Resulting structure inserted into ``data['states']``:
- ``original_diagnose``                  → SetAttribute(subtype=...) routing dispatcher (overwrites the
                                            old single-code state with a distributed_transition)
- ``original_diagnose__variant_<i>``     → ConditionOnset with the i-th variant code (one per variant)

All variants point to the same downstream ``direct_transition`` as the
original ConditionOnset state. This keeps the rest of the module flow
intact while spreading patients across multiple dx codes.

Usage:
    python scripts/add_snomed_variation.py phekb_type_2_diabetes Diagnose_T2DM
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MODULES_DIR = Path(__file__).resolve().parents[1] / "synthea" / "modules" / "custom"


def add_variation(
    module_filename: str,
    original_diagnose: str,
    variants: list[tuple[float, str, str]],
) -> None:
    """Rewrite module to spread patients across SNOMED variants.

    variants: list of (distribution, code, display). Distributions must sum to 1.0.
    The first variant typically reuses the existing single code so old expected
    patient IDs partially survive.
    """
    path = MODULES_DIR / module_filename
    if not path.exists():
        raise FileNotFoundError(path)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    states = data["states"]
    if original_diagnose not in states:
        raise KeyError(f"State {original_diagnose} not found in {path}")

    old = states[original_diagnose]
    if old.get("type") != "ConditionOnset":
        raise ValueError(
            f"Expected {original_diagnose} to be ConditionOnset, got {old.get('type')}"
        )

    next_state = old.get("direct_transition")
    if not next_state:
        raise ValueError(f"{original_diagnose} has no direct_transition")
    assign_to = old.get("assign_to_attribute")

    total = sum(v[0] for v in variants)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Distributions must sum to 1.0, got {total}")

    # Build variant Diagnose states
    variant_states = []
    for i, (dist, code, display) in enumerate(variants):
        variant_name = f"{original_diagnose}__variant_{i}"
        variant_states.append((dist, variant_name))
        new_state = {
            "type": "ConditionOnset",
            "codes": [
                {"system": "SNOMED-CT", "code": code, "display": display}
            ],
            "direct_transition": next_state,
        }
        if assign_to:
            new_state["assign_to_attribute"] = assign_to
        states[variant_name] = new_state

    # Replace the original ConditionOnset with a Simple distributed_transition
    states[original_diagnose] = {
        "type": "Simple",
        "remarks": old.get("remarks", []) + [
            "Distributes patients across SNOMED variants for code-variation testing."
        ],
        "distributed_transition": [
            {"transition": variant_name, "distribution": round(dist, 4)}
            for dist, variant_name in variant_states
        ],
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Updated {path}: {original_diagnose} now distributes across {len(variants)} variants")
    for dist, name in variant_states:
        print(f"  {dist:.0%} → {name}: {states[name]['codes'][0]['code']} {states[name]['codes'][0]['display']}")


# --------------------------------------------------------------------- #
# CLI invocation: customize variants for each phenotype
# --------------------------------------------------------------------- #
PHENOTYPE_CONFIGS = {
    "phekb_type_2_diabetes.json": {
        "state": "Diagnose_T2DM",
        "variants": [
            (0.60, "44054006", "Type 2 diabetes mellitus"),
            (0.25, "73211009", "Diabetes mellitus"),
            (0.15, "9414007", "Impaired glucose tolerance"),
        ],
    },
    "phekb_adhd.json": {
        "state": "Diagnose_ADHD",
        "variants": [
            (0.50, "406506008", "Attention deficit hyperactivity disorder"),
            (0.30, "31177006", "ADHD combined type"),
            (0.20, "192127007", "Child attention deficit disorder"),
        ],
    },
    "phekb_appendicitis.json": {
        "state": "Appendicitis_Dx_Onset",
        "variants": [
            (0.70, "85189001", "Acute appendicitis"),
            (0.30, "74400008", "Appendicitis"),
        ],
    },
    "phekb_asthma.json": {
        "state": "Diagnose_Asthma",
        "variants": [
            (0.40, "195967001", "Asthma"),
            (0.30, "389145006", "Allergic asthma"),
            (0.20, "233678006", "Childhood asthma"),
            (0.10, "195977004", "Mixed asthma"),
        ],
    },
    "phekb_atopic_dermatitis.json": {
        "state": "Diagnose_Atopic_Dermatitis",
        "variants": [
            (0.70, "24079001", "Atopic dermatitis"),
            (0.30, "43116000", "Eczema"),
        ],
    },
    "phekb_atrial_fibrillation.json": {
        "state": "Diagnose_Atrial_Fibrillation",
        "variants": [
            (0.50, "49436004", "Atrial fibrillation"),
            (0.30, "282825002", "Paroxysmal atrial fibrillation"),
            (0.20, "426749004", "Chronic atrial fibrillation"),
        ],
    },
    "phekb_autism.json": {
        "state": "Diagnose_ASD",
        "variants": [
            (0.50, "35919005", "Pervasive developmental disorder"),
            (0.30, "408856003", "Autistic disorder"),
            (0.20, "23560001", "Asperger's disorder"),
        ],
    },
}


def main():
    if len(sys.argv) > 1:
        # Run for a single phenotype
        for filename in sys.argv[1:]:
            cfg = PHENOTYPE_CONFIGS.get(filename)
            if not cfg:
                print(f"No config for {filename}, skipping")
                continue
            try:
                add_variation(filename, cfg["state"], cfg["variants"])
            except (KeyError, ValueError, FileNotFoundError) as e:
                print(f"FAIL {filename}: {e}")
    else:
        # Run all
        for filename, cfg in PHENOTYPE_CONFIGS.items():
            try:
                add_variation(filename, cfg["state"], cfg["variants"])
            except (KeyError, ValueError, FileNotFoundError) as e:
                print(f"FAIL {filename}: {e}")


if __name__ == "__main__":
    main()
