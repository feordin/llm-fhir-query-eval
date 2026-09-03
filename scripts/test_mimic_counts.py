"""Tests for MIMIC per-phenotype counting core (ICD normalization + prefix match).

Run: python -m pytest scripts/test_mimic_counts.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mimic_phenotype_counts import (
    normalize_icd, icd_matches, parse_value_quantity, value_meets,
)


# --- normalize_icd: strip dots, uppercase ------------------------------------
def test_normalize_strips_dot_icd10():
    assert normalize_icd("E11.9") == "E119"

def test_normalize_strips_dot_icd9():
    assert normalize_icd("571.5") == "5715"

def test_normalize_uppercases():
    assert normalize_icd("e11.9") == "E119"

def test_normalize_already_bare():
    assert normalize_icd("E119") == "E119"


# --- icd_matches: phenotype code is a prefix of the MIMIC code ---------------
def test_category_code_matches_subcode():
    # phenotype carries category E11; MIMIC has specific E11.9 -> match
    assert icd_matches("E119", {"E11"}) is True

def test_exact_code_matches():
    assert icd_matches("5715", {"5715"}) is True

def test_three_digit_category_matches_icd9_subcode():
    # diabetes category 250 should match 250.00 (-> 25000)
    assert icd_matches("25000", {"250"}) is True

def test_non_matching_sibling_does_not_match():
    assert icd_matches("E119", {"E10"}) is False

def test_no_codes_no_match():
    assert icd_matches("E119", set()) is False

def test_match_is_normalization_agnostic_on_phenotype_side():
    # phenotype code provided dotted should still match
    assert icd_matches("I714", {"I71.4"}) is True


# --- parse_value_quantity: FHIR <comp><value>|system|unit ---------------------
def test_parse_vq_with_unit_suffix():
    assert parse_value_quantity("ge6.5||%") == ("ge", 6.5)

def test_parse_vq_bare():
    assert parse_value_quantity("lt60") == ("lt", 60.0)

def test_parse_vq_integerish():
    assert parse_value_quantity("gt7") == ("gt", 7.0)

def test_parse_vq_negative_threshold():
    # osteoporosis T-score <= -2.5
    assert parse_value_quantity("le-2.5") == ("le", -2.5)

def test_parse_vq_tolerates_trailing_dot():
    assert parse_value_quantity("ge190.") == ("ge", 190.0)


# --- value_meets: comparator semantics --------------------------------------
def test_ge_inclusive():
    assert value_meets(7.0, "ge", 6.5) is True
    assert value_meets(6.5, "ge", 6.5) is True
    assert value_meets(6.4, "ge", 6.5) is False

def test_gt_exclusive():
    assert value_meets(8.0, "gt", 7.0) is True
    assert value_meets(7.0, "gt", 7.0) is False

def test_lt_exclusive():
    assert value_meets(50, "lt", 60) is True
    assert value_meets(60, "lt", 60) is False

def test_le_with_negative_threshold():
    # T-score -3.0 <= -2.5 -> meets; -2.0 does not
    assert value_meets(-3.0, "le", -2.5) is True
    assert value_meets(-2.0, "le", -2.5) is False


# --- _valid_icd: reject URL-scrape junk, accept real codes + categories ------
from mimic_phenotype_counts import _valid_icd

def test_valid_icd10_specific_and_category():
    assert _valid_icd("icd10cm", "E11.9") is True
    assert _valid_icd("icd10cm", "E11") is True
    assert _valid_icd("icd10cm", "I1A.0") is True  # new-style I1A resistant HTN

def test_valid_icd10_rejects_junk():
    assert _valid_icd("icd10cm", 'E11"]') is False
    assert _valid_icd("icd10cm", "E10.x") is False
    assert _valid_icd("icd10cm", "A15-A19") is False  # range notation

def test_valid_icd9_shapes():
    assert _valid_icd("icd9cm", "250.01") is True
    assert _valid_icd("icd9cm", "250") is True
    assert _valid_icd("icd9cm", "E950.0") is True
    assert _valid_icd("icd9cm", "V45.1") is True

def test_valid_icd9_rejects_junk_and_procedure_codes():
    assert _valid_icd("icd9cm", "250.(0-9)0") is False
    assert _valid_icd("icd9cm", "37.51") is False   # 2-digit proc would prefix-match dx 375.x
    assert _valid_icd("icd9cm", "010-018.99") is False

def test_valid_icd10pcs():
    assert _valid_icd("icd10pcs", "02100Z9") is True
    assert _valid_icd("icd10pcs", "A15-A19") is False
