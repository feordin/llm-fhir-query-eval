# LLM Execution Framework Plan

## Overview

This document outlines the plan for executing test cases against multiple LLM providers, supporting both cloud-based APIs and locally-hosted models, with the ability to test different configurations (skills, MCP servers, system prompts).

## Goals

1. Execute test cases against any LLM provider (cloud or local)
2. Support testing with different model configurations (MCP servers, tools, system prompts)
3. **Evaluate primarily by execution results** (does the query return correct data?)
4. Collect and store evaluation results for comparison
5. Enable parallel execution for efficiency
6. Provide both CLI and API interfaces

## Core Principle: Execution is Ground Truth

FHIR is flexible - multiple different queries can return the same correct results. For example:

```
# All of these might correctly find diabetic patients:
Patient?_has:Condition:patient:code=http://snomed.info/sct|44054006
Patient?_has:Condition:subject:code=http://hl7.org/fhir/sid/icd-10-cm|E11
Condition?code=E11&_include=Condition:subject
```

**The primary evaluation metric is: Does the generated query return the expected results when executed against the test data?**

Secondary metrics (semantic similarity, LLM judge) help explain failures but don't determine pass/fail.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Evaluation Runner                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Test Loader  │  │ LLM Router   │  │ Result Store │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Cloud Providers│  │ Local Providers │  │ Custom Endpoints│
│  ─────────────  │  │  ─────────────  │  │  ─────────────  │
│  - Anthropic    │  │  - Ollama       │  │  - vLLM         │
│  - OpenAI       │  │  - llama.cpp    │  │  - TGI          │
│  - Azure OpenAI │  │  - LM Studio    │  │  - Custom REST  │
│  - Google       │  │  - LocalAI      │  │                 │
│  - Bedrock      │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Provider Abstraction Layer

### Base Provider Interface

```python
# backend/src/llm/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class LLMConfig:
    """Configuration for an LLM provider."""
    provider: str           # "anthropic", "openai", "ollama", etc.
    model: str             # "claude-sonnet-4-20250514", "gpt-4o", "llama3.2"
    base_url: Optional[str] = None  # For custom endpoints
    api_key: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 4096
    system_prompt: Optional[str] = None
    tools: Optional[List[Dict]] = None  # Tool definitions
    mcp_servers: Optional[List[str]] = None  # MCP server configs

@dataclass
class LLMResponse:
    """Response from an LLM."""
    content: str
    model: str
    usage: Dict[str, int]  # tokens used
    latency_ms: float
    raw_response: Any  # Provider-specific raw response

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        config: LLMConfig
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    async def generate_with_tools(
        self,
        prompt: str,
        config: LLMConfig,
        tools: List[Dict]
    ) -> LLMResponse:
        """Generate a response with tool use capability."""
        pass

    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether this provider supports tool use."""
        pass
```

### Provider Implementations

#### Cloud Providers

| Provider | Models | Tool Support | MCP Support |
|----------|--------|--------------|-------------|
| **Anthropic** | Claude family | ✅ Native | ✅ Via MCP SDK |
| **OpenAI** | GPT-4, GPT-4o | ✅ Native | ❌ (simulate) |
| **Azure OpenAI** | OpenAI models | ✅ Native | ❌ (simulate) |
| **Google Vertex** | Gemini family | ✅ Native | ❌ (simulate) |
| **AWS Bedrock** | Multiple | ✅ Varies | ❌ (simulate) |

#### Local Providers

| Provider | Interface | Models | Tool Support |
|----------|-----------|--------|--------------|
| **Ollama** | REST API | Llama, Mistral, etc. | ✅ (Ollama 0.4+) |
| **llama.cpp** | REST/gRPC | GGUF models | ⚠️ Limited |
| **LM Studio** | REST API | Various | ⚠️ Limited |
| **vLLM** | OpenAI-compatible | Various | ✅ |
| **TGI** | REST API | Various | ⚠️ Limited |

### Provider Registry

```python
# backend/src/llm/registry.py

class ProviderRegistry:
    """Registry of available LLM providers."""

    _providers: Dict[str, Type[BaseLLMProvider]] = {}

    @classmethod
    def register(cls, name: str, provider: Type[BaseLLMProvider]):
        cls._providers[name] = provider

    @classmethod
    def get(cls, name: str) -> BaseLLMProvider:
        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}")
        return cls._providers[name]()

    @classmethod
    def list_providers(cls) -> List[str]:
        return list(cls._providers.keys())
```

---

## Configuration System

### Evaluation Profile

