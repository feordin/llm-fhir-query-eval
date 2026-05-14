# Plan: Cloud Frontier Model Evaluation

> **Status**: Phase 0 complete (committed `7d56661c`). Phase 1a (Azure provisioning) in progress.
>
> **Created**: 2026-05-05 | **Updated**: 2026-05-14

## Problem Statement

The evaluation framework currently runs only against local Ollama models (qwen3:8b).
We need to run the full 3×3 matrix (3 prompt variants × 3 tiers) across frontier
models from Anthropic, OpenAI, and Google, plus a cloud-hosted small model.

**Evaluation matrix** (per test case, per model):
- **Prompt variants**: `naive`, `broad`, `expert`
- **Tiers**: T1 (closed-book), T2 (agentic with tools), T3 (agentic + methodology skill)
- **Tools available to T2/T3**: `fhir_server_metadata`, `fhir_search`, `fhir_resource_sample`,
  `umls_search`, `umls_crosswalk`, `vsac_search_value_sets`, `vsac_expand_value_set`,
  `vsac_validate_code`, `vsac_lookup_code`, `vsac_check_subsumption`

**Scale**: ~100 phenotypes × ~3 test cases × 9 cells = ~2,700 cells per model × 4 models.

**Tier focus**: This evaluation is anchored at the **workhorse tier** (Claude Sonnet 4.6 class).
All target models are chosen to match that tier on positioning and pricing, so the model is
the only variable rather than the capability class. Flagship-tier comparisons (Opus 4.7 /
GPT-5.5 standard / Gemini 3 Pro) are out of scope for the initial run but can be added as
a separate track once the workhorse-tier baseline is established.

## Key Design Decision: Azure AI Foundry as Unified Backend

Azure AI Foundry can host models from all three major providers through a single
OpenAI-compatible API. This is ideal for the standardized comparison track because
it normalizes the wire format, making the model the only variable.

| Criterion | Azure Foundry (Track S) | Native SDKs (Track O) | Copilot SDK (Track C) |
|-----------|------------------------|----------------------|----------------------|
| Scientific control | ✅ Same API for all models | ⚠️ Per-provider API differences | ❌ Copilot loop is a confound |
| Tool calling | ✅ Unified OpenAI format | ✅ Native format per model | ⚠️ Normalized by SDK |
| Model-specific features | ❌ Normalized away | ✅ Extended thinking, etc. | ❌ Limited |
| Auth / billing | ✅ Single Azure subscription | ❌ Per-provider API keys | ⚠️ BYOK + Copilot quota |
| MCP integration | ❌ HTTP tool wrappers | ❌ HTTP tool wrappers | ✅ Native MCP |
| Small model (Qwen) | ✅ Serverless endpoint | N/A | ✅ Via BYOK Ollama |

## Benchmark Tracks

### Track S (Standardized) — Primary

All models hosted on Azure AI Foundry behind OpenAI-compatible endpoints.
Same agentic loop, same tool format, same prompt envelope. The ONLY variable
is the model. This is the publishable comparison.

**Local Qwen option**: For development/debugging or cost savings, Qwen can also
run locally via Ollama. The `OllamaAdapter` (existing) serves as the local
backend, while the Azure serverless endpoint is the cloud backend. Both use the
same OpenAI-compatible tool calling format, so results are comparable.

### Track O (Optimized) — Secondary

Native SDKs with model-specific features enabled (Claude extended thinking,
OpenAI structured outputs, Gemini grounding). Shows "best possible" per model.
Not directly comparable across models.

### Track C (Copilot SDK) — Tertiary

Same models routed through GitHub Copilot SDK (`github-copilot-sdk` Python package)
agent loop with native MCP tools. Compares our custom agentic loop vs Copilot's
built-in orchestration. Uses BYOK to route to each provider.

## Target Models

Workhorse-tier lineup (~$3–5 input / ~$15–30 output per Mtok class):

| Model | Provider | Azure Deployment | Track S (Azure) | Track S (Local) | Track O | Track C |
|-------|----------|-----------------|-----------------|-----------------|---------|---------|
| Claude Sonnet 4.6 | Anthropic | Serverless API | ✅ | — | ✅ (native Anthropic SDK) | ✅ |
| GPT-5.5 Instant | OpenAI | Azure OpenAI | ✅ | — | ✅ (native OpenAI SDK) | ✅ |
| Gemini 3 Flash | Google | Serverless API | ✅ | — | ✅ (native Google SDK) | ✅ |
| Qwen3.5-9B | Alibaba | Serverless API | ✅ | ✅ (Ollama) | — | ✅ |

