# Implementation Roadmap

## Executive Summary

This document provides a unified roadmap for implementing the LLM FHIR Query Evaluation framework. It combines the LLM execution framework and test data generation plans into a cohesive implementation strategy.

## Current State

### What Exists

| Component | Status | Location |
|-----------|--------|----------|
| Test Cases (100+) | ✅ Complete | `test-cases/phekb/`, `test-cases/manual/` |
| Phenotype Data | ✅ Complete | `data/phekb-raw/*/document_analysis.json` |
| Test Case Models | ✅ Complete | `backend/src/api/models/test_case.py` |
| Evaluation Models | ✅ Complete | `backend/src/api/models/evaluation.py` |
| Test Case API | ✅ Complete | `backend/src/api/routes/test_cases.py` |
| LLM Providers | ⚠️ Skeleton | `backend/src/llm/` (empty) |
| Evaluation Engines | ⚠️ Skeleton | `backend/src/evaluation/` (empty) |
| Test Data | ❌ Missing | Need Synthea integration |
| FHIR Server Data | ❌ Empty | fhir-candle has no data |

### Key Assets

- **78 phenotypes** with detailed document analysis
- **100+ test cases** with prompts and expected queries
- **Clinical codes** extracted from source documents (LOINC, SNOMED, ICD, RxNorm)
- **Algorithm summaries** describing phenotype logic

---

## Evaluation Philosophy

### The Ground Truth: Execution Results

**FHIR is flexible.** Multiple different queries can return the same correct results:

```
# These queries might all find the same diabetic patients:
Patient?_has:Condition:patient:code=http://snomed.info/sct|44054006
Patient?_has:Condition:subject:code=http://hl7.org/fhir/sid/icd-10-cm|E11
Condition?code=E11&_include=Condition:subject
```

**The primary evaluation metric is: Does the generated query return the expected results?**

### Evaluation Hierarchy

| Priority | Evaluator | What It Measures | When It Matters |
|----------|-----------|------------------|-----------------|
| **P0** | **Execution** | Correct results returned | **Always** - this is ground truth |
| P1 | Semantic | Query structure similarity | Debugging, understanding failures |
| P2 | LLM Judge | Semantic equivalence reasoning | Edge cases, tie-breaking |

### Execution-Based Scoring

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Execution Evaluation Flow                         │
└─────────────────────────────────────────────────────────────────────┘

  Test Case                    Generated Query
      │                              │
      ▼                              ▼
┌──────────────┐              ┌──────────────┐
│ Expected IDs │              │ Execute on   │
│ from test_data│             │ FHIR Server  │
└──────────────┘              └──────────────┘
      │                              │
      ▼                              ▼
   [P1, P2, P3]                [P1, P2, P4]
      │                              │
      └──────────────┬───────────────┘
                     ▼
              ┌─────────────┐
              │  Compare    │
              │  Result Sets│
              └─────────────┘
                     │
                     ▼
    ┌────────────────────────────────────┐
    │  Precision = 2/3 (P1,P2 correct)   │
    │  Recall = 2/3 (P1,P2 found)        │
    │  F1 = 0.67                         │
    │  Missing: P3                       │
    │  Extra: P4                         │
    └────────────────────────────────────┘
```

### Scoring Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Precision** | TP / (TP + FP) | Of returned results, how many are correct? |
| **Recall** | TP / (TP + FN) | Of expected results, how many were found? |
| **F1 Score** | 2 × (P × R) / (P + R) | Harmonic mean - balanced measure |
| **Exact Match** | Expected == Returned | Boolean - perfect result set |

### Why Keep Semantic & LLM Judge?

Even though execution is primary, the other evaluators provide value:

1. **Semantic Evaluator**
   - Helps explain *why* a query failed
   - Identifies if wrong resource type, missing parameters, wrong codes
   - Useful for debugging and model improvement

2. **LLM Judge**
   - Handles ambiguous cases where both queries might be "correct enough"
   - Can reason about clinical equivalence
   - Catches cases where different codes represent same concept

### Example: Same Results, Different Queries

```yaml
Test Case: "Find patients with Type 2 Diabetes"

Expected Query (from test case):
  Patient?_has:Condition:patient:code=http://snomed.info/sct|44054006

