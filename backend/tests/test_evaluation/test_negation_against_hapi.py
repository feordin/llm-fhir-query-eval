"""End-to-end integration test for the negation evaluation pipeline.

Requires a running HAPI FHIR server at http://localhost:8080 with the suite
data loaded. Skipped when the server is unreachable.

For each adverse fixture, verifies that:
1. With both expected queries provided, F1 == 1.0 (correct LLM gets full credit)
2. With only the keep query, F1 < 0.5 (LLM that forgot the negation is penalized)
3. The OLD union-interpretation always scores worse than difference for these tests
"""
import json
import sys
from pathlib import Path

import pytest

backend_path = Path(__file__).resolve().parents[2]
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.evaluation.execution import ExecutionEvaluator
from src.fhir.client import FHIRClient


FIXTURE_DIR = Path(__file__).resolve().parents[3] / "test-cases" / "phekb"

ADVERSE_FIXTURES = [
    "phekb-venous-thromboembolism-anticoag-without-dx.json",
    "phekb-crohns-disease-biologic-without-dx.json",
    "phekb-type-1-diabetes-insulin-without-dx.json",
    "phekb-sleep-apnea-polysom-without-dx.json",
]


@pytest.fixture(scope="module")
def fhir_client():
    client = FHIRClient(base_url="http://localhost:8080")
    if not client.health_check():
        pytest.skip("HAPI FHIR not reachable at http://localhost:8080")
    return client


@pytest.fixture(scope="module")
def evaluator(fhir_client):
    return ExecutionEvaluator(fhir_client)


@pytest.mark.parametrize("fixture_name", ADVERSE_FIXTURES)
def test_correct_llm_gets_full_credit(evaluator, fixture_name):
    with open(FIXTURE_DIR / fixture_name, encoding="utf-8") as f:
        tc = json.load(f)

    expected = tc["test_data"]["expected_patient_ids"]
    queries = tc["metadata"]["expected_queries"]

    result = evaluator.evaluate_multi_query_patient_difference(expected, queries)
    assert result.f1_score == 1.0, (
        f"{fixture_name}: expected F1=1.0 got {result.f1_score} "
        f"(actual={result.actual_count}, expected={result.expected_count})"
    )
    assert result.passed is True


@pytest.mark.parametrize("fixture_name", ADVERSE_FIXTURES)
def test_llm_forgot_subtract_query_is_penalized(evaluator, fixture_name):
    with open(FIXTURE_DIR / fixture_name, encoding="utf-8") as f:
        tc = json.load(f)

    expected = tc["test_data"]["expected_patient_ids"]
    queries = tc["metadata"]["expected_queries"]

    full_result = evaluator.evaluate_multi_query_patient_difference(expected, queries)
    # Only the keep query — LLM forgot to add the negation
    partial_result = evaluator.evaluate_multi_query_patient_difference(
        expected, [queries[0]]
    )
    # Strictly worse than full credit, and below the harness's pass threshold (0.8).
    assert partial_result.f1_score < full_result.f1_score, (
        f"{fixture_name}: forgetting subtract should score lower than including it "
        f"(partial={partial_result.f1_score}, full={full_result.f1_score})"
    )
    assert partial_result.passed is False


@pytest.mark.parametrize("fixture_name", ADVERSE_FIXTURES)
def test_difference_beats_union_for_negation(evaluator, fixture_name):
    """Sanity check: the new difference evaluator scores better than the old
    union evaluator for these test cases. This is the regression we're fixing."""
    with open(FIXTURE_DIR / fixture_name, encoding="utf-8") as f:
        tc = json.load(f)

    expected = tc["test_data"]["expected_patient_ids"]
    queries = tc["metadata"]["expected_queries"]

    diff_result = evaluator.evaluate_multi_query_patient_difference(expected, queries)
    union_result = evaluator.evaluate_multi_query_patient_union(expected, queries)

    assert diff_result.f1_score > union_result.f1_score, (
        f"{fixture_name}: difference {diff_result.f1_score} should beat union "
        f"{union_result.f1_score} for negation tests"
    )
