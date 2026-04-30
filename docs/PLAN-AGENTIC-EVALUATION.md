# Plan: Agentic LLM Evaluation with Tool Access

## Overview

Extend the evaluation framework to test LLMs not just on "closed book" FHIR query generation, but on their ability to **use tools** (UMLS code lookup, FHIR server introspection, profile/valueset awareness) to construct accurate queries. This mirrors how a real user interacts with an LLM in a chat application with MCP servers and skills.

## The Three Evaluation Tiers

| Tier | LLM Has Access To | What It Tests | Current Status |
|------|-------------------|---------------|---------------|
| **1. Closed Book** | Just the prompt | Raw FHIR + clinical knowledge | **Working** (qwen2.5:7b scored 0.00) |
| **2. Tool-Assisted** | + UMLS MCP + FHIR `/metadata` | Reasoning + tool use | Design phase |
| **3. Skill-Guided** | + IG profiles + valueset bindings + methodology skill | Following a systematic approach | Design phase |

## Dual Test Data Sets

### Problem

Synthea generates data with base FHIR profiles (SNOMED conditions, LOINC labs, RxNorm SCD meds). Real EHR data often conforms to US Core, which has specific valueset bindings and constraints. An LLM should behave differently depending on which profiles are in use.

### Solution: Two Synthea Module Variants Per Phenotype

| Variant | Profile | Condition Codes | Medication Codes | Lab Codes | When to Use |
|---------|---------|----------------|-----------------|-----------|-------------|
| **Generic** | Base FHIR R4 | SNOMED only | RxNorm SCD | LOINC | Tests basic FHIR knowledge |
| **US Core** | US Core 6.1.0 | SNOMED + ICD-10-CM (Condition.code allows both) | RxNorm (ingredient + SCD) | LOINC | Tests profile-aware querying |

The US Core variant would:
- Add ICD-10-CM codes alongside SNOMED on Condition resources (US Core Condition allows both)
- Use `Condition.category` = `problem-list-item` (US Core requires this)
- Add `Observation.category` = `laboratory` with proper US Core category coding
- Add `MedicationRequest.intent` and `.status` as required by US Core
- Add US Core-required extensions where applicable

### Module Structure

```
synthea/modules/custom/
├── phekb_type_2_diabetes.json              # Current (generic FHIR R4)
├── phekb_type_2_diabetes_control.json      # Current (generic controls)
├── phekb_type_2_diabetes_uscore.json       # US Core variant
├── phekb_type_2_diabetes_uscore_control.json
```

Output directories:
```
synthea/output/type-2-diabetes/
├── generic/
│   ├── positive/fhir/
│   └── control/fhir/
└── uscore/
    ├── positive/fhir/
    └── control/fhir/
```

### MIMIC-IV as a Third Data Source

In addition to the two Synthea variants, evaluations will also run against **MIMIC-IV on FHIR Demo** (100 real de-identified patients from PhysioNet). This creates a dual-track evaluation:

| Track | Data Source | Code Systems Present | Ground Truth | Layer 3 Behavior |
|-------|-----------|---------------------|-------------|-----------------|
| **A (Synthea Generic)** | Synthea custom modules | SNOMED conditions, LOINC labs, RxNorm SCD meds | Controlled — we built the data | ICD-10 queries return 0 results (SNOMED only) |
| **A (Synthea US Core)** | Synthea US Core variant | SNOMED + ICD-10-CM conditions, LOINC, RxNorm | Controlled | ICD-10 queries return results |
| **B (MIMIC-IV)** | MIMIC-IV on FHIR Demo | ICD-10-CM, ICD-9-CM, SNOMED CT, RxNorm, LOINC | Comprehensive reference queries (VSAC-expanded) | Any clinically valid code may return results |

MIMIC ground truth is established per-phenotype by building **comprehensive reference queries** from VSAC value set expansions and validating the resulting patient sets. See `docs/IMPLEMENTATION-ROADMAP.md` "Dual-Track Evaluation" for the full methodology.

The three-tier evaluation (Closed Book → Tool-Assisted → Skill-Guided) runs independently on each track, producing a 3×3 comparison matrix (3 tiers × 3 data tracks) per model.

## Agentic Evaluation Architecture

