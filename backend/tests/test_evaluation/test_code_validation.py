"""Tests for CodeSystemValidator."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

backend_path = Path(__file__).resolve().parents[2]
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.test_case import Code
from src.evaluation.code_validation import (
    CodeSystemValidator,
    extract_codes_from_url,
)


FIXTURE_DIR = Path(__file__).resolve().parents[3] / "test-cases" / "phekb"


def _code(system: str, code: str, display: str = "") -> Code:
    return Code(system=system, code=code, display=display, source="test")


# --------------------------------------------------------------------- #
# URL parsing
# --------------------------------------------------------------------- #

def test_parse_simple_code_url():
    pairs = extract_codes_from_url(
        "Condition?code=http://snomed.info/sct|44054006"
    )
    assert pairs == [("http://snomed.info/sct", "44054006")]


def test_parse_multiple_codes_comma_separated():
    pairs = extract_codes_from_url(
        "Condition?code=http://snomed.info/sct|44054006,http://hl7.org/fhir/sid/icd-10-cm|E11"
    )
    assert sorted(pairs) == [
        ("http://hl7.org/fhir/sid/icd-10-cm", "E11"),
        ("http://snomed.info/sct", "44054006"),
    ]


def test_parse_code_without_system():
    pairs = extract_codes_from_url("Condition?code=44054006")
    assert pairs == [(None, "44054006")]


def test_parse_value_quantity_param_ignored():
    """value-quantity is not a code-bearing param — should be skipped."""
    pairs = extract_codes_from_url(
        "Observation?code=http://loinc.org|4548-4&value-quantity=ge6.5"
    )
    assert pairs == [("http://loinc.org", "4548-4")]


def test_parse_has_chained_code():
    pairs = extract_codes_from_url(
        "Patient?_has:Condition:patient:code=http://snomed.info/sct|44054006"
    )
    assert pairs == [("http://snomed.info/sct", "44054006")]


def test_parse_has_composite_code_value_quantity():
    """Composite parameter — strip $ge6.5 suffix, keep system|code."""
    pairs = extract_codes_from_url(
        "Patient?_has:Observation:patient:code-value-quantity=http://loinc.org|4548-4$ge6.5"
    )
    assert pairs == [("http://loinc.org", "4548-4")]


def test_parse_double_has_two_resources():
    pairs = extract_codes_from_url(
        "Patient?_has:Condition:patient:code=http://snomed.info/sct|34000006"
        "&_has:MedicationRequest:patient:code=http://www.nlm.nih.gov/research/umls/rxnorm|327361"
    )
    assert sorted(pairs) == [
        ("http://snomed.info/sct", "34000006"),
        ("http://www.nlm.nih.gov/research/umls/rxnorm", "327361"),
    ]


def test_parse_normalizes_short_system_aliases():
    """LLMs often write 'RxNorm' instead of the full URI — should normalize."""
    pairs = extract_codes_from_url("MedicationRequest?code=RxNorm|11289")
    assert pairs == [("http://www.nlm.nih.gov/research/umls/rxnorm", "11289")]


def test_parse_empty_url():
    assert extract_codes_from_url("") == []
    assert extract_codes_from_url("Patient") == []


# --------------------------------------------------------------------- #
# Validation logic
# --------------------------------------------------------------------- #

def test_perfect_match_passes():
    required = [
        _code("http://snomed.info/sct", "44054006"),
        _code("http://hl7.org/fhir/sid/icd-10-cm", "E11"),
    ]
    urls = [
        "Condition?code=http://snomed.info/sct|44054006,http://hl7.org/fhir/sid/icd-10-cm|E11"
    ]
    result = CodeSystemValidator().evaluate(required, urls)
    assert result.passed is True
    assert sorted(result.correct_systems) == [
        "http://hl7.org/fhir/sid/icd-10-cm",
        "http://snomed.info/sct",
    ]
    assert result.incorrect_systems == []
    assert result.missing_codes == []
    assert result.extra_codes == []


def test_missing_code_does_not_fail_passed_when_systems_match():
    """LLM uses fewer codes than required, but covers all systems → passed=True
    (still 'used the right systems') with codes flagged as missing for diagnostics."""
    required = [
        _code("http://snomed.info/sct", "53741008"),
        _code("http://snomed.info/sct", "414545008"),
        _code("http://snomed.info/sct", "233817007"),
    ]
    urls = ["Condition?code=http://snomed.info/sct|53741008"]
    result = CodeSystemValidator().evaluate(required, urls)
    assert result.passed is True  # right system used
    assert result.correct_systems == ["http://snomed.info/sct"]
    assert sorted(result.missing_codes) == [
        "http://snomed.info/sct|233817007",
        "http://snomed.info/sct|414545008",
    ]


def test_wrong_system_fails():
    """Using ICD-9 instead of ICD-10 — wrong system."""
    required = [_code("http://hl7.org/fhir/sid/icd-10-cm", "E11")]
    urls = ["Condition?code=http://hl7.org/fhir/sid/icd-9-cm|250.00"]
    result = CodeSystemValidator().evaluate(required, urls)
    assert result.passed is False
    assert "http://hl7.org/fhir/sid/icd-9-cm" in result.incorrect_systems


def test_missing_system_fails():
    """LLM only used SNOMED but test required RxNorm too."""
    required = [
        _code("http://snomed.info/sct", "44054006"),
        _code("http://www.nlm.nih.gov/research/umls/rxnorm", "6809"),
    ]
    urls = ["Condition?code=http://snomed.info/sct|44054006"]
    result = CodeSystemValidator().evaluate(required, urls)
    assert result.passed is False  # missing RxNorm system
    assert result.correct_systems == ["http://snomed.info/sct"]
    assert "http://www.nlm.nih.gov/research/umls/rxnorm|6809" in result.missing_codes


def test_no_system_uri_fails():
    """LLM provided a code without the system URI — FHIR servers won't multi-match."""
    required = [_code("http://snomed.info/sct", "44054006")]
    urls = ["Condition?code=44054006"]
    result = CodeSystemValidator().evaluate(required, urls)
    assert result.passed is False
    assert "|44054006" in result.extra_codes


