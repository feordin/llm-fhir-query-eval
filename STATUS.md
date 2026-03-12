# Evaluation Pipeline Status

**Last Updated:** 2026-03-12

## Phenotype Progress Tracker

108 phenotypes downloaded from PheKB. 93 basic test cases auto-generated. The table below tracks the **deep evaluation pipeline** for each phenotype (algorithm analysis, multi-path test cases, Synthea data, LLM evaluation).

### Legend
- **Algorithm Analyzed**: PheKB algorithm PDF read, paths identified, codes verified via UMLS
- **Test Cases (Multi-Path)**: Per-path test cases + comprehensive provider query created
- **Synthea Module**: Multi-path module with path-specific patient generation
- **Data Generated**: Synthea patients generated and loaded into HAPI FHIR
- **Model columns**: Overall F1 score on the comprehensive (multi-query) test case. `-` = not run yet

### Evaluation Results

| Phenotype | Algorithm Analyzed | Test Cases | Synthea Module | Data Generated | qwen2.5:7b | Claude | Gemini | GPT-4 |
|-----------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Type 2 Diabetes** | Yes | 6 cases | Yes (multi-path) | 40 pos / 23 ctrl | **0.00** | - | - | - |
| Abdominal Aortic Aneurysm | No | 1 (basic) | Yes (v1) | No | - | - | - | - |
| ACE Inhibitor Cough | No | 1 (basic) | No | No | - | - | - | - |
| Acute Kidney Injury | No | 1 (basic) | No | No | - | - | - | - |
| ADHD | No | 1 (basic) | No | No | - | - | - | - |
| Anxiety | No | 1 (basic) | No | No | - | - | - | - |
| Appendicitis | No | 1 (basic) | No | No | - | - | - | - |
| Asthma | No | 1 (basic) | No | No | - | - | - | - |
| Atopic Dermatitis | No | 1 (basic) | No | No | - | - | - | - |
| Atrial Fibrillation | No | 1 (basic) | No | No | - | - | - | - |
| Autism | No | 1 (basic) | No | No | - | - | - | - |
| Breast Cancer | No | 1 (basic) | No | No | - | - | - | - |
| Chronic Kidney Disease | No | 1 (basic) | No | No | - | - | - | - |
| Colorectal Cancer | No | 1 (basic) | No | No | - | - | - | - |
| Coronary Heart Disease | No | 1 (basic) | No | No | - | - | - | - |
| *... 93 more phenotypes* | No | 1 (basic) | No | No | - | - | - | - |

### T2D Detailed Test Case Results (qwen2.5:7b)

| Test Case | Difficulty | Expected Resource | F1 | Semantic | Overall | Notes |
|-----------|-----------|-------------------|:---:|:--------:|:-------:|-------|
| Diagnosis (dx) | Easy | Condition | 0.00 | Fail | 0.00 | Used E10.0 (T1DM!), wrong resource type |
| Medications (meds) | Medium | MedicationRequest | 0.00 | Fail | 0.00 | Right resource, invented fake RxNorm codes |
| Labs HbA1c (labs) | Hard | Observation | 0.00 | Pass | 0.40 | Right structure, wrong LOINC code (2598-5) |
| Path 4 cross-resource | Expert | Patient (_has) | 0.00 | Fail | 0.00 | Mixed _has and chained syntax incorrectly |
| Comprehensive (multi-query) | Expert | Multi-query union | 0.00 | Fail | 0.15 | Generated 3 queries (good!) but all had broken syntax/codes |

## What's Built

### FHIR Servers

| Server | Port | Command | Status |
|--------|------|---------|--------|
| **HAPI FHIR** (default) | 8080 | `docker-compose up -d fhir-server` | Working |
| **Azure FHIR** | 9080 | `docker-compose up -d azure-fhir` | Configured (needs SQL Server) |

### Evaluation Pipeline

- **Multi-query support**: Test cases with `multi_query: true` are evaluated by unioning patient IDs across all generated queries
- **Patient-level scoring**: Comprehensive test cases compare patient IDs (not resource IDs) across multiple FHIR resource types
- **Query coverage scoring**: Checks how many expected resource types the LLM searched (Condition, MedicationRequest, Observation)
- **Multi-query parser**: Extracts all FHIR queries from an LLM response (handles multi-line responses)

### LLM Providers

| Provider | Command | Status | Cost |
|----------|---------|--------|------|
| Anthropic SDK | `-p anthropic` | Credits depleted | API credits |
| Claude CLI | `-p claude-cli` | `--print` requires API credits | API credits |
| Ollama (local) | `-p command --command "ollama run <model>"` | Working | Free |

### Skills

| Skill | Purpose |
|-------|---------|
| `/synthea` | Generate Synthea modules and test data (multi-path, dual generic/US Core variants) |
| `/umls` | Verify clinical codes via NIH UMLS MCP |
| `/phenotype_test_case` | Analyze algorithms, create per-path test cases, comprehensive provider queries, validate against FHIR |
| `/fhir_server_introspection` | Teach LLM to introspect server capabilities, profiles, valuesets for Tier 2/3 eval |

### Evaluation Tiers (Planned)

| Tier | LLM Has Access To | Status |
|------|-------------------|--------|
| **1. Closed Book** | Just the prompt | **Working** — first results with qwen2.5:7b |
| **2. Tool-Assisted** | + UMLS MCP + FHIR `/metadata` | Design complete (see `docs/PLAN-AGENTIC-EVALUATION.md`) |
| **3. Skill-Guided** | + IG profiles (FSH/YAML) + valueset bindings + introspection skill | Design complete |

### IG Profile Data

Format preference: **FSH > YAML > JSON** (FSH is most concise for LLM context windows).