**Tier-mapping rationale** (see Open Question #6 below for the full analysis):
- Claude Sonnet 4.6 is the anchor (Anthropic's workhorse, $3/$15 per Mtok).
- GPT-5.5 Instant is OpenAI's workhorse counterpart. GPT-5.5 standard prices at $5/$30 and
  benchmarks head-to-head against Opus 4.7 — that's a flagship-tier match, not a Sonnet
  match. Instant is the right Sonnet 4.6 peer.
- Gemini 3 Flash matches the workhorse positioning and pricing; Gemini 3 Pro would be the
  Opus 4.7 peer.
- Qwen3.5-9B is the small open-source baseline, with optional local Ollama fallback for
  cost/sanity comparison.

---

## Architecture

### Current Code (key files)

| File | Role |
|------|------|
| `scripts/run_workload.py` | Top-level runner: iterates phenotypes, calls sanity matrix per test case |
| `scripts/run_sanity_matrix.py` | Runs 3×3 matrix for one test case + model. Subprocess per cell. |
| `backend/src/llm/provider.py` | `LLMProvider` ABC, `FHIR_SYSTEM_PROMPT`, `build_generated_query()`, parsers |
| `backend/src/llm/agentic_provider.py` | `OllamaAgenticProvider` — agentic loop with 10 tools, Ollama backend |
| `backend/src/llm/command_provider.py` | `CommandProvider` — Tier 1 closed-book via `ollama run <model>` |
| `backend/src/llm/__init__.py` | `get_provider()` factory |
| `backend/src/api/models/evaluation.py` | `GeneratedQuery`, `RunMetadata`, `EvaluationResult` models |
| `backend/src/evaluation/runner.py` | `EvaluationRunner` — orchestrates LLM → FHIR → scoring |
| `backend/src/evaluation/execution.py` | Patient-set comparison (union, difference) |
| `docs/eval-workloads.json` | Phenotype → machine assignment for parallel workloads |

### Version Constants (bump when changing prompts/tools)

| Constant | File | Current |
|----------|------|---------|
| `FHIR_SYSTEM_PROMPT_VERSION` | `backend/src/llm/provider.py` | `1.0.0` |
| `AGENTIC_SYSTEM_PROMPT_VERSION` | `backend/src/llm/agentic_provider.py` | `2.0.0` |
| `TOOL_SCHEMA_VERSION` | `backend/src/llm/agentic_provider.py` | `1.0.0` |

---

## Implementation Phases

### Phase 0: Pre-requisites ✅ DONE (commit `7d56661c`)

All four completed:

- **0a. Multi-query/fallback correctness**: Added `build_generated_query()` helper in
  `provider.py` that uses plural parser first. All providers (Anthropic, CLI, Command,
  Agentic) updated. Agentic fallback now collects ALL `fhir_search` queries from tool
  trace instead of just the last one. The runner's `_run_multi_query()` still re-parses
  as a safety net, but providers now preserve multi-query responses at the source.

- **0b. Audit-grade run metadata**: New `RunMetadata` Pydantic model with 17 optional
  fields (provider_backend, model_version, tier, tool_transport, iterations_used,
  stop_reason, fallback_used, tool_calls_count, elapsed_sec, system_prompt_version,
  tool_schema_version, etc.). Added to `EvaluationResult` as optional field. Agentic
  provider populates at all exit paths. `run_sanity_matrix.py` emits it in result JSON
  along with hostname, timestamp, and prompt version metadata.

- **0c. Secrets cleanup**: Removed `.mcp.json` file fallback from `_get_umls_api_key()`.
  UMLS API key must now be set via `UMLS_API_KEY` env var only. Logs clear warning when
  missing. Verified no secrets were ever committed to git (`.mcp.json` and `.env` have
  always been in `.gitignore`).

- **0d. Version prompt/tool contract**: Three version constants added and included in
  sanity matrix result JSON under `prompt_versions` key.

### Phase 1: Azure AI Foundry Setup + Adapter Layer

#### 1a. Azure Resource Provisioning

Deploy model endpoints in Azure AI Foundry:

```
Azure AI Foundry Project
├── Azure OpenAI resource (GPT models)
│   └── gpt-5.5-instant deployment
├── Serverless API deployments (Model Catalog — pay-per-token)
│   ├── Claude Sonnet 4.6        (Anthropic via Azure)
│   ├── Gemini 3 Flash           (Google via Azure)
│   └── Qwen3.5-9B               (Alibaba via Azure)
└── Shared config
    ├── API key (single key for all endpoints)
    └── Region: chosen for model availability
```

**Environment variables** (all from one Azure subscription):
```bash
AZURE_FOUNDRY_ENDPOINT=https://<project>.services.ai.azure.com
AZURE_FOUNDRY_API_KEY=<key>
# Per-deployment model names map to Azure deployment IDs
```

**Action**: Manual Azure Portal / CLI provisioning. Check [Azure AI Foundry model catalog](https://ai.azure.com/explore/models) for regional availability of all target models. **Availability caveat**: GPT-5.5 Instant launched 2026-05-05 and Gemini 3 Flash is recent — both may not yet be in every Foundry region as serverless deployments. If a model is missing, either switch region or fall back temporarily to the next-newest variant of the same family (e.g., a prior Gemini Flash or GPT-5.4 Instant) and document the substitution in `RunMetadata.model_version`.

#### 1b. Normalized Agent Protocol

Create a normalized message protocol so the agentic loop is adapter-agnostic:

```python
# backend/src/llm/adapters/protocol.py

@dataclass
class NormalizedToolCall:
    id: str
    name: str
    arguments: dict

@dataclass
class NormalizedMessage:
    role: str                              # "system", "user", "assistant", "tool"
    content: str | None
    tool_calls: list[NormalizedToolCall]    # populated for assistant tool-call turns
    tool_call_id: str | None               # populated for tool-result turns

@dataclass
class NormalizedUsage:
    input_tokens: int
    output_tokens: int

@dataclass
class NormalizedResponse:
    message: NormalizedMessage
    finish_reason: str                     # "stop", "tool_calls", "length"
    usage: NormalizedUsage | None

class ChatAdapter(ABC):
    """Adapter ABC. One method: send messages, get normalized response."""
    @abstractmethod
    def chat(self, messages: list[NormalizedMessage],
             tools: list[dict] | None = None) -> NormalizedResponse: ...

    @property
    @abstractmethod
    def backend_name(self) -> str: ...     # "azure", "ollama", etc.
```

**Provider adapters**:

- **`AzureOpenAIAdapter`** — wraps `openai.AzureOpenAI` client. Single adapter for ALL
  Azure-hosted models (GPT, Claude, Gemini, Qwen). Different deployment names passed
  at construction. This is the Track S workhorse.
  ```python
  # Uses openai Python SDK with azure-specific params
  from openai import AzureOpenAI
  client = AzureOpenAI(
      azure_endpoint=os.environ["AZURE_FOUNDRY_ENDPOINT"],
      api_key=os.environ["AZURE_FOUNDRY_API_KEY"],
      api_version="2024-10-21",
  )
  response = client.chat.completions.create(
      model=deployment_name,  # e.g. "claude-sonnet-4", "gpt-4.1"
      messages=..., tools=...,
  )
  ```

- **`OllamaAdapter`** — wraps existing `ollama.chat()` for local Qwen. Refactored from
  the current `OllamaAgenticProvider` to use normalized protocol.

**Conformance tests**: 5-10 golden tool-calling scenarios that both adapters must handle
identically (same normalized output for the same logical conversation).

#### 1c. Model Configuration Registry

```python
# backend/src/llm/model_registry.py
AZURE_MODELS = {
    "claude-sonnet-4.6": {"deployment": "claude-sonnet-4-6", "provider": "anthropic", "tier": "workhorse"},
    "gpt-5.5-instant":   {"deployment": "gpt-5.5-instant",   "provider": "openai",    "tier": "workhorse"},
    "gemini-3-flash":    {"deployment": "gemini-3-flash",    "provider": "google",    "tier": "workhorse"},
    "qwen3.5-9b":        {"deployment": "qwen3-5-9b",        "provider": "alibaba",   "tier": "small",
                           "local_fallback": "qwen3.5:9b"},
}

LOCAL_MODELS = {
    "qwen3.5:9b": {"backend": "ollama", "tier": "small"},
}
```

### Phase 2: Generic AgenticProvider

Refactor `OllamaAgenticProvider` → `AgenticProvider(adapter: ChatAdapter)`:

- System prompt, tool definitions, iteration logic stay **constant**
- Tool definitions already use OpenAI-compatible JSON Schema format
- Adapter handles the actual chat API call and response normalization
- Same fallback strategy (retry → last assistant → last fhir_search)
- `RunMetadata.provider_backend` set dynamically from `adapter.backend_name`

For Tier 1: `ClosedBookProvider(adapter: ChatAdapter)` — single prompt→response, no tools.

**Key refactoring pattern**:
```python
# Before (Ollama-specific):
response = ollama.chat(model=self.model, messages=messages, tools=tools)
msg = response["message"]

# After (adapter-agnostic):
response = self.adapter.chat(messages=normalized_messages, tools=tool_defs)
msg = response.message  # NormalizedMessage
```

Update `get_provider()` factory in `__init__.py`:
```python
def get_provider(name: str, model: str = None, **kwargs) -> LLMProvider:
    if name == "azure":
        adapter = AzureOpenAIAdapter(deployment=model, ...)
        return AgenticProvider(adapter, tier=kwargs.get("tier", 2), ...)
    elif name == "ollama-agentic":
        adapter = OllamaAdapter(model=model)
        return AgenticProvider(adapter, tier=kwargs.get("tier", 2), ...)
    ...
```

### Phase 3: Timeouts & Cost Controls

**Timeout policy**:

| Backend | Model Request Timeout | Tool Timeout | Per-Cell Wall-Clock |
|---------|----------------------|-------------|-------------------|
| Ollama (local) | 120s | 30s | 300s |
| Azure (all models) | 60s | 30s | 600s |

**Cost gates**:
- **Pilot-first**: Run on 5 representative phenotypes before full suite
- **Per-cell token budget**: Cap at 100K input + 10K output tokens per cell
- **Azure spend alerts**: Set daily budget in Azure Cost Management
- **Early-stop**: If first 5 phenotypes all score F1=0 for T2/T3, abort and diagnose
- **Tool response caching**: Cache UMLS/VSAC responses (deterministic) across cells.
  Key = (tool_name, args_hash) → result. Saves both latency and UMLS rate limit headroom.

### Phase 4: Copilot SDK Integration (Track C)

Uses the `github-copilot-sdk` Python package with BYOK:

```python
from copilot import CopilotClient
from copilot.session import PermissionHandler

client = CopilotClient()
session = await client.create_session(
    model="claude-sonnet-4",
    provider={"type": "anthropic", "base_url": "https://api.anthropic.com",
              "api_key": os.environ["ANTHROPIC_API_KEY"]},
    system_message={"content": AGENTIC_SYSTEM_PROMPT},
    mcp_servers={
        "nih-umls": {
            "type": "local",
            "command": "python",
            "args": ["-m", "nih_umls_mcp.server"],
            "env": {"UMLS_API_KEY": os.environ["UMLS_API_KEY"]},
            "tools": ["*"],
        }
    },
    tools=[fhir_search_tool, fhir_metadata_tool, fhir_sample_tool],
    on_permission_request=PermissionHandler.approve_all,
)
```

Key: Our FHIR-specific custom tools + the MCP server for UMLS/VSAC.
This is a **separate evaluation track** — never mixed with Track S results.

Copilot SDK supports BYOK for: `openai`, `azure`, `anthropic`, and OpenAI-compatible
(which covers Ollama and Gemini). See [BYOK docs](https://github.com/github/copilot-sdk/blob/main/docs/auth/byok.md).

### Phase 5: Update run_workload.py / run_sanity_matrix.py

Add new CLI flags:
```bash
python scripts/run_workload.py \
    --backend azure \                      # azure | ollama | copilot-sdk
    --model claude-sonnet-4.6 \            # model/deployment name
    --track standardized \                 # standardized | optimized | copilot
    --fhir-url https://localhost:8443 \
    --machine main_pc

# Qwen local:
python scripts/run_workload.py --backend ollama --model qwen3.5:9b --track standardized ...

# Pilot mode:
python scripts/run_workload.py --backend azure --model gpt-5.5-instant --pilot ...

# Token budget:
python scripts/run_workload.py --backend azure --model gemini-3-flash --token-budget-k 100 ...
```

Result filenames: `sanity-matrix-{test_case}-{backend}-{model}-{track}-{timestamp}.json`

### Phase 6: Pilot Run → Full Run

**Pilot set** (5 phenotypes, chosen for diversity):
1. `type-2-diabetes` — multi-path, multi-code, high expected counts
2. `crohns-disease` — negation test case, IBD specificity
3. `prostate-cancer` — sex-restricted, procedure + labs + dx
4. `peanut-allergy` — pediatric, epinephrine cross-indication
5. `warfarin-dose-response` — PGx, temporal logic

**Execution order**:
1. **6a**: Pilot — 5 phenotypes × 4 Azure models + local Qwen on Track S
2. **6b**: Full Track S — all 100 phenotypes × all models
3. **6c**: Track O and C runs

---

## Estimated Scope

Workhorse-tier pricing assumed: ~$3–5 input / ~$15–30 output per Mtok.

| Scope | Cells | Est. Cost |
|-------|-------|-----------|
| Pilot (Track S) | 5 × 3 × 9 × 4 = **540** | ~$10-25 |
| Full Track S (Azure, 3 cloud models) | 3 × 2,700 = **8,100** | ~$100-400 |
| Full Track S (Cloud Qwen) | **2,700** | ~$10-30 |
| Full Track S (Local Qwen) | **2,700** | $0 (compute only) |
| Track O + C | **~22,000** | ~$300-900 |

## Implementation Order

1. ~~Phase 0~~ ✅ DONE
2. **Phase 1a** — Azure provisioning (manual, no code changes)
3. **Phase 1b** — Normalized protocol + `AzureOpenAIAdapter` + refactored `OllamaAdapter` + conformance tests
4. **Phase 1c** — Model registry (`backend/src/llm/model_registry.py`)
5. **Phase 2** — Generic `AgenticProvider(adapter)` + `ClosedBookProvider(adapter)`
6. **Phase 3** — Timeout config + cost gates + tool response caching
7. **Phase 5** — CLI updates to `run_workload.py` and `run_sanity_matrix.py`
8. **Phase 6a** — Pilot run
9. **Phase 4** — Copilot SDK (Track C)
10. **Phase 6b** — Full Track S
11. **Phase 6c** — Track O + C

## Open Questions

1. **Azure region**: Choose a region where all Model Catalog models (Claude, Gemini,
   Qwen) are available as serverless endpoints. Check the
   [availability matrix](https://learn.microsoft.com/en-us/azure/ai-studio/how-to/deploy-models-serverless-availability).

2. **Azure OpenAI vs Foundry routing**: GPT models go through Azure OpenAI resource;
   third-party models go through Azure AI Foundry serverless API. Both are
   OpenAI-compatible but may have slightly different endpoint URL patterns. The
   `AzureOpenAIAdapter` must handle both.

3. **Qwen local vs cloud comparability**: Verify that Ollama Qwen and Azure Qwen
   produce similar enough results to be treated as the same model. If not, label
   them as separate entries in the results.

4. **Copilot SDK maturity**: The SDK is in "public preview." Running 2,700+ cells
   through it may surface stability issues. Plan for retries.

5. **Result storage**: Current flat JSON files in `results/`. May need a structured
   DB (SQLite or DuckDB) for cross-model comparison dashboards at scale.

6. **Tier mapping rationale (workhorse anchor)**: Sonnet 4.6 is the workhorse-tier
   anchor at $3/$15 per Mtok. Peers chosen by *positioning + pricing*, not by name
   suffix:
   - **GPT-5.5 standard** ($5/$30) benchmarks head-to-head against Opus 4.7
     (SWE-Bench Pro 58.6 vs 64.3; GPQA Diamond 93.6 vs 94.2; Terminal-Bench 2.0
     82.7 vs 69.4). That's a flagship match — **wrong tier for this eval**.
     **GPT-5.5 Instant** is the workhorse variant (ChatGPT default since
     2026-05-05) and the correct Sonnet 4.6 peer.
   - **Gemini 3 Pro** is the flagship; **Gemini 3 Flash** is the workhorse with
     pricing/positioning matching Sonnet.
   A flagship-tier follow-up run (Opus 4.7 / GPT-5.5 standard / Gemini 3 Pro)
   is plausible later but explicitly out of scope for the initial baseline.

7. **GPT-5.5 Instant API availability**: GPT-5.5 Instant launched 2026-05-05 as
   the ChatGPT default. Confirm it is exposed via Azure OpenAI as a deployable
   model name before locking the plan. If not, fall back options in order of
   preference: (a) wait for GA, (b) GPT-5.5 Thinking with `reasoning_effort=low`
   to approximate Instant, (c) prior workhorse-tier GPT (GPT-5.4 Instant or
   equivalent) — document the substitution in `RunMetadata`.

## Dependencies

```
pip install openai>=1.0          # AzureOpenAI client (already likely installed)
pip install github-copilot-sdk   # Track C only
# google-generativeai            # Track O only (native Gemini)
# anthropic                      # Track O only (native Claude) — already installed
```
