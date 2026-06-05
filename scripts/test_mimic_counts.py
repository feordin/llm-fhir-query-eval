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
