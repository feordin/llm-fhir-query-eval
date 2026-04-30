from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Code(BaseModel):
    """FHIR code system reference"""
    system: str
    code: str
    display: str
    source: str = Field(
        default="inferred",
        description="Where code came from: document, inferred, or umls"
    )


class PatientFilters(BaseModel):
    """Patient-level filters for restricting populations.

    FHIR doesn't have a direct ``Patient.age`` search parameter — to restrict
    by age, queries must use ``Patient.birthdate`` with date arithmetic. This
    model captures the *intent* (age range, sex) so the runner can:
    1. Render the filter as a chained ``patient.birthdate=...`` clause for
       Condition/Observation/Procedure/MedicationRequest queries.
    2. Or apply the filter client-side when chained search isn't available.

    Both ``min_age_years`` and ``max_age_years`` are inclusive of the boundary
    age (e.g., ``min_age_years=5, max_age_years=17`` matches anyone aged 5
    through 17 inclusive on the reference date).
    """
    model_config = {"extra": "allow"}

    min_age_years: Optional[int] = Field(
        default=None,
        description="Minimum age in years, inclusive. Patient.age >= this.",
    )
    max_age_years: Optional[int] = Field(
        default=None,
        description="Maximum age in years, inclusive. Patient.age <= this.",
    )
    sex: Optional[str] = Field(
        default=None,
        description="Restrict to a specific sex. 'male', 'female', 'other', 'unknown'.",
    )
    reference_date: Optional[str] = Field(
        default=None,
        description=(
            "ISO date (YYYY-MM-DD) used as the reference point for age "
            "calculations. Defaults to the date the test case was authored. "
            "Without a fixed reference date, age-restricted test cases drift "
            "as time passes."
        ),
    )


class TestCaseMetadata(BaseModel):
    """Metadata for a test case"""
    model_config = {"extra": "allow"}

    implementation_guide: Optional[str] = None
    code_systems: List[str] = Field(default_factory=list)
    required_codes: List[Code] = Field(default_factory=list)
    complexity: str = Field(default="medium")
    tags: List[str] = Field(default_factory=list)
    # Multi-query support
    multi_query: bool = False
    expected_queries: List[str] = Field(default_factory=list)
    algorithm_path: Optional[str] = None
    algorithm_paths: Optional[str] = None
    # Negation support: when True, expected_queries are interpreted as
    # query[0] = keep set, query[1:] = subtract sets, with patient-level
    # set difference instead of union. negation_operation is a human-readable
    # description of the operation (e.g., "query[0]_patients - query[1]_patients").
    negation: bool = False
    negation_operation: Optional[str] = None
    # Patient-level filters (age range, sex). Documents test-case intent and
    # can be applied as chained ``patient.birthdate``/``patient.gender`` clauses
    # at evaluation time. None = no patient-level restriction.
    patient_filters: Optional[PatientFilters] = None


class ExpectedQuery(BaseModel):
    """Expected FHIR query"""
    model_config = {"extra": "allow"}

    resource_type: str
    parameters: Dict[str, Any]
    url: str


class TestData(BaseModel):
    """Test data configuration"""
    model_config = {"extra": "allow"}

    resources: List[str] = Field(default_factory=list)
    expected_result_count: Optional[int] = None
    expected_resource_ids: List[str] = Field(default_factory=list)
    expected_patient_ids: List[str] = Field(default_factory=list)


class TestCase(BaseModel):
    """FHIR query test case.

    Supports two prompt formats:
    - Legacy: single ``prompt`` field (string)
    - New: ``prompts`` dict mapping variant names to prompt text,
      e.g. ``{"naive": "...", "expert": "..."}``

    When both are present, ``prompts`` takes precedence.
    The ``prompt`` property always returns a usable prompt (defaults to naive).
    Use ``get_prompt(variant)`` to select a specific variant.
    """
    id: str
    source: str = Field(pattern="^(phekb|manual|other)$")
    source_id: Optional[str] = None
    name: str
    description: str
    # Legacy single prompt (kept for backward compat during migration)
    prompt: Optional[str] = None
    # New: prompt variants keyed by name (e.g. "naive", "expert")
    prompts: Optional[Dict[str, str]] = None
    metadata: TestCaseMetadata
    expected_query: ExpectedQuery
    test_data: TestData
    created_at: datetime
    updated_at: datetime

    def get_prompt(self, variant: str = "naive") -> str:
        """Return the prompt for the given variant.

        Falls back through: prompts[variant] → prompts[first key] → prompt field.
        """
        if self.prompts:
            if variant in self.prompts:
                return self.prompts[variant]
            # Fall back to first available variant
            return next(iter(self.prompts.values()))
        return self.prompt or ""

    @property
    def available_variants(self) -> List[str]:
        """Return list of available prompt variant names."""
        if self.prompts:
            return list(self.prompts.keys())
        return ["default"]


class TestCaseCreate(BaseModel):
    """Schema for creating a test case"""
    source: str = Field(default="manual", pattern="^(phekb|manual|other)$")
    source_id: Optional[str] = None
    name: str
    description: str
    prompt: Optional[str] = None
    prompts: Optional[Dict[str, str]] = None
    metadata: TestCaseMetadata
    expected_query: ExpectedQuery
    test_data: TestData


class TestCaseUpdate(BaseModel):
    """Schema for updating a test case"""
    name: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    prompts: Optional[Dict[str, str]] = None
    metadata: Optional[TestCaseMetadata] = None
    expected_query: Optional[ExpectedQuery] = None
    test_data: Optional[TestData] = None
