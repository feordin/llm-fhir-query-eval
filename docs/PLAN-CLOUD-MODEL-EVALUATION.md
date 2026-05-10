# Plan: Cloud Frontier Model Evaluation

> **Status**: Phase 0 complete (committed `7d56661c`). Phase 1a (Azure provisioning) is next.
>
> **Created**: 2026-05-05 | **Updated**: 2026-05-09

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

**Scale**: ~100 phenotypes × ~3 test cases × 9 cells = ~2,700 cells per model × 7+ models.

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

| Model | Azure Deployment | Track S (Azure) | Track S (Local) | Track O | Track C |
|-------|-----------------|-----------------|-----------------|---------|---------|
| Claude Sonnet 4 | Serverless API | ✅ | — | ✅ (native Anthropic SDK) | ✅ |
| Claude Opus 4 | Serverless API | ✅ | — | ✅ (native Anthropic SDK) | ✅ |
| GPT-4.1 | Azure OpenAI | ✅ | — | ✅ (native OpenAI SDK) | ✅ |
| GPT-5.2 | Azure OpenAI | ✅ | — | ✅ (native OpenAI SDK) | ✅ |
| Gemini 2.5 Pro | Serverless API | ✅ | — | ✅ (native Google SDK) | ✅ |
| Gemini 2.5 Flash | Serverless API | ✅ | — | ✅ (native Google SDK) | ✅ |
| Qwen3-8B | Serverless API | ✅ | ✅ (Ollama) | — | ✅ |

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
│   ├── gpt-4.1 deployment
│   └── gpt-5.2 deployment (or latest available)
├── Serverless API deployments (Model Catalog — pay-per-token)
│   ├── Claude Sonnet 4          (Anthropic via Azure)
│   ├── Claude Opus 4            (Anthropic via Azure)
│   ├── Gemini 2.5 Pro           (Google via Azure)
│   ├── Gemini 2.5 Flash         (Google via Azure)
│   └── Qwen3-8B                 (Alibaba via Azure)
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

**Action**: Manual Azure Portal / CLI provisioning. Check [Azure AI Foundry model catalog](https://ai.azure.com/explore/models) for regional availability of all target models.

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
    "claude-sonnet-4":  {"deployment": "claude-sonnet-4",  "provider": "anthropic", "tier": "frontier"},
    "claude-opus-4":    {"deployment": "claude-opus-4",    "provider": "anthropic", "tier": "frontier"},
    "gpt-4.1":          {"deployment": "gpt-4.1",          "provider": "openai",    "tier": "frontier"},
    "gpt-5.2":          {"deployment": "gpt-5.2",          "provider": "openai",    "tier": "frontier"},
    "gemini-2.5-pro":   {"deployment": "gemini-2.5-pro",   "provider": "google",    "tier": "frontier"},
    "gemini-2.5-flash": {"deployment": "gemini-2.5-flash", "provider": "google",    "tier": "frontier"},
    "qwen3-8b":         {"deployment": "qwen3-8b",         "provider": "alibaba",   "tier": "small",
                          "local_fallback": "qwen3:8b"},
}

LOCAL_MODELS = {
    "qwen3:8b": {"backend": "ollama", "tier": "small"},
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
    --model claude-sonnet-4 \              # model/deployment name
    --track standardized \                 # standardized | optimized | copilot
    --fhir-url https://localhost:8443 \
    --machine main_pc

# Qwen local:
python scripts/run_workload.py --backend ollama --model qwen3:8b --track standardized ...

# Pilot mode:
python scripts/run_workload.py --backend azure --model gpt-4.1 --pilot ...

# Token budget:
python scripts/run_workload.py --backend azure --model claude-opus-4 --token-budget-k 100 ...
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
1. **6a**: Pilot — 5 phenotypes × all 7 Azure models + local Qwen on Track S
2. **6b**: Full Track S — all 100 phenotypes × all models
3. **6c**: Track O and C runs

---

## Estimated Scope

| Scope | Cells | Est. Cost |
|-------|-------|-----------|
| Pilot (Track S) | 5 × 3 × 9 × 8 = **1,080** | ~$20-50 |
| Full Track S (Azure) | 7 × 2,700 = **18,900** | ~$200-800 |
| Full Track S (Local Qwen) | **2,700** | $0 (compute only) |
| Track O + C | **~40,000** | ~$500-1,500 |

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

## Dependencies

```
pip install openai>=1.0          # AzureOpenAI client (already likely installed)
pip install github-copilot-sdk   # Track C only
# google-generativeai            # Track O only (native Gemini)
# anthropic                      # Track O only (native Claude) — already installed
```