Generated Query (from LLM):
  Patient?_has:Condition:patient:code=http://hl7.org/fhir/sid/icd-10-cm|E11

Evaluation:
  Execution Score: 1.0 (F1) - Both return same 10 patients ✅
  Semantic Score: 0.6 - Different code system used
  LLM Judge: PASS - "Both codes represent Type 2 Diabetes"

Final Verdict: PASS (execution is ground truth)
```

### Test Data Requirements

For execution-based evaluation to work, each test case needs:

```json
{
  "test_data": {
    "resources": ["Patient/p1", "Patient/p2", "..."],
    "expected_result_count": 10,
    "expected_resource_ids": ["p1", "p2", "p3", "..."]
  }
}
```

This is why **Phase 2 (Test Data Generation) is critical** - without test data loaded in the FHIR server, we can only do semantic evaluation.

---

## Implementation Phases

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PHASE 1: Foundation (Weeks 1-2)                  │
│  LLM Provider Layer │ Basic Evaluation │ CLI Framework              │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PHASE 2: Test Data (Weeks 2-4)                     │
│  Synthea Modules │ Data Generation │ FHIR Server Loading            │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PHASE 3: Full Pipeline (Weeks 4-6)                 │
│  Execution Eval │ Multi-Model │ MCP/Tools │ Reporting               │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PHASE 4: Analysis (Weeks 6-8)                      │
│  Dashboard │ Benchmarks │ Research Analysis                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation (Weeks 1-2)

### Goal
Establish core infrastructure for running test cases against LLMs. **Note:** This phase uses semantic evaluation only (no test data yet). Execution-based evaluation requires Phase 2 completion.

### Deliverables

#### 1.1 LLM Provider Abstraction

```
backend/src/llm/
├── __init__.py
├── base.py           # BaseLLMProvider ABC
├── config.py         # LLMConfig, EvaluationProfile
├── registry.py       # Provider registry
├── providers/
│   ├── __init__.py
│   ├── anthropic.py  # Anthropic Claude
│   ├── openai.py     # OpenAI GPT-4
│   └── ollama.py     # Local Ollama
└── exceptions.py
```

**Key Tasks:**
- [ ] Define provider interface (generate, generate_with_tools)
- [ ] Implement Anthropic provider
- [ ] Implement OpenAI provider
- [ ] Add configuration loading from YAML

#### 1.2 Basic Evaluation Runner

```
backend/src/evaluation/
├── __init__.py
├── runner.py         # EvaluationRunner orchestrator
├── parser.py         # FHIR query parser
├── engines/
│   ├── __init__.py
│   ├── semantic.py   # Structural comparison
│   └── llm_judge.py  # Claude as judge
└── results.py        # Result aggregation
```

**Key Tasks:**
- [ ] Implement FHIR query parser (extract resource type, params)
- [ ] Implement semantic evaluator (compare structure)
- [ ] Create evaluation runner (load tests, execute, score)
- [ ] Add result persistence (JSON/SQLite)

#### 1.3 CLI Framework

```
cli/fhir_eval/commands/
├── run.py           # Execute evaluations
├── providers.py     # Manage providers
└── report.py        # Generate reports
```

**Key Commands:**
```bash
fhir-eval run --provider anthropic --model claude-sonnet-4-20250514
fhir-eval run --profile configs/claude-baseline.yaml
fhir-eval providers list
fhir-eval providers test anthropic
```

### Success Criteria
- Can execute all test cases against Claude
- Semantic scores computed for each test case
- Results stored and viewable

---

## Phase 2: Test Data Generation (Weeks 2-4)

### Goal
Generate FHIR-compliant test data for execution-based evaluation.

### Deliverables

#### 2.1 Phenotype Analyzer

```
tools/synthea_generator/
├── __init__.py
├── analyzer.py       # Extract criteria from phenotype docs
├── code_mapper.py    # ICD-9 to ICD-10, code system URIs
└── criteria.py       # PhenotypeCriteria dataclass
```

**Key Tasks:**
- [ ] Parse document_analysis.json for codes
- [ ] Extract clinical thresholds from criteria
- [ ] Map ICD-9 codes to ICD-10
- [ ] Validate extracted codes

#### 2.2 Synthea Module Generator

```
tools/synthea_generator/
├── module_generator.py    # Generate case modules
├── control_generator.py   # Generate control modules
├── templates/
│   ├── base_module.json
│   └── condition_state.json
└── validators.py
```

**Key Tasks:**
- [ ] Create module template structure
- [ ] Generate state machines from criteria
- [ ] Create control patient modules
- [ ] Validate generated modules against Synthea schema

#### 2.3 Data Generation Pipeline

```
tools/
├── run_synthea.py         # Execute Synthea
├── data_loader.py         # Load to FHIR server
└── test_linker.py         # Link data to test cases
```

**Key Tasks:**
- [ ] Docker compose for Synthea
- [ ] Batch generation script
- [ ] FHIR bundle loader
- [ ] Update test_data in test case files

### Generated Modules (Priority)

| Phenotype | Complexity | Priority |
|-----------|------------|----------|
| Type 2 Diabetes | High | P0 |
| Asthma | High | P0 |
| Heart Failure | High | P0 |
| Hypertension | Medium | P1 |
| Chronic Kidney Disease | High | P1 |
| COPD | Medium | P1 |
| Depression | Medium | P2 |
| Dementia | Medium | P2 |

### Success Criteria
- Synthea modules for top 10 phenotypes
- 30+ patients per phenotype (10 positive, 10 control, 10 edge cases)
- Data loaded to fhir-candle
- Test cases linked to expected results

---

## Phase 3: Full Evaluation Pipeline (Weeks 4-6)

### Goal
Complete evaluation system with **execution-based testing as the primary metric**. This is where the framework becomes truly useful - we can now measure whether LLMs generate queries that return correct results.

### Deliverables

#### 3.1 Execution Evaluator (PRIMARY METRIC)

```
backend/src/evaluation/engines/
└── execution.py      # Run queries against FHIR server
```

**Key Tasks:**
- [ ] FHIR client for query execution
- [ ] Result set comparison (precision/recall/F1)
- [ ] Exact match detection (perfect result set)
- [ ] Handle query execution errors gracefully
- [ ] Timeout and retry logic
- [ ] Detailed diff output (missing IDs, extra IDs)

**Evaluation Output:**
```python
@dataclass
class ExecutionResult:
    # Core metrics
    precision: float      # Correct / Returned
    recall: float         # Found / Expected
    f1_score: float       # Harmonic mean
    exact_match: bool     # Perfect result set?

    # Details for debugging
    expected_ids: List[str]
    returned_ids: List[str]
    missing_ids: List[str]   # In expected, not returned
    extra_ids: List[str]     # In returned, not expected

    # Execution metadata
    query_executed: str
    execution_time_ms: float
    error: Optional[str]
