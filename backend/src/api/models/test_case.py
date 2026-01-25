from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Code(BaseModel):
    """FHIR code system reference"""
    system: str
    code: str
    display: str


class TestCaseMetadata(BaseModel):
    """Metadata for a test case"""
    implementation_guide: Optional[str] = None
    code_systems: List[str] = Field(default_factory=list)
    required_codes: List[Code] = Field(default_factory=list)
    complexity: str = Field(default="medium", pattern="^(simple|medium|complex)$")
    tags: List[str] = Field(default_factory=list)


class ExpectedQuery(BaseModel):
    """Expected FHIR query"""
    resource_type: str
    parameters: Dict[str, Any]
    url: str


class TestData(BaseModel):
    """Test data configuration"""
    resources: List[str] = Field(default_factory=list)
    expected_result_count: int
    expected_resource_ids: List[str] = Field(default_factory=list)


class TestCase(BaseModel):
    """FHIR query test case"""
    id: str
    source: str = Field(pattern="^(phekb|manual|other)$")
    source_id: Optional[str] = None
    name: str
    description: str
    prompt: str
    metadata: TestCaseMetadata
    expected_query: ExpectedQuery
    test_data: TestData
    created_at: datetime
    updated_at: datetime


class TestCaseCreate(BaseModel):
    """Schema for creating a test case"""
    source: str = Field(default="manual", pattern="^(phekb|manual|other)$")
    source_id: Optional[str] = None
    name: str
    description: str
    prompt: str
    metadata: TestCaseMetadata
    expected_query: ExpectedQuery
    test_data: TestData


class TestCaseUpdate(BaseModel):
    """Schema for updating a test case"""
    name: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    metadata: Optional[TestCaseMetadata] = None
    expected_query: Optional[ExpectedQuery] = None
    test_data: Optional[TestData] = None
