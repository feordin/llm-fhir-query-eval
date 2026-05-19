# backend/tests/test_scripts/test_patch_control_module.py
"""Unit tests for the control-module mimicker patcher."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from patch_control_module import patch_control  # noqa: E402


# Minimal control module (mimics the asthma control shape)
BASE_MODULE = {
    "name": "PheKB Test Control",
    "states": {
        "Initial": {"type": "Initial", "direct_transition": "Wellness_Encounter"},
        "Wellness_Encounter": {
            "type": "Encounter",
            "encounter_class": "wellness",
            "direct_transition": "End_Wellness_Encounter",
        },
        "End_Wellness_Encounter": {
            "type": "EncounterEnd",
            "direct_transition": "Terminal_Control",
        },
        "Terminal_Control": {"type": "Terminal"},
    },
}


def test_patch_adds_one_mimicker_with_prevalence():
    mod = copy.deepcopy(BASE_MODULE)
    pack = [{"display": "Chronic obstructive lung disease", "prevalence": 0.2}]
    codes = {
        "Chronic obstructive lung disease": {
            "system": "http://snomed.info/sct",
            "code": "13645005",
            "display": "Chronic obstructive lung disease (disorder)",
        },
    }
    patched = patch_control(mod, pack, codes)

    # A new Maybe_Mimicker_<safe> state should exist, before the wellness end
    new_states = set(patched["states"]) - set(BASE_MODULE["states"])
    assert any(s.startswith("Maybe_Mimicker_") for s in new_states)
    assert any(s.startswith("Diagnose_Mimicker_") for s in new_states)

    # Wellness_Encounter should now transition into the FIRST mimicker gate,
    # not directly to End_Wellness_Encounter.
    next_state = patched["states"]["Wellness_Encounter"]["direct_transition"]
    assert next_state.startswith("Maybe_Mimicker_")

    # The Diagnose_Mimicker state carries the correct SNOMED code
    diag_state = next(patched["states"][s] for s in new_states
                      if s.startswith("Diagnose_Mimicker_"))
    assert diag_state["type"] == "ConditionOnset"
    assert diag_state["codes"][0]["code"] == "13645005"


def test_patch_with_multiple_mimickers_chains_gates():
    mod = copy.deepcopy(BASE_MODULE)
    pack = [
        {"display": "Chronic obstructive lung disease", "prevalence": 0.2},
        {"display": "Bronchiectasis", "prevalence": 0.05},
    ]
    codes = {
        "Chronic obstructive lung disease": {
            "system": "http://snomed.info/sct", "code": "13645005",
            "display": "COPD",
        },
        "Bronchiectasis": {
            "system": "http://snomed.info/sct", "code": "12295008",
            "display": "Bronchiectasis",
        },
    }
    patched = patch_control(mod, pack, codes)
    new_states = sorted(set(patched["states"]) - set(BASE_MODULE["states"]))
    # 2 gates + 2 diagnose states
    gates = [s for s in new_states if s.startswith("Maybe_Mimicker_")]
    diagnoses = [s for s in new_states if s.startswith("Diagnose_Mimicker_")]
    assert len(gates) == 2
    assert len(diagnoses) == 2


def test_patch_is_idempotent():
    mod = copy.deepcopy(BASE_MODULE)
    pack = [{"display": "Chronic obstructive lung disease", "prevalence": 0.2}]
    codes = {
        "Chronic obstructive lung disease": {
            "system": "http://snomed.info/sct", "code": "13645005",
            "display": "COPD",
        },
    }
    patched_once = patch_control(mod, pack, codes)
    patched_twice = patch_control(copy.deepcopy(patched_once), pack, codes)
    # Second application should be a no-op
    assert set(patched_twice["states"]) == set(patched_once["states"])


def test_patch_skips_mimicker_without_code():
    mod = copy.deepcopy(BASE_MODULE)
    pack = [{"display": "Unresolved mimicker", "prevalence": 0.1}]
    patched = patch_control(mod, pack, codes={})  # empty codes map
    # No new states should be added; module unchanged
    assert set(patched["states"]) == set(BASE_MODULE["states"])
