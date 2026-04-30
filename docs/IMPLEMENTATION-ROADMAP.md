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

### Three-Layer Evaluation Decomposition

Our current evaluation produces a single F1 score per test case, making it impossible to diagnose **where** in the reasoning chain the LLM failed. Inspired by FHIR-AgentBench's separation of retrieval metrics from answer correctness, and noting that neither FHIRPath-QA nor FHIR-AgentBench evaluate clinical code accuracy (our unique contribution), we define a three-layer evaluation decomposition:

#### Layer 1: Resource Type Accuracy

> "Did the LLM target the right FHIR resource type?"

- Compares the resource type in the generated query against `expected_query.resource_type` in the test case JSON
- **Binary metric**: correct or incorrect
- For multi-query test cases, check whether all required resource types were identified
- FHIR-AgentBench found this is a major failure mode — agents frequently search `Procedure` when the answer is in `Observation`
- This metric is essentially free to implement — just parse the generated query URL

#### Layer 2: Code System Accuracy

> "Did the LLM select the right clinical codes?"

This is our **UNIQUE contribution** that neither FHIRPath-QA nor FHIR-AgentBench evaluates. Neither paper tests whether LLMs can map natural clinical language to the correct code system and code.

Three sub-metrics:

- **a) Code system match**: Did the agent use the correct code system URI? (e.g., `http://snomed.info/sct` vs `http://hl7.org/fhir/sid/icd-10-cm`)
- **b) Code value match**: Did the agent select a valid code? Options for scoring: exact match against `metadata.required_codes`, OR clinically equivalent match via VSAC value set membership
- **c) Code format correctness**: Did the agent use correct FHIR code parameter syntax? (`system|code` format)

This layer directly measures the value of the UMLS/VSAC MCP server tools: **Tier 1 (no tools) vs Tier 2 (with UMLS MCP) delta on this metric isolates the impact of clinical terminology access**.

Parse `code=` parameter from generated query URL and compare against `metadata.required_codes` array in the test case JSON.

#### Layer 3: Execution Correctness

> "Does the query return the right results?"

- This is our existing F1 metric (precision/recall on patient IDs)
- Also captures query syntax validity (malformed queries → HTTP 400 → F1 = 0)
- This remains the **GROUND TRUTH** for pass/fail determination
- Subsumes Layers 1 and 2 (if both are wrong, Layer 3 will be 0; but Layer 3 can be 0 even with Layers 1 and 2 correct, e.g., correct resource type and code but wrong date filter)

#### Decomposition Summary

| Layer | Metric | Source | Implementation Cost | Key Question |
|-------|--------|--------|-------------------|--------------|
| 1. Resource Type | Binary match | `expected_query.resource_type` vs parsed generated URL | Trivial (string parse) | Did it look at the right data? |
| 2a. Code System | URI match | `metadata.required_codes[].system` vs parsed `code=` param | Low (URL parsing) | Does it know which terminology to use? |
| 2b. Code Value | Exact or VSAC-equivalent match | `metadata.required_codes[].code` vs parsed code value | Medium (VSAC lookup for lenient mode) | Can it find the right clinical concept? |
| 2c. Code Format | Syntax check | Check `system\|code` format in query params | Trivial (regex) | Does it know FHIR code parameter syntax? |
| 3. Execution | Precision/Recall/F1 on patient IDs | FHIR server query execution | Already implemented | Does the query actually work? |

#### Diagnostic Example

The three layers pinpoint exactly where in the reasoning chain the LLM failed:

```yaml
Test Case: "Find patients with acute kidney injury"
Expected: Condition?code=http://snomed.info/sct|14669001

Generated (Tier 1, closed book): Observation?code=http://loinc.org|2160-0&value-quantity=gt2||mg/dL
  Layer 1: FAIL (Observation ≠ Condition) — LLM assumed AKI is found via lab values
  Layer 2: N/A (wrong resource type, code comparison not meaningful)
  Layer 3: F1 = 0.00

Generated (Tier 2, with UMLS tools): Condition?code=http://hl7.org/fhir/sid/icd-10-cm|N17
  Layer 1: PASS (Condition = Condition)
  Layer 2a: FAIL (ICD-10 ≠ SNOMED) — correct code system for real EHRs but wrong for Synthea data
  Layer 2b: EQUIVALENT (N17 and 14669001 both represent AKI — verifiable via VSAC)
  Layer 3: F1 = 0.00 — Synthea uses SNOMED only, so ICD-10 returns no results

Generated (Tier 2, with UMLS tools + server sampling): Condition?code=http://snomed.info/sct|14669001
  Layer 1: PASS
  Layer 2a: PASS
  Layer 2b: PASS (exact match)
  Layer 3: F1 = 1.00
```

