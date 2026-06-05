"""Tests for MIMIC FHIR code standardization (ICD re-dotting + coding injection).

Run: python -m pytest scripts/test_standardize_mimic.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from standardize_mimic_fhir import redot_icd, ICD10CM, ICD9CM, ICD10PCS, add_standard_codings


# --- ICD-10-CM diagnosis: dot after 3rd char when len > 3 -------------------
def test_icd10cm_inserts_dot_after_third_char():
    assert redot_icd("E119", "diagnosis-icd10") == "E11.9"

def test_icd10cm_longer_code():
    assert redot_icd("A4151", "diagnosis-icd10") == "A41.51"

def test_icd10cm_three_char_code_unchanged():
    assert redot_icd("E11", "diagnosis-icd10") == "E11"

def test_icd10cm_already_dotted_is_idempotent():
    assert redot_icd("E11.9", "diagnosis-icd10") == "E11.9"


# --- ICD-9-CM diagnosis: numeric/V dot after 3rd, E after 4th ----------------
def test_icd9cm_numeric_dot_after_third_digit():
    assert redot_icd("5715", "diagnosis-icd9") == "571.5"

def test_icd9cm_numeric_five_digit():
    assert redot_icd("45829", "diagnosis-icd9") == "458.29"

def test_icd9cm_three_digit_unchanged():
    assert redot_icd("250", "diagnosis-icd9") == "250"

def test_icd9cm_v_code_dot_after_third_char():
    assert redot_icd("V462", "diagnosis-icd9") == "V46.2"

def test_icd9cm_v_code_longer():
    assert redot_icd("V4986", "diagnosis-icd9") == "V49.86"

def test_icd9cm_e_code_dot_after_fourth_char():
    assert redot_icd("E8889", "diagnosis-icd9") == "E888.9"


# --- ICD-9 procedure: dot after 2nd char ------------------------------------
def test_icd9_procedure_dot_after_second_char():
    assert redot_icd("5491", "procedure-icd9") == "54.91"

def test_icd9_procedure_two_char_unchanged():
    assert redot_icd("54", "procedure-icd9") == "54"


# --- ICD-10-PCS procedure: never dotted -------------------------------------
def test_icd10pcs_never_dotted():
    assert redot_icd("3E0G76Z", "procedure-icd10") == "3E0G76Z"


# --- add_standard_codings: additive, preserves original ----------------------
def test_add_standard_coding_is_additive_for_condition():
    resource = {
        "resourceType": "Condition",
        "code": {"coding": [
            {"system": "http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10",
             "code": "E119", "display": "Type 2 diabetes mellitus"}
        ]},
    }
    out = add_standard_codings(resource, loinc_map={})
    systems = [c["system"] for c in out["code"]["coding"]]
    # original kept
    assert "http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10" in systems
    # standard added with dotted code
    std = [c for c in out["code"]["coding"] if c["system"] == ICD10CM]
    assert len(std) == 1
    assert std[0]["code"] == "E11.9"
    assert std[0]["display"] == "Type 2 diabetes mellitus"

def test_add_standard_coding_loinc_for_lab():
    resource = {
        "resourceType": "Observation",
        "code": {"coding": [
            {"system": "http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems",
             "code": "50885", "display": "Bilirubin, Total"}
        ]},
    }
    out = add_standard_codings(resource, loinc_map={"50885": "1975-2"})
    loinc = [c for c in out["code"]["coding"] if c["system"] == "http://loinc.org"]
    assert len(loinc) == 1
    assert loinc[0]["code"] == "1975-2"

def test_add_standard_coding_lab_without_map_entry_unchanged():
    resource = {
        "resourceType": "Observation",
        "code": {"coding": [
            {"system": "http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems",
             "code": "99999", "display": "Unmapped"}
        ]},
    }
    out = add_standard_codings(resource, loinc_map={"50885": "1975-2"})
    systems = [c["system"] for c in out["code"]["coding"]]
    assert "http://loinc.org" not in systems
    assert len(out["code"]["coding"]) == 1