```yaml
# configs/evaluation-profiles/claude-with-fhir-tools.yaml
name: claude-with-fhir-tools
description: Claude with FHIR-specific MCP tools enabled

provider:
  name: anthropic
  model: claude-sonnet-4-20250514
  temperature: 0.0
  max_tokens: 4096

system_prompt: |
  You are a FHIR query expert. Generate valid FHIR search queries based on
  clinical requirements. Return only the query URL without explanation.

tools:
  - name: lookup_loinc_code
    description: Look up LOINC codes for lab tests
  - name: lookup_snomed_code
    description: Look up SNOMED CT codes for clinical findings
  - name: lookup_icd10_code
    description: Look up ICD-10 diagnosis codes
  - name: lookup_rxnorm_code
    description: Look up RxNorm medication codes

mcp_servers:
  - name: fhir-terminology
    command: npx
    args: ["-y", "@anthropic/mcp-server-fhir-terminology"]
```

### Multi-Model Comparison Config

```yaml
# configs/evaluation-profiles/comparison-run.yaml
name: model-comparison-2024
description: Compare multiple models on FHIR query generation

runs:
  - profile: claude-sonnet-no-tools
    tags: ["baseline", "no-tools"]

  - profile: claude-sonnet-with-tools
    tags: ["with-tools"]

  - profile: claude-opus-no-tools
    tags: ["premium", "no-tools"]

  - profile: gpt-4o-no-tools
    tags: ["openai", "baseline"]

  - profile: gpt-4o-with-tools
    tags: ["openai", "with-tools"]

  - profile: llama3-70b-ollama
    tags: ["local", "open-source"]

test_cases:
  sources:
    - test-cases/manual/
    - test-cases/phekb/
  filters:
    complexity: ["simple", "medium", "high"]
    tags: ["diabetes", "asthma"]  # Optional filtering
```

---

## MCP Server Integration

### FHIR Terminology Server

A custom MCP server for FHIR terminology lookups:

```typescript
// mcp-servers/fhir-terminology/src/index.ts

const server = new Server({
  name: "fhir-terminology",
  version: "1.0.0"
}, {
  capabilities: {
    tools: {}
  }
});

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "lookup_loinc",
      description: "Search LOINC codes by name or description",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search term" }
        },
        required: ["query"]
      }
    },
    {
      name: "lookup_snomed",
      description: "Search SNOMED CT codes by term",
      inputSchema: { /* ... */ }
    },
    {
      name: "lookup_icd10",
      description: "Search ICD-10-CM codes",
      inputSchema: { /* ... */ }
    },
    {
      name: "lookup_rxnorm",
      description: "Search RxNorm medication codes",
      inputSchema: { /* ... */ }
    },
    {
      name: "validate_fhir_query",
      description: "Validate FHIR query syntax",
      inputSchema: { /* ... */ }
    }
  ]
}));
```

### Tool Use Evaluation Matrix

| Configuration | Code Lookup | Syntax Help | FHIR Knowledge |
|--------------|-------------|-------------|----------------|
| No tools (baseline) | ❌ | ❌ | Model only |
| With terminology tools | ✅ | ❌ | Model + codes |
| With full MCP | ✅ | ✅ | Model + tools |
| With FHIR examples | ❌ | ❌ | Model + RAG |

**UMLS/VSAC MCP Server as Key Differentiator:** Our framework's clinical terminology tools (UMLS search, UMLS crosswalk, VSAC value set expansion) address a gap identified in both FHIRPath-QA (Frew et al., 2026) and FHIR-AgentBench (Lee et al., 2025) — neither benchmark evaluates whether LLMs can resolve natural clinical language to correct code systems and codes. The three-layer evaluation decomposition (Layer 2: Code System Accuracy) directly measures the impact of these tools. See `docs/literature_review.md` for detailed analysis.

---

## Evaluation Pipeline

### Execution Flow

