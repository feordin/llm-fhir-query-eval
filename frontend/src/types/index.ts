// Mirrors backend Pydantic models

export interface Code {
  system: string
  code: string
  display: string
  source: 'document' | 'inferred'
}

export interface TestCaseMetadata {
  implementation_guide?: string
  code_systems: string[]
  required_codes: Code[]
  complexity: string
  tags: string[]
  multi_query: boolean
  expected_queries: string[]
  algorithm_path?: string
  algorithm_paths?: string
}

export interface ExpectedQuery {
  resource_type: string
  parameters: Record<string, unknown>
  url: string
}

export interface TestData {
  resources: string[]
  expected_result_count: number
  expected_resource_ids: string[]
  expected_patient_ids: string[]
}

export interface TestCase {
  id: string
  source: 'phekb' | 'manual' | 'other'
  source_id?: string
  name: string
  description: string
  /** Legacy single prompt (may be absent if prompts dict is used) */
  prompt?: string
  /** Prompt variants keyed by name, e.g. { naive: "...", expert: "..." } */
  prompts?: Record<string, string>
  metadata: TestCaseMetadata
  expected_query: ExpectedQuery
  test_data: TestData
  created_at: string
  updated_at: string
}

// Evaluation types

export interface ParsedQuery {
  resource_type: string
  parameters: Record<string, unknown>
  url: string
}

export interface GeneratedQuery {
  raw_response: string
  parsed_query: ParsedQuery
  additional_queries: ParsedQuery[]
}

export interface ExecutionMatchResult {
  passed: boolean
  expected_count: number
  actual_count: number
  expected_ids: string[]
  actual_ids: string[]
  precision: number
  recall: number
  f1_score: number
}

export interface SemanticMatchResult {
  passed: boolean
  resource_type_match: boolean
  parameters_match: boolean
  differences: string[]
}

export interface LLMJudgeResult {
  passed: boolean
  score: number
  reasoning: string
}

export interface CodeSystemValidationResult {
  passed: boolean
  correct_systems: string[]
  incorrect_systems: string[]
  missing_codes: string[]
  extra_codes: string[]
}

export interface EvaluationResults {
  execution_match: ExecutionMatchResult
  semantic_match: SemanticMatchResult
  llm_judge: LLMJudgeResult
  code_system_validation: CodeSystemValidationResult
}

export interface EvaluationResult {
  evaluation_id: string
  test_case_id: string
  timestamp: string
  llm_provider: string
  model: string
  mcp_enabled: boolean
  generated_query: GeneratedQuery
  evaluation_results: EvaluationResults
  overall_score: number
  passed: boolean
}

// Dashboard types

export interface DashboardModelResult {
  evaluation_id: string
  score: number
  passed: boolean
  mcp_enabled: boolean
  model: string
  timestamp: string
  f1_score: number
  semantic_passed: boolean
}

export interface DashboardTestCase {
  id: string
  name: string
  source: string
  complexity: string
  resource_type: string
  multi_query: boolean
  tags: string[]
  algorithm_path?: string
  results: Record<string, DashboardModelResult>
  best_score: number | null
}

export interface DashboardSummary {
  total_test_cases: number
  evaluated_test_cases: number
  total_evaluations: number
  passed: number
  failed: number
  pass_rate: number
}

export interface DashboardData {
  models: string[]
  test_cases: DashboardTestCase[]
  summary: DashboardSummary
}
