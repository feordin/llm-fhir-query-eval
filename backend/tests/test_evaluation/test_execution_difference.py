"""Tests for evaluate_multi_query_patient_difference (negation evaluation).

Uses a mock FHIR client to avoid requiring a live server. The fixture mirrors
the actual `phekb-venous-thromboembolism-anticoag-without-dx` test case:
  - keep query (anticoagulants):  37 patients
  - subtract query (VTE dx):      29 patients
  - difference:                    8 patients (the AFib cohort)
"""
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import sys

backend_path = Path(__file__).resolve().parents[2]
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.evaluation.execution import ExecutionEvaluator


FIXTURE_PATH = (
    Path(__file__).resolve().parents[3]
    / "test-cases"
    / "phekb"
    / "phekb-venous-thromboembolism-anticoag-without-dx.json"
)


def _load_fixture():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _make_client(patient_sets: dict[str, set[str]]):
    """Mock FHIRClient where get_patient_ids_from_query(url) returns
    the patients keyed by url substring."""
    client = MagicMock()

    def lookup(url: str):
        for key, patients in patient_sets.items():
            if key in url:
                return list(patients)
        return []

    client.get_patient_ids_from_query.side_effect = lookup
    return client


def test_difference_perfect_match_against_fixture():
    """LLM produces both queries in the right order — full credit."""
    tc = _load_fixture()
    expected = set(tc["test_data"]["expected_patient_ids"])
    keep_query, subtract_query = tc["metadata"]["expected_queries"]

    # Build "keep set" = expected difference (8) + the 29 VTE-diagnosed patients.
    # In the real data, keep set = anticoag patients (37) and subtract set = VTE
    # dx patients (29). Their difference is the 8 expected.
    diagnosed_patients = {f"diagnosed_{i}" for i in range(29)}
    keep_set = expected | diagnosed_patients  # 37 patients
    subtract_set = diagnosed_patients         # 29 patients

    client = _make_client({
        "MedicationRequest?code=": keep_set,
        "Condition?code=": subtract_set,
    })
    ev = ExecutionEvaluator(client)

    result = ev.evaluate_multi_query_patient_difference(
        sorted(expected), [keep_query, subtract_query]
    )
    assert result.f1_score == 1.0
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.actual_count == len(expected)
    assert result.passed is True


def test_difference_llm_returns_only_keep_query_penalized():
    """LLM produces only the medication query (forgot the negation) — should be
    penalized because the keep set is a strict superset of the expected diff."""
    tc = _load_fixture()
    expected = set(tc["test_data"]["expected_patient_ids"])
    keep_query, subtract_query = tc["metadata"]["expected_queries"]

    diagnosed_patients = {f"diagnosed_{i}" for i in range(29)}
    keep_set = expected | diagnosed_patients

    client = _make_client({
        "MedicationRequest?code=": keep_set,
        "Condition?code=": diagnosed_patients,
    })
    ev = ExecutionEvaluator(client)

    result = ev.evaluate_multi_query_patient_difference(
        sorted(expected), [keep_query]  # subtract query missing
    )
    # Recall = 1.0 (all 8 returned), but precision = 8/37 = 0.216
    assert result.recall == 1.0
    assert result.precision < 0.3
    assert result.f1_score < 0.5
    assert result.passed is False


def test_difference_llm_returns_no_queries():
    """LLM produces no queries — F1 = 0."""
    tc = _load_fixture()
    expected = set(tc["test_data"]["expected_patient_ids"])

    client = _make_client({})
    ev = ExecutionEvaluator(client)

    result = ev.evaluate_multi_query_patient_difference(sorted(expected), [])
    assert result.f1_score == 0.0
    assert result.actual_count == 0
    assert result.passed is False


def test_difference_with_multiple_subtract_queries():
    """LLM produces three queries: query[0] keep, query[1:] both subtracted (union)."""
    keep = {"a", "b", "c", "d", "e", "f", "g", "h"}
    sub1 = {"a", "b"}
    sub2 = {"c"}
    expected = keep - (sub1 | sub2)  # {"d","e","f","g","h"}

    client = _make_client({
        "keep": keep,
        "sub1": sub1,
        "sub2": sub2,
    })
    ev = ExecutionEvaluator(client)

    result = ev.evaluate_multi_query_patient_difference(
        sorted(expected),
        ["http://localhost/fhir/A?keep", "http://localhost/fhir/B?sub1", "http://localhost/fhir/C?sub2"],
    )
    assert result.f1_score == 1.0
    assert result.actual_count == 5


def test_difference_metadata_flag_is_set_on_fixtures():
    """All four adverse fixtures must carry metadata.negation=true."""
    fixture_dir = FIXTURE_PATH.parent
    adverse = [
        "phekb-venous-thromboembolism-anticoag-without-dx.json",
        "phekb-crohns-disease-biologic-without-dx.json",
        "phekb-type-1-diabetes-insulin-without-dx.json",
        "phekb-sleep-apnea-polysom-without-dx.json",
    ]
    for fname in adverse:
        with open(fixture_dir / fname, encoding="utf-8") as f:
            tc = json.load(f)
        assert tc["metadata"].get("negation") is True, f"{fname} missing negation flag"
        assert tc["metadata"].get("multi_query") is True, f"{fname} missing multi_query flag"
        assert len(tc["metadata"]["expected_queries"]) >= 2, f"{fname} needs >= 2 queries"