### Provider Interface Extension

Current `LLMProvider` has a single method:
```python
def generate_fhir_query(self, prompt: str) -> GeneratedQuery
```

For agentic evaluation, we need:
```python
class AgenticLLMProvider(LLMProvider):
    """LLM provider with tool access for agentic evaluation."""

    def __init__(self, model, tools: list[Tool], mcp_servers: list[MCPServer]):
        self.model = model
        self.tools = tools          # UMLS lookup, FHIR introspection, etc.
        self.mcp_servers = mcp_servers

    def generate_fhir_query(self, prompt: str) -> AgenticGeneratedQuery:
        """Run an agent loop: prompt → tool calls → refinement → final query."""
        # Returns the final query PLUS the full tool call trace
        pass
```

### Tool Definitions

Tools available to the LLM in agentic mode:

| Tool | Purpose | Available In |
|------|---------|-------------|
| `umls_search` | Search UMLS for clinical concepts | Tier 2, 3 |
| `umls_crosswalk` | Map codes between systems | Tier 2, 3 |
| `fhir_metadata` | Query server CapabilityStatement | Tier 2, 3 |
| `fhir_sample_data` | Sample actual data on the server | Tier 2, 3 |
| `fhir_execute_query` | Try a query and see results | Tier 2, 3 |
| `vsac_search_value_sets` | Search VSAC for curated value sets (quality measure code lists) | Tier 2, 3 |
| `vsac_expand_value_set` | Get all codes in a value set — replaces manual crosswalking | Tier 2, 3 |
| `vsac_validate_code` | Check if a code belongs to a value set | Tier 2, 3 |
| `vsac_lookup_code` | Look up code details using FHIR-native system URIs | Tier 2, 3 |
| `vsac_check_subsumption` | Check parent/child relationships in SNOMED hierarchy | Tier 2, 3 |
| `read_profile` | Read a pre-downloaded StructureDefinition | Tier 3 only |
| `read_valueset` | Read a pre-downloaded ValueSet | Tier 3 only |
| `read_ig_summary` | Read an IG summary document | Tier 3 only |

### Implementation Options (Model-Agnostic)

The agent loop needs to work with different LLM APIs:

#### Option A: Anthropic API with Tool Use
```python
class AnthropicAgenticProvider(AgenticLLMProvider):
    def generate_fhir_query(self, prompt):
        messages = [{"role": "user", "content": prompt}]
        while True:
            response = anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                tools=self.tool_definitions,
                messages=messages
            )
            if response.stop_reason == "end_turn":
                return parse_final_query(response)
            # Execute tool calls and feed results back
            for tool_use in response.content:
                if tool_use.type == "tool_use":
                    result = self.execute_tool(tool_use)
                    messages.append(tool_result(result))
```

#### Option B: OpenAI Function Calling
```python
class OpenAIAgenticProvider(AgenticLLMProvider):
    def generate_fhir_query(self, prompt):
        messages = [{"role": "user", "content": prompt}]
        while True:
            response = openai.chat.completions.create(
                model="gpt-4",
                tools=self.tool_definitions,  # OpenAI function format
                messages=messages
            )
            if response.choices[0].finish_reason == "stop":
                return parse_final_query(response)
            # Execute function calls
            for call in response.choices[0].message.tool_calls:
                result = self.execute_tool(call)
                messages.append(function_result(result))
```

#### Option C: Ollama with Manual Tool Dispatch
```python
class OllamaAgenticProvider(AgenticLLMProvider):
    def generate_fhir_query(self, prompt):
        # Ollama models don't natively support tools, so we use a
        # ReAct-style prompt with tool descriptions in the system message
        system = self.build_react_system_prompt(self.tools)
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": prompt}]
        for _ in range(MAX_ITERATIONS):
            response = ollama.chat(model=self.model, messages=messages)
            text = response.message.content
            if "FINAL ANSWER:" in text:
                return parse_final_query(text)
            # Parse tool calls from ReAct format
            tool_call = parse_react_tool_call(text)
            if tool_call:
                result = self.execute_tool(tool_call)
                messages.append({"role": "assistant", "content": text})
                messages.append({"role": "user", "content": f"Tool result: {result}"})
```

