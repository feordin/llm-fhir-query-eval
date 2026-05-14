"""ExecutionEvaluator.evaluate() must compare paginated, stable PATIENT ids
(via get_patient_ids_from_query), not first-page resource ids. Regression test
for the single-query pagination bug seen against Microsoft/Azure FHIR."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.evaluation.execution import ExecutionEvaluator


def _make_client(patient_sets):
    """Mock FHIRClient whose get_patient_ids_from_query(url) returns a known set."""
    client = MagicMock()
    client.get_patient_ids_from_query.side_effect = lambda url: sorted(patient_sets.get(url, set()))
    # If evaluate() ever falls back to get_resource_ids, make it loud.
    client.get_resource_ids.side_effect = AssertionError(
        "evaluate() must use get_patient_ids_from_query, not get_resource_ids"
    )
    return client


def test_evaluate_uses_patient_ids_perfect_match():
    expected = {f"p{i}" for i in range(54)}
    client = _make_client({"GOLD": expected, "GEN": expected})
    result = ExecutionEvaluator(client).evaluate("GOLD", "GEN")
    assert result.expected_count == 54  # not truncated to a first page
    assert result.actual_count == 54
    assert result.precision == 1.0 and result.recall == 1.0 and result.f1_score == 1.0
    assert result.passed is True


def test_evaluate_uses_patient_ids_partial_overlap():
    expected = {f"p{i}" for i in range(10)}
    generated = {f"p{i}" for i in range(5, 15)}  # 5 overlap, 5 extra, 5 missed
    client = _make_client({"GOLD": expected, "GEN": generated})
    result = ExecutionEvaluator(client).evaluate("GOLD", "GEN")
    assert result.expected_count == 10
    assert result.actual_count == 10
    assert result.precision == 0.5
    assert result.recall == 0.5
    assert result.passed is False
