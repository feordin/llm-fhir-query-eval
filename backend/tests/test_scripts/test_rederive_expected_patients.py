"""Unit tests for the re-derive script: given a mocked FHIR client + a test
case file, the script overwrites expected_patient_ids with the IDs the gold
queries currently return, and updates expected_result_count to match."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from rederive_expected_patients import rederive_test_case  # noqa: E402


def _make_client(query_to_patients):
    client = MagicMock()
    client.get_patient_ids_from_query.side_effect = (
        lambda url: sorted(query_to_patients.get(url, set()))
    )
    return client


def test_rederive_single_query(tmp_path):
    tc_file = tmp_path / "phekb-x-dx.json"
    tc_file.write_text(json.dumps({
        "id": "phekb-x-dx",
        "expected_query": {"url": "Condition?code=snomed|1"},
        "metadata": {},
        "test_data": {"expected_patient_ids": ["stale1", "stale2"],
                      "expected_result_count": 2},
    }))
    client = _make_client({"Condition?code=snomed|1": {"new1", "new2", "new3"}})
    changed = rederive_test_case(client, tc_file)
    assert changed is True
    new = json.loads(tc_file.read_text())
    assert sorted(new["test_data"]["expected_patient_ids"]) == ["new1", "new2", "new3"]
    assert new["test_data"]["expected_result_count"] == 3


def test_rederive_multi_query_union(tmp_path):
    tc_file = tmp_path / "phekb-x-comp.json"
    tc_file.write_text(json.dumps({
        "id": "phekb-x-comp",
        "expected_query": {"url": "Condition?code=snomed|1"},
        "metadata": {"multi_query": True,
                     "expected_queries": ["Condition?code=A", "MedicationRequest?code=B"]},
        "test_data": {"expected_patient_ids": [], "expected_result_count": 0},
    }))
    client = _make_client({"Condition?code=A": {"p1", "p2"},
                           "MedicationRequest?code=B": {"p2", "p3"}})
    rederive_test_case(client, tc_file)
    new = json.loads(tc_file.read_text())
    assert sorted(new["test_data"]["expected_patient_ids"]) == ["p1", "p2", "p3"]


def test_rederive_negation(tmp_path):
    tc_file = tmp_path / "phekb-x-neg.json"
    tc_file.write_text(json.dumps({
        "id": "phekb-x-neg",
        "expected_query": {"url": "MedicationRequest?code=A"},
        "metadata": {"multi_query": True, "negation": True,
                     "negation_operation": "query[0]_patients - query[1]_patients",
                     "expected_queries": ["MedicationRequest?code=A", "Condition?code=B"]},
        "test_data": {"expected_patient_ids": [], "expected_result_count": 0},
    }))
    client = _make_client({"MedicationRequest?code=A": {"p1", "p2", "p3"},
                           "Condition?code=B": {"p2"}})
    rederive_test_case(client, tc_file)
    new = json.loads(tc_file.read_text())
    assert sorted(new["test_data"]["expected_patient_ids"]) == ["p1", "p3"]


def test_rederive_no_change_returns_false(tmp_path):
    tc_file = tmp_path / "phekb-x-dx.json"
    tc_file.write_text(json.dumps({
        "id": "phekb-x-dx",
        "expected_query": {"url": "Condition?code=snomed|1"},
        "metadata": {},
        "test_data": {"expected_patient_ids": ["p1", "p2"], "expected_result_count": 2},
    }))
    client = _make_client({"Condition?code=snomed|1": {"p1", "p2"}})
    assert rederive_test_case(client, tc_file) is False  # no diff -> no rewrite


def test_rederive_no_gold_query_returns_false(tmp_path):
    """A test case with neither expected_query.url nor metadata.expected_queries
    has no gold query at all -- rederive should return False without writing
    or raising, leaving the file untouched."""
    tc_file = tmp_path / "phekb-x-stub.json"
    original = json.dumps({
        "id": "phekb-x-stub",
        "expected_query": {},  # no url
        "metadata": {},        # no expected_queries
        "test_data": {"expected_patient_ids": ["unchanged"], "expected_result_count": 1},
    })
    tc_file.write_text(original)
    client = _make_client({})  # would never be called
    assert rederive_test_case(client, tc_file) is False
    assert tc_file.read_text() == original  # file untouched
    client.get_patient_ids_from_query.assert_not_called()
