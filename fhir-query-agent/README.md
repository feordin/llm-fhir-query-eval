# FHIR Query Agent

AI-powered FHIR query generation from natural language. An agentic tool-use workflow that produces accurate FHIR REST API search queries by combining clinical terminology lookup with live server introspection.

## Why Not Just Ask an LLM?

When you ask a bare LLM to generate a FHIR query, it frequently:
- **Hallucinates clinical codes** (wrong LOINC, nonexistent RxNorm codes)
- **Uses the wrong code system** (ICD-10 when the server only has SNOMED)
- **Uses outdated resource names** (MedicationOrder instead of MedicationRequest)
- **Cannot verify** whether the query actually works

The FHIR Query Agent solves this by giving the LLM access to tools:

| Approach | Code Accuracy | Server Awareness | Self-Correction |
|----------|:---:|:---:|:---:|
| **Closed-book LLM** (Tier 1) | Low - guesses codes | None | None |
| **Agent with tools** (Tier 2) | High - looks up codes | Yes - samples data | Yes - tests queries |

In our evaluation framework, tool-assisted agents consistently outperform closed-book generation, especially for medications (where RxNorm ingredient vs. SCD codes matter) and labs (where specific LOINC codes are required).

## Quick Start

### Install

```bash
cd fhir-query-agent
pip install -e .
```

### Prerequisites

- **Ollama** running locally with a tool-calling model (e.g., `qwen2.5:7b`, `llama3.1:8b`)
- **FHIR server** with data (e.g., HAPI FHIR with Synthea data)
- **UMLS API key** (optional but recommended) from https://uts.nlm.nih.gov/uts/signup-login

### Run

```bash
# Interactive mode
fhir-query-agent --fhir-url http://localhost:8080/fhir --umls-key YOUR_KEY

# Single query
fhir-query-agent --fhir-url http://localhost:8080/fhir -q "Find patients with type 2 diabetes"

# JSON output (for scripting)
fhir-query-agent --fhir-url http://localhost:8080/fhir -q "Find diabetic patients" --json-output
```

### Environment Variables

Instead of CLI flags, you can set:

```bash
export FHIR_SERVER_URL=http://localhost:8080/fhir
export UMLS_API_KEY=your-key-here
export OLLAMA_HOST=http://localhost:11434  # if non-default
```

## How It Works

The agent runs a loop: **LLM reasons -> calls tools -> gets results -> reasons again** until it has a working query.

```
User: "Find all patients on metformin"
                    |
            +--------------+
            |   LLM Agent  |
            +--------------+
                    |
    1. umls_search("metformin")
       -> RxNorm 6809 (ingredient)
                    |
    2. fhir_resource_sample("MedicationRequest")
       -> Server uses RxNorm SCD codes (860975, etc.)
                    |
    3. fhir_search("MedicationRequest?code=...6809")
       -> 0 results! Ingredient code not in data.
                    |
    4. umls_crosswalk("RXNORM", "6809", "RXNORM")
       -> SCD code 860975 (metformin 500mg oral tablet)
                    |
    5. fhir_search("MedicationRequest?code=...860975")
       -> 47 results. Query works.
                    |
    Result: MedicationRequest?code=http://www.nlm.nih.gov/research/umls/rxnorm|860975
```

### Tools

| Tool | Purpose |
|------|---------|
| `umls_search` | Search UMLS for clinical concepts, get codes (SNOMED, LOINC, RxNorm, ICD-10) |
| `umls_crosswalk` | Map codes between systems (e.g., RxNorm ingredient to SCD) |
| `fhir_server_metadata` | Check server capabilities (supported resources, search parameters) |
| `fhir_resource_sample` | Sample resources to see what code systems are actually in the data |
| `fhir_search` | Test a FHIR query and get result counts |

## Architecture

```
fhir-query-agent/
├── src/fhir_query_agent/
│   ├── agent.py             # Core agent loop (model-agnostic)
│   ├── tools.py             # Tool definitions + implementations
│   ├── prompts.py           # System prompts
│   ├── cli.py               # CLI entry point
│   └── adapters/
│       ├── base.py              # LLM adapter interface
│       ├── ollama_adapter.py    # Ollama native tool calling
│       └── anthropic_adapter.py # Anthropic API (stub)
├── examples/
│   └── example_queries.md   # Example prompts and expected results
├── SKILL.md                 # Claude Code skill definition
└── pyproject.toml           # Package configuration
```

The agent loop is **model-agnostic**. The `LLMAdapter` interface abstracts away provider differences. Currently Ollama is fully implemented; Anthropic is a stub ready for contribution.

### Adding a New LLM Provider

Implement the `LLMAdapter` interface:

```python
from fhir_query_agent.adapters.base import LLMAdapter, AdapterResponse, ToolCall

class MyAdapter(LLMAdapter):
    def chat(self, messages, tools) -> AdapterResponse:
        # Call your LLM API
        # Parse tool calls from response
        return AdapterResponse(
            content="...",
            tool_calls=[ToolCall(name="...", arguments={...})],
            is_final=False,  # True when no more tool calls
        )
```

## Configuration

| Option | CLI Flag | Env Var | Default |
|--------|----------|---------|---------|
| FHIR server URL | `--fhir-url` | `FHIR_SERVER_URL` | (required) |
| LLM model | `--model` | - | `qwen2.5:7b` |
| Ollama host | `--ollama-host` | `OLLAMA_HOST` | `http://localhost:11434` |
| UMLS API key | `--umls-key` | `UMLS_API_KEY` | (optional) |
| Max iterations | `--max-iterations` | - | 10 |
| LLM provider | `--provider` | - | `ollama` |

## UMLS Without an API Key

The agent works without UMLS, but with reduced accuracy. Without UMLS, the agent relies on:
- `fhir_resource_sample` to discover codes already in the server
- The LLM's built-in knowledge of clinical codes (which may be wrong)

For best results, get a free UMLS API key from https://uts.nlm.nih.gov/uts/signup-login.

## Programmatic Use

```python
from fhir_query_agent import FHIRQueryAgent
from fhir_query_agent.adapters import OllamaAdapter

llm = OllamaAdapter(model="qwen2.5:7b")
agent = FHIRQueryAgent(
    llm_adapter=llm,
    fhir_base_url="http://localhost:8080/fhir",
    umls_api_key="your-key",
)

result = agent.generate_query("Find patients with type 2 diabetes on metformin")

print(result.queries)       # ['Condition?code=...', 'MedicationRequest?code=...']
print(result.iterations)    # 5
print(result.tool_trace)    # Full tool call history

agent.close()
```

## Part of the FHIR Query Evaluation Framework

This agent packages the best-performing workflow discovered through systematic evaluation of LLM FHIR query generation. See the parent project for evaluation results comparing closed-book (Tier 1) vs. tool-assisted (Tier 2) approaches.
