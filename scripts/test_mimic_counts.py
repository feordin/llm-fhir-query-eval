"""Tests for MIMIC per-phenotype counting core (ICD normalization + prefix match).

Run: python -m pytest scripts/test_mimic_counts.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mimic_phenotype_counts import normalize_icd, icd_matches


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
