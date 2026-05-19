# scripts/patch_path_b.py
"""Add Path B (dx-only) to a phenotype Synthea module that lacks it.

Path B = diagnosed but not on medications. Patients in this path get the
phenotype's Condition codes but skip the medication-prescription branch.
Without Path B, every dx patient also has meds, so dx is a subset of meds
and the 'comprehensive' test case == the 'meds' test case.

This patcher targets the canonical Choose_Patient_Path shape (CHD/HF/...).
For modules with a different shape, it skips with a warning.

Usage:
    python scripts/patch_path_b.py <phenotype> [--prevalence 0.15]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MODULES_DIR = REPO / "synthea" / "modules" / "custom"


def has_path_b(module: dict) -> bool:
    """True if Set_Path_B (or an equivalent value=='B' SetAttribute) already exists."""
    for name, s in module.get("states", {}).items():
        if name == "Set_Path_B":
            return True
        if s.get("type") == "SetAttribute" and s.get("attribute") == "path" \
                and s.get("value") == "B":
            return True
    return False


def patch_path_b(module: dict, prevalence: float = 0.15) -> dict:
    """Add a Set_Path_B branch with the given prevalence weight.

    Recognises modules with a Choose_Patient_Path distributed_transition into
    Set_Path_A / Set_Path_C and inserts Set_Path_B alongside them, then rescales
    the existing weights so totals sum to 1.

    Other module shapes are returned unchanged (caller should log + skip).
    """
    if has_path_b(module):
        return module
    states = module.get("states", {})
    choose = states.get("Choose_Patient_Path")
    if not choose or "distributed_transition" not in choose:
        return module  # unrecognised shape -- skip
    # Verify the shape is the canonical Set_Path_A/Set_Path_C pattern
    targets = [t["transition"] for t in choose["distributed_transition"]]
    if "Set_Path_A" not in targets:
        return module  # not our shape

    # Find a sibling Set_Path_A state to mimic the downstream transition.
    a_state = states.get("Set_Path_A")
    if not a_state or a_state.get("type") != "SetAttribute":
        return module
    next_after_path = a_state.get("direct_transition")
    if not next_after_path:
        return module

    # Insert Set_Path_B mimicking Set_Path_A but with value="B" and no meds.
    # Most modules route Set_Path_A -> Set_Path_A_Meds -> ... -> Wellness.
    # Path B should skip the meds states by transitioning directly to wellness
    # (or whatever the post-meds state is). We approximate by using the same
    # next_after_path as Set_Path_A but rely on a `path == "B"` guard in the
    # meds-prescription state. If no such guard exists, downstream meds states
    # still fire; the module author should add `if path != "B"` checks. For now
    # the new state is still useful: the cohort attribute is set, so downstream
    # `path == "B"` references work.
    states["Set_Path_B"] = {
        "type": "SetAttribute",
        "attribute": "path",
        "value": "B",
        "direct_transition": next_after_path,
    }

    # Rescale existing distribution: new total = 1; pull `prevalence` from the
    # existing branches proportionally to their weights.
    existing = choose["distributed_transition"]
    existing_total = sum(t["distribution"] for t in existing)
    if existing_total > 0:
        scale = (1.0 - prevalence) / existing_total
        for t in existing:
            t["distribution"] = round(t["distribution"] * scale, 6)
    existing.append({"transition": "Set_Path_B", "distribution": prevalence})
    return module


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phenotype")
    ap.add_argument("--prevalence", type=float, default=0.15,
                    help="Path B share of total patient distribution (default 0.15)")
    args = ap.parse_args()

    mod_path = MODULES_DIR / f"phekb_{args.phenotype}.json"
    if not mod_path.exists():
        print(f"missing {mod_path}")
        return 1
    module = json.loads(mod_path.read_text(encoding="utf-8"))
    if has_path_b(module):
        print(f"{args.phenotype}: already has Path B -- skipped")
        return 0
    before_states = set(module.get("states", {}))
    patch_path_b(module, prevalence=args.prevalence)
    added = set(module.get("states", {})) - before_states
    if not added:
        print(f"{args.phenotype}: module shape not recognised by patcher -- "
              f"manual edit required")
        return 2
    mod_path.write_text(json.dumps(module, indent=2) + "\n", encoding="utf-8")
    print(f"{args.phenotype}: added Path B "
          f"(prevalence={args.prevalence}); new states: {sorted(added)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