> **Key insight:** With single F1, the first two generated queries both score 0.00 and appear equally bad. With three-layer decomposition, we can see that the Tier 2 ICD-10 query was actually **MUCH closer** to correct — it identified the right resource type and a clinically valid code, but failed only because Synthea's synthetic data uses SNOMED exclusively. This kind of diagnostic granularity is essential for understanding model behavior and the value of tool access.

See `docs/literature_review.md` for the full analysis of FHIRPath-QA and FHIR-AgentBench that motivated this decomposition.

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

## Dual-Track Evaluation: Synthea + MIMIC-IV

### Why Two Tracks?

Synthea provides **controlled ground truth** — we design the modules, we know exactly which patients match each phenotype. But Synthea data is synthetic, uses only SNOMED for conditions, and lacks the messiness of real clinical records. Both FHIRPath-QA and FHIR-AgentBench use MIMIC-IV on FHIR as their data source and explicitly note the limitations of Synthea-based benchmarks.

We run **both tracks** to get the best of each:

| Track | Data Source | Ground Truth Method | Strengths | Limitations |
|-------|------------|-------------------|-----------|-------------|
| **Track A: Synthea** (Primary) | Synthea custom modules | Controlled — we built the data, we know the answer | Perfect ground truth, reproducible, multi-path phenotype coverage | Synthetic, SNOMED-only conditions, limited code system diversity |
| **Track B: MIMIC-IV** (Secondary) | MIMIC-IV on FHIR Demo (100 patients) | Comprehensive reference query with VSAC-expanded codes | Real clinical data, multi-code-system, noise and variability | Approximate ground truth, limited to 100 patients, requires manual validation |

### Track B: MIMIC-IV Ground Truth via Comprehensive Reference Queries

Since MIMIC-IV has no pre-labeled phenotype cohorts, we establish ground truth using **comprehensive reference queries** — maximally inclusive FHIR queries built from VSAC value set expansions that capture all valid codes for a phenotype across all code systems present in the data.

#### Methodology

For each phenotype evaluated on MIMIC-IV:

1. **Identify the relevant VSAC value set(s)** for the condition/phenotype. For example:
   - Type 2 Diabetes: OID `2.16.840.1.113883.3.464.1003.103.12.1001`
   - Acute Kidney Injury: search VSAC for relevant value sets

2. **Expand the value set** to get all member codes across all code systems:
   ```bash
   /umls expand <OID>
   ```
   This returns codes from SNOMED CT, ICD-10-CM, ICD-9-CM, and any other systems included in the value set.

3. **Build a comprehensive reference query** that unions all codes:
   ```
   Condition?code=http://snomed.info/sct|44054006,
     http://hl7.org/fhir/sid/icd-10-cm|E11,
     http://hl7.org/fhir/sid/icd-10-cm|E11.0,
     http://hl7.org/fhir/sid/icd-10-cm|E11.1,
     http://hl7.org/fhir/sid/icd-10-cm|E11.2,
     ...
   ```

4. **Execute the reference query** against the MIMIC-IV FHIR server and collect the patient set.

5. **Manually validate** a sample of the returned patients (spot-check 10-20 records) to confirm the reference query is correct. Document any edge cases.