#### Option D: Claude Agent SDK (Most Native)
```python
from claude_agent_sdk import Agent, MCPServer

class ClaudeAgentProvider(AgenticLLMProvider):
    def generate_fhir_query(self, prompt):
        agent = Agent(
            model="claude-sonnet-4-20250514",
            mcp_servers=[
                MCPServer("nih-umls", command="python -m nih_umls_mcp.server"),
            ],
            tools=[fhir_metadata_tool, fhir_sample_tool, read_profile_tool],
        )
        result = agent.run(prompt)
        return parse_final_query(result)
```

### Recommended Approach: Unified Agent Loop

Build a model-agnostic agent loop that adapts to each provider:

```python
class AgentLoop:
    """Model-agnostic agent loop with tool dispatch."""

    def __init__(self, llm_adapter, tools, max_iterations=10):
        self.llm = llm_adapter      # Adapts to Anthropic/OpenAI/Ollama API
        self.tools = tools
        self.max_iterations = max_iterations

    def run(self, prompt: str) -> AgenticResult:
        trace = []  # Record all tool calls for evaluation
        messages = self.llm.init_messages(prompt, self.tools)

        for i in range(self.max_iterations):
            response = self.llm.generate(messages)

            if response.is_final:
                return AgenticResult(
                    final_response=response.text,
                    tool_trace=trace,
                    iterations=i + 1
                )

            for tool_call in response.tool_calls:
                result = self.dispatch_tool(tool_call)
                trace.append(ToolCall(
                    tool=tool_call.name,
                    input=tool_call.args,
                    output=result,
                    iteration=i
                ))
                messages = self.llm.add_tool_result(messages, tool_call, result)

        return AgenticResult(final_response="Max iterations reached", ...)
```

LLM adapters implement a simple interface:
```python
class LLMAdapter(ABC):
    def init_messages(self, prompt, tools) -> Messages: ...
    def generate(self, messages) -> LLMResponse: ...
    def add_tool_result(self, messages, tool_call, result) -> Messages: ...
```

## Pre-Downloaded IG Data

### Source Format Preference: FSH > YAML > JSON

When downloading IG profile data, prefer the most concise human-readable format:

| Format | Lines per Profile | LLM Token Cost | Source |
|--------|:-:|:-:|--------|
| **FSH (FHIR Shorthand)** | ~30-80 | Lowest | IGs authored in SUSHI/FSH (check for `input/fsh/` in IG repo) |
| **YAML StructureDefinition** | ~100-200 | Low | Some IGs (US Core 8+ uses `input/resources-yaml/`) |
| **JSON StructureDefinition** | ~500-2000 | High | All IGs publish these, but verbose |

**Why FSH first?** FHIR Shorthand is literally designed as the human-readable authoring format for FHIR conformance resources. It's like reading the source code vs. the compiled binary. Many modern IGs are authored in FSH and the source is available on GitHub.

**For IGs not authored in FSH**, the YAML StructureDefinition format (used by US Core 8+) is the next best option — roughly 5-10x smaller than JSON.

**For IGs only available as JSON**, consider using SUSHI's `goFSH` tool to reverse-engineer the JSON back to FSH. This produces readable FSH from any StructureDefinition:
```bash
# Convert JSON StructureDefinitions to FSH
npx gofsh data/ig-profiles/some-ig/ -o data/ig-profiles/some-ig/fsh/
```

### What's Downloaded

US Core 8.0.1 profiles and valuesets (YAML format, from GitHub `HL7/US-Core` repo):

```
data/ig-profiles/us-core-8.0.1/
├── StructureDefinition-us-core-condition-problems-health-concerns.yml
├── StructureDefinition-us-core-condition-encounter-diagnosis.yml
├── StructureDefinition-us-core-observation-lab.yml
├── StructureDefinition-us-core-medicationrequest.yml
├── StructureDefinition-us-core-patient.yml
├── ValueSet-us-core-condition-code-current.yml    # SNOMED + ICD-10-CM (no ICD-9 in v8!)
├── ValueSet-us-core-clinical-note-type.yml
├── ValueSet-us-core-clinical-result-observation-category.yml
└── ... (more valuesets)
```