```

#### 3.2 Multi-Model Comparison

```
backend/src/evaluation/
├── comparison.py     # Compare across models
└── aggregator.py     # Aggregate results
```

**Key Tasks:**
- [ ] Parallel execution across models
- [ ] Result normalization
- [ ] Statistical comparison

#### 3.3 MCP Server Integration

```
mcp-servers/
└── fhir-terminology/
    ├── package.json
    ├── src/
    │   └── index.ts
    └── README.md
```

**Key Tasks:**
- [ ] FHIR terminology lookup server
- [ ] Integration with Anthropic provider
- [ ] Tool use evaluation metrics

#### 3.4 Local Model Support

**Key Tasks:**
- [ ] Ollama provider implementation
- [ ] vLLM provider (OpenAI-compatible)
- [ ] Model-specific prompts

### Success Criteria
- **Execution evaluation working with test data** (primary metric functional)
- F1/precision/recall scores computed for all test cases
- Can compare 3+ models in single run with execution scores
- MCP tools available for Claude (test if tools improve accuracy)
- Ollama support functional for local model testing

---

## Phase 4: Analysis & Reporting (Weeks 6-8)

### Goal
Comprehensive analysis tools and visualization.

### Deliverables

#### 4.1 Dashboard

```
frontend/src/
├── pages/
│   ├── EvaluationRuns.tsx
│   ├── RunDetail.tsx
│   └── ModelComparison.tsx
└── components/
    ├── ScoreChart.tsx
    └── TestCaseTable.tsx
