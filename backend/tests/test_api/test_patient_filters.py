"""Tests for the PatientFilters schema and its integration into TestCase."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

backend_path = Path(__file__).resolve().parents[2]
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.test_case import (
    ExpectedQuery,
    PatientFilters,
    TestCase,
    TestCaseMetadata,
    TestData,
)


FIXTURE_DIR = Path(__file__).resolve().parents[3] / "test-cases" / "phekb"


# --------------------------------------------------------------------- #
# PatientFilters direct construction
# --------------------------------------------------------------------- #
def test_patient_filters_all_fields():
    pf = PatientFilters(
        min_age_years=5,
        max_age_years=17,
        sex="female",
        reference_date="2026-04-28",
    )
    assert pf.min_age_years == 5
    assert pf.max_age_years == 17
    assert pf.sex == "female"
    assert pf.reference_date == "2026-04-28"


def test_patient_filters_all_optional():
    pf = PatientFilters()
    assert pf.min_age_years is None
    assert pf.max_age_years is None
    assert pf.sex is None
    assert pf.reference_date is None


def test_patient_filters_partial():
    pf = PatientFilters(min_age_years=18)
    assert pf.min_age_years == 18
    assert pf.max_age_years is None


def test_patient_filters_extra_keys_allowed():
    """``extra=allow`` so future fields don't crash older readers."""
    pf = PatientFilters.model_validate(
        {"min_age_years": 0, "future_field": "ignored"}
    )
    assert pf.min_age_years == 0


# --------------------------------------------------------------------- #
# TestCaseMetadata integration
# --------------------------------------------------------------------- #
def test_metadata_without_patient_filters():
    md = TestCaseMetadata()
    assert md.patient_filters is None


def test_metadata_with_patient_filters_dict():
    md = TestCaseMetadata.model_validate(
        {
            "patient_filters": {
                "min_age_years": 5,
                "max_age_years": 17,
                "reference_date": "2026-04-28",
            }
        }
    )
    assert md.patient_filters is not None
    assert md.patient_filters.min_age_years == 5
    assert md.patient_filters.max_age_years == 17
    assert md.patient_filters.reference_date == "2026-04-28"


def test_metadata_patient_filters_round_trip():
    md = TestCaseMetadata(
        patient_filters=PatientFilters(min_age_years=5, max_age_years=17)
    )
    dumped = md.model_dump()
    re_parsed = TestCaseMetadata.model_validate(dumped)
    assert re_parsed.patient_filters.min_age_years == 5
    assert re_parsed.patient_filters.max_age_years == 17


# --------------------------------------------------------------------- #
# Real fixture: SECO test cases must have patient_filters populated
# --------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "fixture_name",
    [
        "phekb-severe-childhood-obesity-dx.json",
        "phekb-severe-childhood-obesity-labs.json",
        "phekb-severe-childhood-obesity-comprehensive.json",
    ],
)
def test_seco_fixtures_carry_age_filter(fixture_name: str):
    path = FIXTURE_DIR / fixture_name
    if not path.exists():
        pytest.skip(f"fixture {fixture_name} not present")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    tc = TestCase.model_validate(data)
    pf = tc.metadata.patient_filters
    assert pf is not None, f"{fixture_name} should declare patient_filters"
    assert pf.min_age_years == 5
    assert pf.max_age_years == 17
    assert pf.reference_date == "2026-04-28"


def test_seco_fixtures_url_includes_birthdate_filter():
    """The rendered URL must reflect the patient filter so HAPI scopes results."""
    for fixture in (
        "phekb-severe-childhood-obesity-dx.json",
        "phekb-severe-childhood-obesity-labs.json",
    ):
        path = FIXTURE_DIR / fixture
        if not path.exists():
            pytest.skip(f"fixture {fixture} not present")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        url = data["expected_query"]["url"]
        assert "patient.birthdate=gt2008-04-28" in url, fixture
        assert "patient.birthdate=le2021-04-28" in url, fixture


# --------------------------------------------------------------------- #
# Type validation
# --------------------------------------------------------------------- #
def test_min_age_must_be_int():
    with pytest.raises(ValidationError):
        PatientFilters(min_age_years="five")


def test_reference_date_accepts_string():
    pf = PatientFilters(reference_date="2026-04-28")
    assert pf.reference_date == "2026-04-28"