### Key Findings from US Core 8 YAML Profiles

From examining the downloaded YAML:

**Condition.code** (`StructureDefinition-us-core-condition-problems-health-concerns.yml`):
- Binding strength: **preferred** (to `us-core-condition-code`)
- "Current" binding: `us-core-condition-code-current` (excludes ICD-9-CM, new in v8)
- Code systems: **SNOMED CT** (descendants of Clinical Finding 404684003) + **ICD-10-CM** (all codes)
- ICD-9-CM was **removed in US Core 8** for new records

**Condition.category**: **required** — must be `problem-list-item` or `health-concern`

**Observation.code**: LOINC (required for laboratory results per US Core Lab profile)

**MedicationRequest.medication[x]**: RxNorm (required for US Core)

### How the LLM Should Use This Data

In Tier 3 (Skill-Guided) evaluation, the LLM reads these FSH/YAML files to determine:
1. Which code systems are valid for each resource element
2. What binding strength applies (required vs preferred vs extensible)
3. What valueset the codes must come from
4. Whether the server uses a version that includes or excludes certain code systems

This is far more reliable than guessing from training data, and FSH/YAML is concise enough to fit in context without excessive token usage.

### How to Download IG Data for New IGs

```bash
# 1. Find the IG's GitHub repo (most HL7 IGs are on github.com/HL7/)
gh api repos/HL7/<ig-name>/git/trees/<branch>?recursive=1 --jq '.tree[].path' | grep -E "\.fsh$|\.yml$"

# 2. Prefer FSH source (input/fsh/*.fsh)
# 3. If no FSH, check for YAML (input/resources-yaml/*.yml)
# 4. If neither, download JSON from the published IG package:
npm --registry https://packages.fhir.org install <package-name>@<version>

# 5. For JSON-only IGs, convert to FSH with goFSH:
npx gofsh <json-directory> -o <fsh-output-directory>
```

## Evaluation Comparison Matrix

The final output would be a comparison across all three tiers:

```
Phenotype: Type 2 Diabetes Mellitus
Test Case: Comprehensive Provider Query (multi-query)
Expected: 20 patients (union of dx + meds + labs)

| Model           | Tier 1 (Closed) | Tier 2 (Tools) | Tier 3 (Skill) |
|-----------------|:---:|:---:|:---:|
| qwen2.5:7b      | 0.00 | ? | ? |
| qwen2.5:32b     | -    | ? | ? |
| Claude Sonnet    | -    | ? | ? |
| Claude Opus      | -    | ? | ? |
| GPT-4o           | -    | ? | ? |
| Gemini 2.0 Pro   | -    | ? | ? |

Tool Usage Analysis (Tier 2):
| Model           | UMLS Lookups | VSAC Value Sets | /metadata Checked | Data Sampled | Self-Corrected |
|-----------------|:---:|:---:|:---:|:---:|:---:|
| qwen2.5:7b      | ? | ? | ? | ? | ? |
| Claude Sonnet    | ? | ? | ? | ? | ? |
```

Three-Layer Evaluation Breakdown (per test case):
| Metric                  | Tier 1 (Closed) | Tier 2 (Tools) | Tier 3 (Skill) |
|-------------------------|:---:|:---:|:---:|
| L1: Resource Type Match | ?   | ?   | ?   |
| L2a: Code System Match  | ?   | ?   | ?   |
| L2b: Code Value Match   | ?   | ?   | ?   |
| L3: Execution F1        | ?   | ?   | ?   |

The three-layer decomposition (see `docs/IMPLEMENTATION-ROADMAP.md`) enables isolating the specific impact of each evaluation tier. We expect **Layer 2 (code system accuracy) to show the largest delta between Tier 1 and Tier 2**, directly quantifying the value of the UMLS/VSAC MCP server. Tier 3 should improve Layer 3 execution scores by teaching LLMs to sample actual server data and adapt query strategies to the Implementation Guide in use.

