# Papers

- **FHIRPath-QA: Executable Question Answering over FHIR Electronic Health Records**
   M. Frew, Nishit Bheda, Bryan Tripp
   arXiv.org 2026
   [open paper page](https://api.semanticscholar.org/CorpusId:286170906)
   <details>
     <summary> Abstract </summary>
     Though patients are increasingly granted digital access to their electronic health records (EHRs), existing interfaces may not support precise, trustworthy answers to patient-specific questions. Large language models (LLM) show promise in clinical question answering (QA), but retrieval-based approaches are computationally inefficient, prone to hallucination, and difficult to deploy over real-life EHRs. This work introduces FHIRPath-QA, the first open dataset and benchmark for patient-specific QA that includes open-standard FHIRPath queries over real-world clinical data. A text-to-FHIRPath QA paradigm is proposed that shifts reasoning from free-text generation to FHIRPath query synthesis. For o4-mini, this reduced average token usage by 391x relative to retrieval-first prompting (629,829 vs 1,609 tokens per question) and lowered failure rates from 0.36 to 0.09 on clinician-phrased questions. Built on MIMIC-IV on FHIR Demo, the dataset pairs over 14k natural language questions in patient and clinician phrasing with validated FHIRPath queries and answers. Empirically, the evaluated LLMs achieve at most 42% accuracy, highlighting the challenge of the task, but benefit strongly from supervised fine-tuning, with query synthesis accuracy improving from 27% to 79% for 4o-mini. These results highlight that text-to-FHIRPath synthesis has the potential to serve as a practical foundation for safe, efficient, and interoperable consumer health applications, and the FHIRPath-QA dataset and benchmark serve as a starting point for future research on the topic. The full dataset and generation code can be accessed at: https://github.com/mooshifrew/fhirpath-qa.
  </details>

### Key Findings & Relevance to Our Work

- **Task framing**: Proposes text-to-FHIRPath (not FHIR REST API queries). This is a complementary but distinct task from ours — FHIRPath operates on in-memory resources, while we evaluate REST search query generation against a live FHIR server.
- **Data source**: Built on MIMIC-IV on FHIR Demo (100 real patients), not synthetic data like Synthea. Demonstrates the value of real clinical data for evaluation.
- **Efficiency**: Query-first paradigm reduces token usage **391×** vs retrieval-first (1,609 vs 629,829 tokens/question), strongly motivating the query-generation approach over RAG for FHIR QA.
- **Base model accuracy**: Best base model accuracy is only **42% (o4-mini)**, confirming that FHIR query generation from natural language is a genuinely hard task for current LLMs.
- **Supervised fine-tuning (SFT)**: SFT boosts 4o-mini from **27% → 79%** — a massive improvement, suggesting fine-tuning is a high-leverage future direction.
- **Generalization tests (3 axes)**:
  - Novel paraphrases of seen queries → SFT helps
  - Unseen query logic patterns → SFT helps
  - Unseen resource types → SFT **hurts** (overfitting to seen resource types)
- **Dual perspectives**: Clinician vs patient phrasing of the same questions. Retrieval-based approaches favor clinician language; query generation favors patient language. This has implications for how we phrase our test case prompts.
- **Error modes**:
  - Resource profile misunderstanding (wrong resource type or field)
  - Semantic misinterpretation (e.g., confusing MedicationRequest vs MedicationAdministration)
  - Date filter mismatch (~30% of fine-tuned model errors)
- **Critical gap**: Does **NOT** evaluate clinical code accuracy. Codes are embedded in templates, not LLM-generated. The LLM never has to resolve "type 2 diabetes" → `http://hl7.org/fhir/sid/icd-10-cm|E11`. This is exactly the gap our framework targets.
- **FHIR server**: Uses HAPI FHIR, same technology stack as our project.

---

- **FHIR-AgentBench: Benchmarking LLM Agents for Realistic Interoperable EHR Question Answering**
   Gyubok Lee, Elea Bach, Eric Yang, Tom J. Pollard, Alistair Johnson, Edward Choi, Yugang Jia, Jong Ha Lee
   arXiv.org 2025
   [open paper page](https://api.semanticscholar.org/CorpusId:281505607)
   <details>
     <summary> Abstract </summary>
     The recent shift toward the Health Level Seven Fast Healthcare Interoperability Resources (HL7 FHIR) standard opens a new frontier for clinical AI, demanding LLM agents to navigate complex, resource-based data models instead of conventional structured health data. However, existing benchmarks have lagged behind this transition, lacking the realism needed to evaluate recent LLMs on interoperable clinical data. To bridge this gap, we introduce FHIR-AgentBench, a benchmark that grounds 2,931 real-world clinical questions in the HL7 FHIR standard. Using this benchmark, we systematically evaluate agentic frameworks, comparing different data retrieval strategies (direct FHIR API calls vs. specialized tools), interaction patterns (single-turn vs. multi-turn), and reasoning strategies (natural language vs. code generation). Our experiments highlight the practical challenges of retrieving data from intricate FHIR resources and the difficulty of reasoning over them, both of which critically affect question answering performance. We publicly release the FHIR-AgentBench dataset and evaluation suite (https://github.com/glee4810/FHIR-AgentBench) to promote reproducible research and the development of robust, reliable LLM agents for clinical applications.
  </details>

### Key Findings & Relevance to Our Work

- **Scale**: 2,931 real-world questions sourced from EHRSQL, grounded in MIMIC-IV-FHIR — substantially larger than FHIRPath-QA's dataset.
- **Agent architectures compared (5 variants)**:
  1. Single-turn FHIR query generation
  2. Single-turn retriever
  3. Single-turn retriever + code interpreter
  4. Multi-turn retriever
  5. Multi-turn retriever + code interpreter
- **Best configuration**: Multi-turn + retriever + code interpreter achieves **50% accuracy** (o4-mini). This is the current state-of-the-art for agentic FHIR QA.
- **Multi-turn improves recall**: 71% vs 58% for single-turn — iterative refinement is critical for navigating FHIR's complex resource graph.
- **Code interpreter is the biggest lever**: Jumps correctness from **20% → 50%**. The ability to programmatically process retrieved FHIR resources is more impactful than any other single architectural choice.
- **Model choice matters LESS than architecture**: All models achieve 44–50% on the best architecture. Architecture design dominates model selection.
- **Evaluation metrics**: Uses retrieval precision/recall AND answer correctness as separate metrics — a good decomposition we should consider adopting.
- **Realistic empty answers**: 24% of questions correctly have empty answers, testing whether models can appropriately return "no results" rather than hallucinating.
- **Error modes**:
  - Wrong resource type selection
  - Overly-specific queries that miss valid results
  - Failure to follow FHIR references (e.g., `medicationReference` → `Medication` resource)
  - Text matching vs code matching confusion
- **Critical gap**: Does **NOT** use clinical terminology tools (UMLS, VSAC, or any code resolution service). This is a significant gap — our framework fills this with the UMLS/VSAC MCP server integration.
- **Models tested**: o4-mini, Gemini-2.5-Flash, Qwen3-32B, LLaMA-3.3-70B — provides a useful baseline model set for comparison.

---

## Synthesis & Implications for Our Framework

### 1. Clinical Code Resolution Is the Unaddressed Gap

Neither paper evaluates the ability of LLMs to resolve natural language clinical concepts into correct code systems and codes (e.g., "type 2 diabetes" → `http://hl7.org/fhir/sid/icd-10-cm|E11`). FHIRPath-QA embeds codes in templates; FHIR-AgentBench relies on text matching or pre-coded queries. **This is our unique contribution** — our framework tests NL → correct code system + code mapping, supported by UMLS/VSAC MCP server integration for validation.

### 2. Dual-Track Evaluation: Synthea + MIMIC-IV

Both papers use MIMIC-IV on FHIR (real clinical data) and explicitly note limitations of Synthea-based benchmarks. **Decision: We will run a dual-track evaluation.**

- **Track A (Synthea)**: Primary track with controlled ground truth. We design the data, we know exactly which patients match. Tests code specificity — the LLM must find the exact codes present in Synthea data.
- **Track B (MIMIC-IV)**: Secondary track with real clinical data. Ground truth established via **comprehensive reference queries** built from VSAC value set expansions covering all valid codes across all code systems. Tests code breadth — any clinically valid code that returns real patients is correct.

This dual-track design directly exploits our three-layer evaluation: on Synthea, an ICD-10 query for T2DM scores L2b=EQUIVALENT but L3=0.00 (data is SNOMED-only). On MIMIC, the same query scores L2b=PASS and L3>0 (ICD-10 codes are present). Together, the two tracks distinguish **clinically correct but data-mismatched** from **genuinely wrong** — a distinction invisible in single-track evaluation. See `docs/IMPLEMENTATION-ROADMAP.md` "Dual-Track Evaluation" for the full specification.

### 3. Three-Layer Evaluation Decomposition

The literature suggests evaluation should be decomposed into three independent layers:

| Layer | What It Measures | FHIRPath-QA | AgentBench | Our Framework |
|-------|-----------------|-------------|------------|---------------|
| **(a) Resource type accuracy** | Correct FHIR resource selection | ✅ (partial) | ✅ | ✅ |
| **(b) Clinical code accuracy** | NL → correct code system + code | ❌ (codes in templates) | ❌ (no code tools) | ✅ (our focus) |
| **(c) Query execution / answer correctness** | End-to-end correct answer | ✅ | ✅ | ✅ |

Neither paper isolates clinical code accuracy because neither tests NL → code mapping. Our phenotype-based test cases with code-free prompts are uniquely positioned to fill this gap.

### 4. Models to Benchmark Against

From the two papers, a combined model set for comparison:

- **From FHIRPath-QA**: o4-mini, 4o-mini, 4.1-mini, 4.1-nano
- **From FHIR-AgentBench**: o4-mini, Gemini-2.5-Flash, Qwen3-32B, LLaMA-3.3-70B

Priority: **o4-mini** (appears in both, consistently top performer), **4o-mini** (SFT baseline from FHIRPath-QA), and at least one open-weight model (Qwen3-32B or LLaMA-3.3-70B) for reproducibility.

### 5. Code Interpreter / Code Generation Is Critical

FHIR-AgentBench shows that adding a code interpreter is the single highest-leverage architectural choice (20% → 50% accuracy). This validates our planned agentic evaluation tiers (see `docs/PLAN-AGENTIC-EVALUATION.md`) — agents that can write and execute code to process FHIR responses will significantly outperform pure query generators.

### 6. Supervised Fine-Tuning as a Future Direction

FHIRPath-QA demonstrates that SFT can boost accuracy from 27% → 79% on the target task. However, it also shows overfitting risks (SFT hurts on unseen resource types). If we pursue SFT, our phenotype-based test cases with diverse resource types provide natural held-out evaluation sets for measuring generalization.

### 7. Complementary Test Design Philosophy

Our phenotype-based test design (multi-path clinical algorithms, code-free prompts) is complementary to both papers' approaches:

- **FHIRPath-QA**: Template-based questions, single-resource queries, codes provided
- **FHIR-AgentBench**: EHRSQL-derived questions, multi-resource reasoning, codes provided or text-matched
- **Our framework**: PheKB phenotype algorithms decomposed into per-path test cases, no codes in prompts, tests full NL → FHIR query pipeline including clinical terminology resolution

This positions our work as filling a distinct and important niche in the FHIR + LLM evaluation landscape.