def test_extra_codes_flagged():
    required = [_code("http://snomed.info/sct", "44054006")]
    urls = [
        "Condition?code=http://snomed.info/sct|44054006,http://snomed.info/sct|999999999"
    ]
    result = CodeSystemValidator().evaluate(required, urls)
    # All systems match, all required codes present → passes; extras tracked separately.
    assert result.passed is True
    assert "http://snomed.info/sct|999999999" in result.extra_codes


def test_multi_query_aggregates_codes():
    required = [
        _code("http://snomed.info/sct", "44054006"),
        _code("http://www.nlm.nih.gov/research/umls/rxnorm", "6809"),
    ]
    urls = [
        "Condition?code=http://snomed.info/sct|44054006",
        "MedicationRequest?code=http://www.nlm.nih.gov/research/umls/rxnorm|6809",
    ]
    result = CodeSystemValidator().evaluate(required, urls)
    assert result.passed is True
    assert sorted(result.correct_systems) == [
        "http://snomed.info/sct",
        "http://www.nlm.nih.gov/research/umls/rxnorm",
    ]


def test_short_alias_normalized_to_canonical():
    """LLM uses 'SNOMED' instead of 'http://snomed.info/sct' — should normalize and match."""
    required = [_code("http://snomed.info/sct", "44054006")]
    urls = ["Condition?code=SNOMED|44054006"]
    result = CodeSystemValidator().evaluate(required, urls)
    assert result.passed is True
    assert result.correct_systems == ["http://snomed.info/sct"]


# --------------------------------------------------------------------- #
# Real fixtures
# --------------------------------------------------------------------- #

@pytest.mark.parametrize("fixture_name", [
    "phekb-coronary-heart-disease-dx.json",
    "phekb-crohns-disease-meds.json",
    "phekb-venous-thromboembolism-dx.json",
])
def test_fixture_perfect_match_against_own_expected_query(fixture_name):
    """Each fixture's own expected_query.url should perfectly match its required_codes."""
    with open(FIXTURE_DIR / fixture_name, encoding="utf-8") as f:
        tc = json.load(f)
    required = [Code(**c) for c in tc["metadata"]["required_codes"]]
    urls = [tc["expected_query"]["url"]]
    result = CodeSystemValidator().evaluate(required, urls)
    assert result.passed is True, (
        f"{fixture_name}: own query should pass own validation, got "
        f"correct={result.correct_systems} incorrect={result.incorrect_systems} "
        f"missing={result.missing_codes}"
    )
    assert result.missing_codes == [], (
        f"{fixture_name}: should have no missing codes, got {result.missing_codes}"
    )


def test_fixture_negation_uses_expected_queries():
    """Negation tests have multiple expected_queries — validator should aggregate them."""
    fname = "phekb-venous-thromboembolism-anticoag-without-dx.json"
    with open(FIXTURE_DIR / fname, encoding="utf-8") as f:
        tc = json.load(f)
    required = [Code(**c) for c in tc["metadata"]["required_codes"]]
    urls = tc["metadata"]["expected_queries"]
    result = CodeSystemValidator().evaluate(required, urls)
    assert result.passed is True
    assert result.missing_codes == []