```python
# backend/src/evaluation/runner.py

class EvaluationRunner:
    """Orchestrates test case execution."""

    async def run_evaluation(
        self,
        profile: EvaluationProfile,
        test_cases: List[TestCase],
        parallel: int = 5
    ) -> EvaluationRun:
        """
        Execute test cases against configured LLM.

        Args:
            profile: LLM configuration profile
            test_cases: Test cases to evaluate
            parallel: Number of concurrent executions

        Returns:
            EvaluationRun with all results
        """
        run = EvaluationRun(
            id=str(uuid.uuid4()),
            profile=profile.name,
            started_at=datetime.utcnow()
        )

        provider = ProviderRegistry.get(profile.provider.name)

        # Execute in parallel batches
        semaphore = asyncio.Semaphore(parallel)

        async def execute_one(test_case: TestCase):
            async with semaphore:
                return await self._execute_test_case(
                    provider, profile, test_case
                )

        tasks = [execute_one(tc) for tc in test_cases]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        run.results = [r for r in results if not isinstance(r, Exception)]
        run.errors = [str(e) for e in results if isinstance(e, Exception)]
        run.completed_at = datetime.utcnow()

        return run

    async def _execute_test_case(
        self,
        provider: BaseLLMProvider,
        profile: EvaluationProfile,
        test_case: TestCase
    ) -> TestCaseResult:
        """Execute a single test case."""

        # Build prompt with system context
        full_prompt = self._build_prompt(profile, test_case)

        # Generate LLM response
        start = time.time()
        response = await provider.generate(full_prompt, profile.config)
        latency = (time.time() - start) * 1000

        # Parse generated query
        generated_query = self._parse_fhir_query(response.content)

        # Run evaluations
        semantic_result = await self._evaluate_semantic(
            generated_query, test_case.expected_query
        )
        execution_result = await self._evaluate_execution(
            generated_query, test_case
        )

        return TestCaseResult(
            test_case_id=test_case.id,
            generated_query=generated_query,
            semantic_score=semantic_result.score,
            execution_score=execution_result.score,
            latency_ms=latency,
            token_usage=response.usage
        )
```

### Evaluation Engines

**Important:** Execution-based evaluation is the PRIMARY metric. FHIR queries can be written many different ways but still return correct results. The ground truth is whether the generated query returns the expected resources.

```python
# backend/src/evaluation/engines/

# 1. EXECUTION EVALUATION (PRIMARY - Ground Truth)
class ExecutionEvaluator:
    """
    Run queries against FHIR server, compare results.
    THIS IS THE PRIMARY METRIC - determines pass/fail.
    """

    async def evaluate(
        self,
        generated_query: str,
        test_case: TestCase,
        fhir_client: FHIRClient
    ) -> ExecutionMatchResult:
        # Execute generated query against FHIR server
        returned_ids = await fhir_client.execute_query(generated_query)

        # Compare with expected results from test_data
        expected_ids = set(test_case.test_data.expected_resource_ids)
        returned_set = set(returned_ids)

        # Calculate precision/recall/F1
        true_positives = expected_ids & returned_set
        precision = len(true_positives) / len(returned_set) if returned_set else 0
        recall = len(true_positives) / len(expected_ids) if expected_ids else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) else 0

        return ExecutionMatchResult(
            precision=precision,
            recall=recall,
            f1_score=f1,
            exact_match=(expected_ids == returned_set),
            expected_ids=list(expected_ids),
            returned_ids=list(returned_set),
            missing_ids=list(expected_ids - returned_set),
            extra_ids=list(returned_set - expected_ids)
        )

# 2. Semantic Evaluation (SECONDARY - for debugging/analysis)
class SemanticEvaluator:
    """
    Compare query structure and parameters.
    Useful for understanding WHY a query failed execution.
    """

    def evaluate(
        self,
        generated: ParsedQuery,
        expected: ExpectedQuery
    ) -> SemanticMatchResult:
        # Check resource type match
        # Check parameters (order-independent)
        # Check code systems used
        # Identify structural differences
        # Compute similarity score

# 1b. THREE-LAYER DECOMPOSITION (diagnostic breakdown of execution failures)
# Decomposes a single F1 into three diagnostic layers:
#
# Layer 1: Resource Type Accuracy
#   - Compares resource type in generated query vs expected_query.resource_type
#   - Binary: correct/incorrect
#   - Implementation: parse generated URL, extract resource type before '?'
#
# Layer 2: Code System Accuracy (UNIQUE — our UMLS/VSAC MCP contribution)
#   - 2a: Code system URI match (e.g., http://snomed.info/sct vs http://hl7.org/fhir/sid/icd-10-cm)
#   - 2b: Code value match (exact match OR VSAC value set membership for lenient mode)
#   - 2c: Code format check (system|code syntax)
#   - Implementation: parse 'code=' param from generated URL, compare vs metadata.required_codes
#   - Neither FHIRPath-QA nor FHIR-AgentBench evaluate this dimension
#
# Layer 3: Execution Correctness (existing F1 metric)
#   - Precision/Recall/F1 on patient IDs
#   - Remains the ground truth for pass/fail
#
# See: docs/IMPLEMENTATION-ROADMAP.md "Three-Layer Evaluation Decomposition"
# See: docs/literature_review.md for motivation from published benchmarks

# 3. LLM Judge Evaluation (SUPPLEMENTARY - edge cases)
class LLMJudgeEvaluator:
    """
    Use LLM to evaluate semantic equivalence.
    Handles edge cases where different queries are clinically equivalent.
    """

    async def evaluate(
        self,
        generated: str,
        expected: str,
        prompt: str
    ) -> LLMJudgeResult:
        # Ask Claude to evaluate if queries are clinically equivalent
        # Useful when execution passes but semantic differs
        # Can explain why alternative approaches are valid
```