```

#### 4.2 Reports

```
cli/fhir_eval/commands/
└── report.py

reports/
├── templates/
│   ├── summary.html
│   └── detailed.html
└── exports/
```

#### 4.3 Benchmark Suite

```
benchmarks/
├── configs/
│   ├── full-benchmark.yaml
│   └── quick-smoke.yaml
└── results/
```

### Success Criteria
- Interactive dashboard for results
- HTML/PDF report generation
- Reproducible benchmark runs

---

## File Structure (Final)

```
llm-fhir-query-eval/
├── backend/
│   └── src/
│       ├── api/
│       │   ├── models/
│       │   │   ├── test_case.py ✅
│       │   │   └── evaluation.py ✅
│       │   └── routes/
│       │       ├── test_cases.py ✅
│       │       └── evaluation.py (new)
│       ├── llm/
│       │   ├── base.py (new)
│       │   ├── config.py (new)
│       │   ├── registry.py (new)
│       │   └── providers/
│       │       ├── anthropic.py (new)
│       │       ├── openai.py (new)
│       │       └── ollama.py (new)
│       └── evaluation/
│           ├── runner.py (new)
│           ├── parser.py (new)
│           └── engines/
│               ├── semantic.py (new)
│               ├── execution.py (new)
│               └── llm_judge.py (new)
├── cli/
│   └── fhir_eval/
│       └── commands/
│           ├── run.py (new)
│           ├── providers.py (new)
│           ├── synthea.py (new)
│           └── report.py (new)
├── tools/
│   └── synthea_generator/
│       ├── analyzer.py (new)
│       ├── module_generator.py (new)
│       └── control_generator.py (new)
├── mcp-servers/
│   └── fhir-terminology/ (new)
├── synthea/
│   ├── modules/custom/ (new)
│   └── output/ (new)
├── test-data/
│   └── {phenotype}/ (new)
├── configs/
│   └── evaluation-profiles/ (new)
├── test-cases/
│   ├── manual/ ✅
│   └── phekb/ ✅
├── data/
│   └── phekb-raw/ ✅
└── docs/
    ├── PLAN-LLM-EXECUTION.md ✅
    ├── PLAN-TEST-DATA-GENERATION.md ✅
    └── IMPLEMENTATION-ROADMAP.md ✅
```

---

## Quick Start (After Implementation)

```bash
# 1. Generate test data for a phenotype
fhir-eval synthea generate-module type-2-diabetes
fhir-eval synthea generate-data type-2-diabetes --patients 30
fhir-eval data load --phenotype type-2-diabetes

# 2. Run evaluation against Claude
fhir-eval run --provider anthropic --model claude-sonnet-4-20250514 \
  --test-cases test-cases/phekb/phekb-type-2-diabetes.json

# 3. Compare multiple models
fhir-eval run --comparison configs/model-comparison.yaml

# 4. Generate report
fhir-eval report --run-id latest --format html
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Synthea complexity | Start with simple phenotypes, iterate |
| ICD-9 to ICD-10 mapping | Use CMS GEMs, validate manually |
| LLM rate limits | Implement backoff, parallel batching |
| Test data quality | Manual review of generated modules |
| FHIR query complexity | Start with simple queries, add complexity |

---

## Dependencies

### Required
- Python 3.11+
- Node.js 18+ (MCP servers)
- Docker (Synthea, fhir-candle)
- Java 11+ (Synthea runtime)

### API Keys
- `ANTHROPIC_API_KEY` - Claude models
- `OPENAI_API_KEY` - GPT models (optional)

### Services
- fhir-candle (Docker) - FHIR server
- Synthea (Docker) - Patient generator

---

## Next Steps

1. **Review plans** - Get feedback on approach
2. **Start Phase 1** - LLM provider layer
3. **Parallel work** - Begin Synthea exploration
4. **Iterate** - Adjust based on learnings

See detailed plans:
- [LLM Execution Framework](./PLAN-LLM-EXECUTION.md)
- [Test Data Generation](./PLAN-TEST-DATA-GENERATION.md)