6. **Store the reference patient set** in the test case JSON as `test_data.mimic_expected_patient_ids` (separate from Synthea's `expected_patient_ids`).

#### What This Tests

The MIMIC track is particularly valuable for evaluating **Layer 2 (Code System Accuracy)** because:
- MIMIC uses multiple code systems (ICD-10-CM, ICD-9-CM, SNOMED CT) for conditions — unlike Synthea which is SNOMED-only
- The LLM must choose which code system to query, or ideally query multiple
- The UMLS/VSAC MCP tools become essential for navigating this multi-code-system reality
- A generated query using ICD-10 `E11` will actually WORK on MIMIC (unlike Synthea), so Layer 3 execution scores are more meaningful for alternative code choices

#### Three-Layer Scoring on MIMIC

| Layer | Synthea Track | MIMIC Track |
|-------|--------------|-------------|
| L1: Resource Type | Same | Same |
| L2: Code Accuracy | Strict — must match Synthea's specific codes | Lenient — any code in the VSAC value set is valid |
| L3: Execution F1 | Against Synthea patient IDs (controlled) | Against comprehensive reference query patient IDs (validated) |

The key difference: On Synthea, an ICD-10 query for T2DM scores L2b=EQUIVALENT but L3=0.00 (data is SNOMED-only). On MIMIC, the same ICD-10 query scores both L2b=PASS and L3>0 (ICD-10 codes are actually present). This dual-track approach reveals whether a generated query is **clinically correct but data-mismatched** (Synthea L3 failure) vs **genuinely wrong**.

#### Phenotype Priority for MIMIC Track

Start with 3-5 well-characterized phenotypes where VSAC value sets are readily available:

| Phenotype | VSAC Value Set | Expected Code Systems in MIMIC |
|-----------|---------------|-------------------------------|
| Type 2 Diabetes | 2.16.840.1.113883.3.464.1003.103.12.1001 | ICD-10-CM, ICD-9-CM, SNOMED CT |
| Acute Kidney Injury | TBD — search VSAC | ICD-10-CM, ICD-9-CM, SNOMED CT |
| Asthma | TBD — search VSAC | ICD-10-CM, ICD-9-CM, SNOMED CT |
| Atrial Fibrillation | TBD — search VSAC | ICD-10-CM, ICD-9-CM, SNOMED CT |
| Type 2 Diabetes (meds) | RxNorm-based | RxNorm (multiple term types) |

#### Data Setup

MIMIC-IV on FHIR Demo is freely available from PhysioNet:
- Download: https://physionet.org/content/mimic-iv-fhir-demo/
- 100 de-identified patients, full FHIR R4 bundles
- Load into the same HAPI FHIR instance (separate FHIR store or tagged with source)
- Both FHIRPath-QA and FHIR-AgentBench provide loading scripts we can reference

#### Test Case Structure for MIMIC

MIMIC test cases extend the existing JSON format with a `mimic` section:

```json
{
  "id": "phekb-type-2-diabetes-dx",
  "test_data": {
    "resources": ["synthea/output/type-2-diabetes/..."],
    "expected_patient_ids": ["uuid1", "uuid2", "..."],
    "expected_result_count": 14
  },
  "mimic_test_data": {
    "reference_query_url": "Condition?code=http://snomed.info/sct|44054006,http://hl7.org/fhir/sid/icd-10-cm|E11,http://hl7.org/fhir/sid/icd-10-cm|E11.9,...",
    "reference_query_vsac_oids": ["2.16.840.1.113883.3.464.1003.103.12.1001"],
    "expected_patient_ids": ["mimic-patient-id-1", "mimic-patient-id-2", "..."],
    "expected_result_count": null,
    "validation_notes": "Manually validated 15/20 returned patients. All confirmed T2DM.",
    "validated_date": "2026-04-01"
  }
}
```

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
│  Synthea Modules │ MIMIC-IV Setup │ Data Loading │ Reference Queries │
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

#### 2.4 MIMIC-IV Data Setup (Track B)

**Key Tasks:**
- [ ] Download MIMIC-IV on FHIR Demo from PhysioNet (100 de-identified patients)
- [ ] Load MIMIC-IV FHIR bundles into HAPI FHIR (separate from Synthea data)
- [ ] For 3-5 priority phenotypes, expand VSAC value sets via `/umls expand <OID>`
- [ ] Build comprehensive reference queries covering all code systems per phenotype
- [ ] Execute reference queries, collect ground truth patient sets
- [ ] Manually validate a sample (10-20 patients) per phenotype
- [ ] Store results in test case JSON as `mimic_test_data` section

See "Dual-Track Evaluation: Synthea + MIMIC-IV" above for the full methodology.

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
- [ ] Implement Layer 1: Resource type match extraction and comparison
- [ ] Implement Layer 2: Code system and code value parsing from generated query URLs
- [ ] Implement Layer 2 lenient mode: VSAC value set membership check for clinically equivalent codes
- [ ] Add three-layer breakdown to `ExecutionResult` dataclass
- [ ] Update batch evaluation report to show per-layer metrics
- [ ] Track per-layer deltas between Tier 1 and Tier 2 to quantify UMLS MCP server impact

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
- MIMIC-IV on FHIR Demo (PhysioNet) - Real patient data for Track B evaluation

---

## Next Steps

1. **Review plans** - Get feedback on approach
2. **Start Phase 1** - LLM provider layer
3. **Parallel work** - Begin Synthea exploration
4. **Iterate** - Adjust based on learnings

See detailed plans:
- [LLM Execution Framework](./PLAN-LLM-EXECUTION.md)
- [Test Data Generation](./PLAN-TEST-DATA-GENERATION.md)
- `docs/literature_review.md` — Analysis of FHIRPath-QA and FHIR-AgentBench, and how our three-layer evaluation + UMLS/VSAC MCP tools address gaps in both benchmarks
