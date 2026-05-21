"""Tests for SNOMED :below/:above subsumption-modifier stripping.

The Azure Microsoft FHIR server has no terminology hierarchy loaded, so
subsumption queries return zero. Our synthetic data is flat, so the modifier
is rewritten to a plain code= before execution.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from fhir.client import strip_subsumption_modifiers  # noqa: E402


def test_strips_code_below():
    url = "Condition?code:below=http://snomed.info/sct|195967001"
    assert strip_subsumption_modifiers(url) == (
        "Condition?code=http://snomed.info/sct|195967001"
    )


def test_strips_code_above():
    url = "Condition?code:above=http://snomed.info/sct|123"
    assert strip_subsumption_modifiers(url) == (
        "Condition?code=http://snomed.info/sct|123"
    )


def test_plain_code_unchanged():
    url = "Condition?code=http://snomed.info/sct|195967001"
    assert strip_subsumption_modifiers(url) == url


def test_include_modifier_not_mangled():
    """_include=Condition:subject has a colon but is not a subsumption
    modifier -- it must survive untouched."""
    url = ("Condition?code:below=http://snomed.info/sct|195967001"
           "&_include=Condition:subject")
    assert strip_subsumption_modifiers(url) == (
        "Condition?code=http://snomed.info/sct|195967001"
        "&_include=Condition:subject"
    )


def test_multiple_modifiers_all_stripped():
    url = ("Observation?code:below=http://loinc.org|1234"
           "&component-code:above=http://loinc.org|5678")
    assert strip_subsumption_modifiers(url) == (
        "Observation?code=http://loinc.org|1234"
        "&component-code=http://loinc.org|5678"
    )