### Evaluation Priority Matrix

| Scenario | Execution | Semantic | LLM Judge | Final Verdict |
|----------|-----------|----------|-----------|---------------|
| Exact execution match | ✅ F1=1.0 | Any | Skip | **PASS** |
| Partial execution match | ⚠️ F1<1.0 | Low | Check | **PARTIAL** |
| Resource type correct, wrong code | ❌ F1=0 | ✅ High (structure OK) | Check | **FAIL (Layer 2)** — code accuracy issue, UMLS tools may help |
| Execution fails | ❌ F1=0 | Any | N/A | **FAIL** |
| Execution passes, different structure | ✅ F1=1.0 | ❌ Low | ✅ Equivalent | **PASS** |

**Key Principle:** If execution returns correct results, the query is correct regardless of structure.

---

## CLI Interface

```bash
# Run evaluation with specific profile
fhir-eval run --profile claude-sonnet-no-tools

# Run comparison across multiple models
fhir-eval run --comparison comparison-run.yaml

# Filter test cases
fhir-eval run --profile gpt-4o --complexity high --tags diabetes

# Local model evaluation
fhir-eval run --provider ollama --model llama3.2:70b

# Generate report
fhir-eval report --run-id abc123 --format html

# List available providers
fhir-eval providers list

# Test provider configuration
fhir-eval providers test anthropic
```

---

## API Endpoints

```python
# backend/src/api/routes/evaluation.py

@router.post("/api/evaluation/runs")
async def create_evaluation_run(request: CreateRunRequest):
    """Start a new evaluation run."""

@router.get("/api/evaluation/runs/{run_id}")
async def get_evaluation_run(run_id: str):
    """Get evaluation run status and results."""

@router.get("/api/evaluation/runs")
async def list_evaluation_runs(
    profile: Optional[str] = None,
    limit: int = 50
):
    """List recent evaluation runs."""

@router.post("/api/evaluation/compare")
async def compare_runs(run_ids: List[str]):
    """Compare results across multiple runs."""

@router.get("/api/providers")
async def list_providers():
    """List available LLM providers."""

@router.post("/api/providers/test")
async def test_provider(config: ProviderConfig):
    """Test provider connectivity."""
```

---

## Data Storage

### Evaluation Results Schema

```python
# backend/src/api/models/evaluation_run.py

class EvaluationRun(BaseModel):
    id: str
    profile: str
    provider: str
    model: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: Literal["running", "completed", "failed"]

    # Aggregated metrics
    total_cases: int
    passed_cases: int
    failed_cases: int
    avg_semantic_score: float
    avg_execution_score: float
    avg_latency_ms: float
    total_tokens: int

    # Individual results
    results: List[TestCaseResult]
    errors: List[str]

class TestCaseResult(BaseModel):
    test_case_id: str
    generated_query: str
    parsed_query: Optional[ParsedQuery]

    semantic_score: float
    execution_score: float
    llm_judge_score: Optional[float]

    latency_ms: float
    token_usage: TokenUsage

    errors: List[str]
```

### Storage Options

1. **SQLite** (default for development)
2. **PostgreSQL** (production)
3. **JSON files** (simple export/archive)

---

## Implementation Phases

### Phase 1: Core Framework (Week 1-2)
- [ ] Provider abstraction layer
- [ ] Anthropic + OpenAI implementations
- [ ] Basic evaluation runner
- [ ] CLI for single-model runs

### Phase 2: Local Models (Week 2-3)
- [ ] Ollama provider
- [ ] vLLM provider (OpenAI-compatible)
- [ ] Configuration profiles

### Phase 3: Tool Integration (Week 3-4)
- [ ] FHIR terminology MCP server
- [ ] Tool-use evaluation mode
- [ ] MCP server management

### Phase 4: Analysis & Reporting (Week 4-5)
- [ ] Comparison reports
- [ ] Dashboard visualizations
- [ ] Export capabilities

---

## Testing Strategy

### Unit Tests
- Provider mock tests
- Query parser tests
- Evaluation engine tests

### Integration Tests
- Real API calls (with rate limiting)
- FHIR server integration
- MCP server integration

### Benchmark Tests
- Latency measurements
- Token usage tracking
- Cost estimation

---

## Sources

- [Synthea Documentation](https://synthetichealth.github.io/synthea/)
- [Synthea GitHub](https://github.com/synthetichealth/synthea)
- [FHIR for Research - Synthea Overview](https://mitre.github.io/fhir-for-research/modules/synthea-overview)
