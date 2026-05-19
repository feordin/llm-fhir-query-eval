# scripts/patch_control_module.py
"""Patch a control Synthea module with prevalence-weighted mimicker conditions.

For each mimicker in the phenotype's pack, insert a gate state (distributed
transition: prevalence -> Diagnose, 1-prevalence -> next gate) followed by a
ConditionOnset state carrying the SNOMED code. Gates are chained in order;
the last gate transitions back to the original Wellness_Encounter next state.

The patcher is idempotent: re-running detects existing Diagnose_Mimicker_*
states by SNOMED code and skips already-added mimickers.

Usage:
    python scripts/patch_control_module.py <phenotype>

Reads:
- data/mimicker_packs.json[<phenotype>]
- data/mimicker_codes.json (term -> code mapping)
- synthea/modules/custom/phekb_<phenotype>_control.json (in-place edit)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PACKS = REPO / "data" / "mimicker_packs.json"
CODES = REPO / "data" / "mimicker_codes.json"
MODULES_DIR = REPO / "synthea" / "modules" / "custom"


def _safe(name: str) -> str:
    """Make a display string safe for a Synthea state name (alphanumeric + _)."""
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")


def _already_present(module: dict, code: str) -> bool:
    """True if a ConditionOnset state with this SNOMED code already exists."""
    for s in module.get("states", {}).values():
        if s.get("type") == "ConditionOnset":
            for c in s.get("codes", []):
                if c.get("code") == code:
                    return True
    return False


def patch_control(module: dict, pack: list[dict], codes: dict) -> dict:
    """Add mimicker gate + diagnose states to a control module.

    Args:
        module: parsed Synthea module dict
        pack: [{"display": str, "prevalence": float}, ...]
        codes: {display_string: {"system","code","display"}}

    Returns:
        modified module (also mutates `module` in place for convenience)
    """
    states = module.setdefault("states", {})
    # Find the wellness entry transition we'll splice into.
    wellness = states.get("Wellness_Encounter")
    if not wellness or "direct_transition" not in wellness:
        # No splice point -- skip patching.
        return module
    original_next = wellness["direct_transition"]

    # Build the new gate+diagnose pairs in order, skipping cached/unresolved/dup.
    new_chain: list[tuple[str, dict, str, dict]] = []  # (gate_name, gate, diag_name, diag)
    for mimicker in pack:
        display = mimicker["display"]
        prevalence = float(mimicker["prevalence"])
        if display not in codes:
            continue  # unresolved code -- skip
        code_info = codes[display]
        if _already_present(module, code_info["code"]):
            continue  # idempotent: already patched in
        safe = _safe(display)
        gate_name = f"Maybe_Mimicker_{safe}"
        diag_name = f"Diagnose_Mimicker_{safe}"
        gate = {
            "type": "Simple",
            "distributed_transition": [
                {"transition": diag_name, "distribution": prevalence},
                {"transition": "__PLACEHOLDER__", "distribution": 1.0 - prevalence},
            ],
        }
        diag = {
            "type": "ConditionOnset",
            "codes": [{
                "system": code_info["system"],
                "code": code_info["code"],
                "display": code_info["display"],
            }],
            "direct_transition": "__PLACEHOLDER__",
        }
        new_chain.append((gate_name, gate, diag_name, diag))

    if not new_chain:
        return module  # nothing to add

    # Wire the chain: each gate's "skip" branch goes to the NEXT gate; last
    # gate's skip goes to original_next. Each diagnose state continues to its
    # own gate's skip target.
    for i, (gate_name, gate, diag_name, diag) in enumerate(new_chain):
        skip_target = new_chain[i + 1][0] if i + 1 < len(new_chain) else original_next
        gate["distributed_transition"][1]["transition"] = skip_target
        diag["direct_transition"] = skip_target
        states[gate_name] = gate
        states[diag_name] = diag

    # Splice: Wellness_Encounter -> first new gate
    wellness["direct_transition"] = new_chain[0][0]
    return module


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phenotype")
    args = ap.parse_args()

    packs = json.loads(PACKS.read_text(encoding="utf-8"))
    if args.phenotype not in packs:
        print(f"no pack defined for '{args.phenotype}' in {PACKS}")
        return 1
    codes = json.loads(CODES.read_text(encoding="utf-8")) if CODES.exists() else {}

    mod_path = MODULES_DIR / f"phekb_{args.phenotype}_control.json"
    if not mod_path.exists():
        print(f"missing {mod_path}")
        return 1

    module = json.loads(mod_path.read_text(encoding="utf-8"))
    n_before = sum(1 for s in module.get("states", {}).values()
                   if s.get("type") == "ConditionOnset")
    patch_control(module, packs[args.phenotype], codes)
    n_after = sum(1 for s in module.get("states", {}).values()
                  if s.get("type") == "ConditionOnset")
    added = n_after - n_before

    mod_path.write_text(json.dumps(module, indent=2) + "\n", encoding="utf-8")
    print(f"{args.phenotype}: {added} mimicker(s) added "
          f"({n_after} total ConditionOnset states)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
