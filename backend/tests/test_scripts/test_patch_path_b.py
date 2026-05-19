# backend/tests/test_scripts/test_patch_path_b.py
"""Unit tests for the Path B (dx-only) patcher. Only handles the canonical
'Choose_Patient_Path' -> Set_Path_A/C shape; other shapes are skipped with
a warning."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from patch_path_b import patch_path_b, has_path_b  # noqa: E402


CANONICAL_MODULE = {
    "name": "TestPheno",
    "states": {
        "Initial": {"type": "Initial", "direct_transition": "Choose_Patient_Path"},
        "Choose_Patient_Path": {
            "type": "Simple",
            "distributed_transition": [
                {"transition": "Set_Path_A", "distribution": 0.7},
                {"transition": "Set_Path_C", "distribution": 0.3},
            ],
        },
        "Set_Path_A": {
            "type": "SetAttribute", "attribute": "path", "value": "A",
            "direct_transition": "Wellness_Encounter",
        },
        "Set_Path_C": {
            "type": "SetAttribute", "attribute": "path", "value": "C",
            "direct_transition": "Wellness_Encounter",
        },
        "Wellness_Encounter": {"type": "Encounter", "direct_transition": "Terminal"},
        "Terminal": {"type": "Terminal"},
    },
}


def test_has_path_b_detects_missing_state():
    assert has_path_b(CANONICAL_MODULE) is False


def test_has_path_b_detects_present_state():
    mod = copy.deepcopy(CANONICAL_MODULE)
    mod["states"]["Set_Path_B"] = {"type": "SetAttribute", "attribute": "path", "value": "B"}
    assert has_path_b(mod) is True


def test_patch_path_b_adds_state_and_rebalances():
    mod = copy.deepcopy(CANONICAL_MODULE)
    patched = patch_path_b(mod, prevalence=0.15)
    # Set_Path_B state exists
    assert "Set_Path_B" in patched["states"]
    assert patched["states"]["Set_Path_B"]["value"] == "B"
    # Choose_Patient_Path now includes Set_Path_B with the given weight
    choices = patched["states"]["Choose_Patient_Path"]["distributed_transition"]
    targets = {c["transition"]: c["distribution"] for c in choices}
    assert "Set_Path_B" in targets
    assert abs(targets["Set_Path_B"] - 0.15) < 1e-9
    # Distributions still sum to ~1
    total = sum(c["distribution"] for c in choices)
    assert abs(total - 1.0) < 1e-9


def test_patch_path_b_idempotent_on_already_patched():
    mod = copy.deepcopy(CANONICAL_MODULE)
    once = patch_path_b(mod, prevalence=0.15)
    twice = patch_path_b(copy.deepcopy(once), prevalence=0.15)
    # State count unchanged on second application
    assert set(twice["states"]) == set(once["states"])


def test_patch_path_b_skips_unrecognized_module_shape():
    """If module has no Choose_Patient_Path, return unchanged (caller logs)."""
    mod = {"name": "X", "states": {"Initial": {"type": "Initial"}}}
    patched = patch_path_b(copy.deepcopy(mod), prevalence=0.15)
    assert patched == mod