Dual-Track Comparison (per phenotype, per model):
```
Phenotype: Type 2 Diabetes Mellitus
Model: [model name]

| Metric        | Synthea (Track A) | MIMIC-IV (Track B) | Interpretation |
|---------------|:-:|:-:|----------------|
| L1: Resource Type | ? | ? | Should match across tracks |
| L2a: Code System  | ? | ? | MIMIC may reward ICD-10; Synthea requires SNOMED |
| L2b: Code Value   | ? | ? | MIMIC accepts broader code set via VSAC |
| L3: Execution F1  | ? | ? | MIMIC L3 validates clinically correct codes that Synthea penalizes |
```

When L3 differs across tracks (e.g., L3=0 on Synthea but L3>0 on MIMIC for the same generated query), the failure is **data-mismatch**, not clinical error. This is a key diagnostic that only dual-track evaluation can provide.

## Implementation Phases

### Phase 1: Tool Definitions + Unified Agent Loop (2-3 days)
- [ ] Define tool interfaces for UMLS, FHIR metadata, data sampling
- [ ] Build model-agnostic `AgentLoop` class
- [ ] Build `LLMAdapter` for Anthropic API (tool use)
- [ ] Build `LLMAdapter` for Ollama (ReAct-style)
- [ ] Build `AgenticResult` model with tool trace
- [ ] Extend `EvaluationRunner` with `run_agentic()` method

### Phase 2: US Core Data Variant (1-2 days)
- [ ] Download US Core 6.1.0 StructureDefinitions and ValueSets
- [ ] Create `ig-summary.md` and `valueset-bindings-summary.md`
- [ ] Create US Core variant Synthea modules (add ICD-10 codes, US Core categories)
- [ ] Generate dual data sets (generic + US Core)
- [ ] Update CLI `load` command to support `--variant generic|uscore`

### Phase 3: FHIR Server Introspection Skill (1 day)
- [ ] Load US Core profiles into HAPI FHIR
- [ ] Verify CapabilityStatement reflects loaded profiles
- [ ] Test the introspection workflow end-to-end
- [ ] Create `ig-summary.md` from actual loaded profiles

### Phase 4: Evaluation + Comparison (2-3 days)
- [ ] Run Tier 1 (closed book) for all models
- [ ] Run Tier 2 (tool-assisted) for all models
- [ ] Run Tier 3 (skill-guided) for all models
- [ ] Build comparison report
- [ ] Analyze: which models improve most with tool access?

### Phase 5: Additional LLM Providers (1-2 days)
- [ ] Build `LLMAdapter` for OpenAI API (function calling)
- [ ] Build `LLMAdapter` for Google Gemini API
- [ ] Test with GPT-4o and Gemini 2.0 Pro

## Open Questions

1. **How to handle multi-turn in evaluation scoring?** An LLM that takes 3 iterations but gets the right answer vs. one that gets it in 1 — should the former score lower?

2. **Cost tracking**: Agentic evaluation uses more tokens (tool calls + results). Should we track and report token usage per evaluation?

3. **Tool call budget**: Should we limit the number of tool calls to simulate real-world latency constraints? (e.g., max 10 tool calls)

4. **ReAct prompt engineering**: For models without native tool support (Ollama), the ReAct prompt format significantly affects quality. Should we standardize this or count it as part of the evaluation?

5. **Caching**: UMLS lookups for the same codes repeat across evaluations. Should we cache tool results to speed up batch runs?

6. **Ground truth for tool usage**: Should we define "expected tool calls" (e.g., "the LLM SHOULD have looked up the LOINC code for HbA1c") and score on that?

7. **VSAC value set caching**: Value set expansions can be large (100+ codes). Should we cache expansions to avoid repeated API calls? Should we pre-expand common value sets as part of test setup?

8. **Value set awareness scoring**: Should we give bonus points to LLMs that look up VSAC value sets to find comprehensive code lists vs. ones that only use individual code lookup?

9. **Three-layer metric aggregation**: When reporting aggregate scores across test cases, should we weight Layer 2 (code accuracy) more heavily for phenotype test cases since clinical code resolution is the primary capability being tested?

10. **Lenient vs strict code evaluation**: Should Layer 2b use exact code match (strict) or VSAC value set membership (lenient)? Strict mode penalizes clinically correct codes that don't match Synthea's generated data (e.g., ICD-10 E11 for T2DM when Synthea only generates SNOMED 44054006). Lenient mode requires VSAC API access and pre-expanded value sets. We may want to report both.
