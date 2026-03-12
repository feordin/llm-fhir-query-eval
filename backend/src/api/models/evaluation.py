from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ParsedQuery(BaseModel):
    """Parsed FHIR query"""
    resource_type: str
    parameters: Dict[str, Any]
    url: str


class GeneratedQuery(BaseModel):
    """LLM-generated query (single or multi)"""
    raw_response: str
    parsed_query: ParsedQuery
    additional_queries: List[ParsedQuery] = Field(default_factory=list)

    @property
    def all_queries(self) -> List[ParsedQuery]:
        """Return all parsed queries (primary + additional)."""
        return [self.parsed_query] + self.additional_queries

    @property
    def is_multi_query(self) -> bool:
        return len(self.additional_queries) > 0


class ExecutionMatchResult(BaseModel):
    """Result of execution-based evaluation"""
    passed: bool
    expected_count: int
    actual_count: int
    expected_ids: List[str]
    actual_ids: List[str]
    precision: float
    recall: float
    f1_score: float


class SemanticMatchResult(BaseModel):
    """Result of semantic parsing evaluation"""
    passed: bool
    resource_type_match: bool
    parameters_match: bool
    differences: List[str]


class LLMJudgeResult(BaseModel):
    """Result of LLM judge evaluation"""
    passed: bool
    score: float
    reasoning: str


class CodeSystemValidationResult(BaseModel):
    """Result of code system validation"""
    passed: bool
    correct_systems: List[str]
    incorrect_systems: List[str]
    missing_codes: List[str]
    extra_codes: List[str]


class EvaluationResults(BaseModel):
    """Combined evaluation results"""
    execution_match: ExecutionMatchResult
    semantic_match: SemanticMatchResult
    llm_judge: LLMJudgeResult
    code_system_validation: CodeSystemValidationResult


class EvaluationResult(BaseModel):
    """Complete evaluation result"""
    evaluation_id: str
    test_case_id: str
    timestamp: datetime
    llm_provider: str
    model: str
    mcp_enabled: bool
    generated_query: GeneratedQuery
    evaluation_results: EvaluationResults
    overall_score: float
    passed: bool


class EvaluationRequest(BaseModel):
    """Request to run an evaluation"""
    test_case_ids: List[str] = Field(default_factory=list)
    llm_provider: str = Field(default="anthropic")
    model: Optional[str] = None
    mcp_enabled: bool = Field(default=False)
    run_all: bool = Field(default=False)