| IG Version | Format | FSH Available | Condition.code Systems |
|------------|--------|:---:|----------------|
| **US Core 6.1.0** | JSON | Yes (via `goFSH`) | SNOMED + ICD-10-CM + **ICD-9-CM** |
| **US Core 8.0.1** | YAML | No (YAML readable) | SNOMED + ICD-10-CM (**ICD-9 removed**) |

Both downloaded to `data/ig-profiles/`. See `data/ig-profiles/README.md` for details.

## How to Run Evaluations

```bash
# 1. Start FHIR server
docker-compose up -d fhir-server

# 2. Install CLI
cd cli && pip install -e . && cd ..

# 3. Load test data for a phenotype
fhir-eval load synthea -p type-2-diabetes --update-test-case

# 4. Run evaluation with a model
fhir-eval run -t phekb-type-2-diabetes-comprehensive -p command --command "ollama run qwen2.5:7b" -v

# 5. Run all T2D test cases
for tc in dx meds labs path4-meds-labs comprehensive; do
  fhir-eval run -t phekb-type-2-diabetes-$tc -p command --command "ollama run qwen2.5:7b"
done

# 6. Results saved to results/ directory
ls results/
```

## Remaining Work

### Immediate — Tier 1 (Closed Book) Completion
1. **Add API credits** for Anthropic/Claude evaluation
2. **Add OpenAI provider** for GPT-4 evaluation
3. **Add Gemini provider** for Google model evaluation
4. **Try larger Ollama models** (qwen2.5:32b, llama3.1:70b)
5. **Expand phenotypes** — run `/phenotype_test_case analyze` on Asthma, Atrial Fibrillation, CKD next

### Tier 2/3 — Agentic Evaluation (see `docs/PLAN-AGENTIC-EVALUATION.md`)
1. Build model-agnostic `AgentLoop` with tool dispatch
2. Build `LLMAdapter` for Anthropic API (tool use), OpenAI (function calling), Ollama (ReAct)
3. Create US Core variant Synthea modules (dual data sets)
4. Load US Core profiles into HAPI FHIR
5. Run comparative eval: Closed Book vs Tool-Assisted vs Skill-Guided
6. Analyze which models improve most with tool access

### Framework Improvements
1. Add batch runner (`fhir-eval run-all` across all test cases)
2. Build results comparison dashboard
3. Add LLM judge evaluator (currently stubbed)
4. Add code system validation evaluator (currently stubbed)
5. Support "acceptable alternative" queries (e.g., ICD-10 E11 is valid even if SNOMED expected)
6. Track token usage and cost per evaluation

## Resolved Issues

### Synthea T2D Module (Fixed 2026-03-12)
- Added `"wellness": true` on Encounter states
- Moved ConditionOnset inside encounters
- Upgraded to SCD-level RxNorm codes verified via UMLS
- Added multi-path generation: 70% diagnosed (Paths 1-3,5), 30% no-diagnosis (Path 4)

### FHIR Server Switch (Fixed 2026-03-12)
- Replaced fhir-candle (data loss due to healthcheck-triggered restarts) with HAPI FHIR
- Fixed bundle load order (infrastructure files first)
- Added Azure FHIR as second option

### Multi-Query Evaluation (Added 2026-03-12)
- Extended runner to detect `multi_query: true` test cases
- Added patient-level union evaluation across multiple generated queries
- Added query coverage scoring (how many expected resource types covered)
- Added multi-query parser for LLM responses

## File Map

| File | Status | Purpose |
|------|--------|---------|
| `backend/src/fhir/client.py` | Done | FHIR server client |
| `backend/src/llm/provider.py` | Updated | Multi-query parser, updated system prompt |
| `backend/src/llm/anthropic_provider.py` | Done | Anthropic SDK provider |
| `backend/src/llm/cli_delegate_provider.py` | Updated | Fixed `--print` flag usage |
| `backend/src/llm/command_provider.py` | Done | Generic command provider |
| `backend/src/evaluation/execution.py` | Updated | Added patient-level union evaluation |
| `backend/src/evaluation/semantic.py` | Done | Semantic query evaluator |
| `backend/src/evaluation/runner.py` | Updated | Multi-query detection and evaluation |
| `backend/src/api/models/evaluation.py` | Updated | Multi-query GeneratedQuery model |
| `backend/src/api/models/test_case.py` | Updated | Multi-query metadata fields |
| `cli/fhir_eval/commands/load.py` | Updated | Loads infra files first |
| `cli/fhir_eval/commands/run.py` | Updated | Multi-query display |
| `synthea/modules/custom/phekb_type_2_diabetes.json` | Done | Multi-path T2DM module |
| `synthea/modules/custom/phekb_type_2_diabetes_control.json` | Done | Control patients |
| `test-cases/phekb/phekb-type-2-diabetes-*.json` | Done | 6 test cases (dx, meds, labs, path4, comprehensive, base) |
| `.claude/skills/phenotype_test_case/SKILL.md` | Done | Algorithm analysis + test case creation methodology |
| `.claude/skills/synthea/SKILL.md` | Updated | Multi-path modules, GMF patterns, server compat |
| `.claude/skills/umls/SKILL.md` | Done | UMLS code lookup and crosswalk |
| `.claude/skills/fhir_server_introspection/SKILL.md` | Done | Server introspection workflow for agentic eval |
| `docs/PLAN-AGENTIC-EVALUATION.md` | Done | Full architecture for 3-tier agentic evaluation |
| `data/ig-profiles/us-core-8.0.1/` | Downloaded | US Core 8 YAML profiles and valuesets |
| `docker-compose.yml` | Updated | HAPI FHIR + Azure FHIR |
