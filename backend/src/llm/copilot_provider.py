"""GitHub Copilot SDK as an LLM provider.

Fundamentally different paradigm from the OpenAI-compat / Ollama backends:
Copilot's session runs the agent loop INTERNALLY. We hand it tools + system
prompt + user prompt; it iterates with the model, executes any tool calls
against our @define_tool wrappers, and returns the final assistant message
once the loop is idle.

That means Copilot can't slot into the ChatBackend abstraction (which is a
single chat turn). The two providers here implement LLMProvider directly:

- CopilotProvider          -- Tier 1 closed-book; no tools registered
- CopilotAgenticProvider   -- Tier 2/3; 10 FHIR/UMLS/VSAC tools registered as
                              @define_tool wrappers around the existing
                              AgenticProvider._tool_* methods

Auth is GitHub Copilot subscription (gh auth login). Each call spawns a new
session via the CLI subprocess; the SDK installs the Copilot CLI on first use.

Requires ``pip install github-copilot-sdk`` (import name ``copilot``).
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from copilot import CopilotClient, define_tool
from copilot.generated.session_events import AssistantMessageData
from copilot.session import PermissionHandler, SystemMessageReplaceConfig

from .provider import (
    LLMProvider, FHIR_SYSTEM_PROMPT, build_generated_query,
    parse_fhir_query_from_text, parse_fhir_queries_from_text,
)

backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import GeneratedQuery, RunMetadata

logger = logging.getLogger(__name__)


# --- helpers ----------------------------------------------------------------

def _final_text(response) -> str:
    """Pull the assistant's final content out of a SessionEvent."""
    if response is None or not isinstance(response.data, AssistantMessageData):
        return ""
    return response.data.content or ""


def _output_tokens(response) -> int | None:
    """Pull output_tokens (may be a float in the SDK) out of a SessionEvent."""
    if response is None or not isinstance(response.data, AssistantMessageData):
        return None
    n = response.data.output_tokens
    return int(n) if n is not None else None


def _system_replace(text: str) -> SystemMessageReplaceConfig:
    """SystemMessageReplaceConfig is a TypedDict; build one inline."""
    return {"mode": "replace", "content": text}  # type: ignore[return-value]


# --- Tier 1 closed-book -----------------------------------------------------

class CopilotProvider(LLMProvider):
    """Closed-book FHIR query generation via a Copilot session with no tools."""

    def __init__(self, model: str = "claude-sonnet-4.6", timeout_sec: int = 180):
        self.model = model
        self.timeout_sec = timeout_sec

    def generate_fhir_query(self, prompt: str, context: str = "") -> GeneratedQuery:
        user_msg = prompt if not context else f"{context}\n\n{prompt}"

        async def _run() -> str:
            async with CopilotClient() as client:
                session = await client.create_session(
                    model=self.model,
                    on_permission_request=PermissionHandler.approve_all,
                    available_tools=[],  # drop Copilot's built-in tools
                    system_message=_system_replace(FHIR_SYSTEM_PROMPT),
                )
                resp = await session.send_and_wait(user_msg, timeout=self.timeout_sec)
                return _final_text(resp)

        text = asyncio.run(_run()).strip()
        if not text:
            raise RuntimeError("Copilot returned empty content")

        all_parsed = parse_fhir_queries_from_text(text)
        if all_parsed:
            parsed, additional = all_parsed[0], all_parsed[1:]
        else:
            parsed, additional = parse_fhir_query_from_text(text), []
        return GeneratedQuery(raw_response=text, parsed_query=parsed,
                              additional_queries=additional)


# --- Tier 2/3 agentic -------------------------------------------------------

# Pydantic param models for each tool (matches TOOL_DEFINITIONS in agentic_provider).
class _NoParams(BaseModel):
    pass


class _FhirSearchParams(BaseModel):
    query: str = Field(description=(
        "FHIR search query path, e.g. 'Condition?code=http://snomed.info/sct|44054006' "
        "or 'Patient?_summary=count'."
    ))


class _FhirResourceSampleParams(BaseModel):
    resource_type: str = Field(description="FHIR resource type to sample, e.g. 'Condition'.")
    count: int = Field(default=3, description="Number of resources to sample (default 3).")


class _UmlsSearchParams(BaseModel):
    term: str = Field(description="Clinical concept to search for.")
    search_type: str = Field(default="words", description="UMLS search type (default 'words').")


class _UmlsCrosswalkParams(BaseModel):
    source: str = Field(description="Source vocabulary, e.g. 'SNOMEDCT_US'.")
    code: str = Field(description="Code in the source vocabulary.")
    target_source: Optional[str] = Field(
        default=None, description="Optional target vocabulary; omit to crosswalk to all.")


class _VsacSearchParams(BaseModel):
    title: Optional[str] = Field(default=None, description="Title substring (case-insensitive).")
    code: Optional[str] = Field(default=None, description="Member code to find containing value sets.")


class _VsacExpandParams(BaseModel):
    oid: str = Field(description="Value set OID, e.g. '2.16.840.1.113883.3.464.1003.103.12.1001'.")
    filter: Optional[str] = Field(default=None, description="Optional substring filter on display.")


class _VsacValidateParams(BaseModel):
    oid: str = Field(description="Value set OID to validate against.")
    code: str = Field(description="Code to check for membership.")
    system: Optional[str] = Field(default=None, description="Optional code-system URI.")


class _VsacLookupParams(BaseModel):
    system: str = Field(description="FHIR code-system URI.")
    code: str = Field(description="Code to look up.")


class _VsacSubsumeParams(BaseModel):
    system: str = Field(description="FHIR code-system URI (e.g. 'http://snomed.info/sct').")
    code_a: str = Field(description="Putative ancestor code.")
    code_b: str = Field(description="Putative descendant code.")


def _short_descs() -> dict[str, str]:
    """One-line descriptions per tool; the full system prompt provides workflow context."""
    return {
        "fhir_server_metadata": "Get the FHIR server CapabilityStatement (resource types, search params, IGs).",
        "fhir_search": "Execute a FHIR search query. Returns total count, resource types, and sample codings.",
        "fhir_resource_sample": "Sample N resources of a given type to discover which code systems the server uses.",
        "umls_search": "Search UMLS for a clinical concept; returns CUI + matching codes across vocabularies.",
        "umls_crosswalk": "Map a code from one clinical vocabulary to others (e.g. SNOMED -> ICD-10).",
        "vsac_search_value_sets": "Search VSAC value sets by title substring or member code.",
        "vsac_expand_value_set": "Expand a VSAC value set to its full member-code list.",
        "vsac_validate_code": "Check whether a code is a member of a given VSAC value set.",
        "vsac_lookup_code": "Look up a code's display + properties in a FHIR code system.",
        "vsac_check_subsumption": "Check whether code_a subsumes code_b (parent/child relationship).",
    }


class CopilotAgenticProvider(LLMProvider):
    """Agentic Tier 2/3 via Copilot SDK with our 10 FHIR/UMLS/VSAC tools registered.

    Copilot's session runs the agent loop internally; we get back the final
    assistant message after all tool calls resolved.
    """

    def __init__(self, model: str = "claude-sonnet-4.6",
                 fhir_base_url: str = "http://localhost:8080/fhir",
                 tier: int = 2,
                 timeout_sec: int = 600,
                 lean_prompt: bool = False):
        self.model = model
        self.fhir_base_url = fhir_base_url
        self.tier = tier
        self.timeout_sec = timeout_sec
        self.lean_prompt = lean_prompt
        # Reuse AgenticProvider for its 10 _tool_* method implementations + the
        # built (tier-aware) system prompt. Pass a dummy backend; we never call
        # .chat() on it -- Copilot runs the loop.
        from .agentic_provider import (
            AgenticProvider, AGENTIC_SYSTEM_PROMPT, AGENTIC_SYSTEM_PROMPT_VERSION,
            LEAN_AGENTIC_SYSTEM_PROMPT, LEAN_AGENTIC_SYSTEM_PROMPT_VERSION,
            TOOL_SCHEMA_VERSION,
        )
        from .chat_backend import OllamaChatBackend
        prompt = LEAN_AGENTIC_SYSTEM_PROMPT if lean_prompt else AGENTIC_SYSTEM_PROMPT
        version = LEAN_AGENTIC_SYSTEM_PROMPT_VERSION if lean_prompt else AGENTIC_SYSTEM_PROMPT_VERSION
        self._tools_owner = AgenticProvider(
            chat_backend=OllamaChatBackend(model="unused"),  # never invoked
            fhir_base_url=fhir_base_url,
            tier=tier,
            agentic_prompt=prompt,
            agentic_prompt_version=version,
        )
        self._tool_schema_version = TOOL_SCHEMA_VERSION
        self._tool_call_counts: dict[str, int] = {}
        self.last_run_metadata: Optional[RunMetadata] = None

    def _build_tools(self) -> list:
        """Build @define_tool wrappers around the 10 AgenticProvider tool methods.

        Each wrapper increments a counter so we can report tool_calls_count in
        run metadata. Results are JSON-serialised since Copilot tools return strings.
        """
        owner = self._tools_owner
        counts = self._tool_call_counts
        descs = _short_descs()

        def _call(name: str, fn, **kwargs) -> str:
            counts[name] = counts.get(name, 0) + 1
            try:
                result = fn(**kwargs)
            except Exception as e:
                logger.warning("tool %s raised: %s", name, e)
                result = {"error": str(e)[:200]}
            return json.dumps(result) if not isinstance(result, str) else result

        @define_tool(description=descs["fhir_server_metadata"], skip_permission=True)
        def fhir_server_metadata(_: _NoParams) -> str:
            return _call("fhir_server_metadata", owner._tool_fhir_server_metadata)

        @define_tool(description=descs["fhir_search"], skip_permission=True)
        def fhir_search(p: _FhirSearchParams) -> str:
            return _call("fhir_search", owner._tool_fhir_search, query=p.query)

        @define_tool(description=descs["fhir_resource_sample"], skip_permission=True)
        def fhir_resource_sample(p: _FhirResourceSampleParams) -> str:
            return _call("fhir_resource_sample", owner._tool_fhir_resource_sample,
                         resource_type=p.resource_type, count=p.count)

        @define_tool(description=descs["umls_search"], skip_permission=True)
        def umls_search(p: _UmlsSearchParams) -> str:
            return _call("umls_search", owner._tool_umls_search,
                         term=p.term, search_type=p.search_type)

        @define_tool(description=descs["umls_crosswalk"], skip_permission=True)
        def umls_crosswalk(p: _UmlsCrosswalkParams) -> str:
            return _call("umls_crosswalk", owner._tool_umls_crosswalk,
                         source=p.source, code=p.code, target_source=p.target_source)

        @define_tool(description=descs["vsac_search_value_sets"], skip_permission=True)
        def vsac_search_value_sets(p: _VsacSearchParams) -> str:
            return _call("vsac_search_value_sets", owner._tool_vsac_search_value_sets,
                         title=p.title, code=p.code)

        @define_tool(description=descs["vsac_expand_value_set"], skip_permission=True)
        def vsac_expand_value_set(p: _VsacExpandParams) -> str:
            return _call("vsac_expand_value_set", owner._tool_vsac_expand_value_set,
                         oid=p.oid, filter=p.filter)

        @define_tool(description=descs["vsac_validate_code"], skip_permission=True)
        def vsac_validate_code(p: _VsacValidateParams) -> str:
            return _call("vsac_validate_code", owner._tool_vsac_validate_code,
                         oid=p.oid, code=p.code, system=p.system)

        @define_tool(description=descs["vsac_lookup_code"], skip_permission=True)
        def vsac_lookup_code(p: _VsacLookupParams) -> str:
            return _call("vsac_lookup_code", owner._tool_vsac_lookup_code,
                         system=p.system, code=p.code)

        @define_tool(description=descs["vsac_check_subsumption"], skip_permission=True)
        def vsac_check_subsumption(p: _VsacSubsumeParams) -> str:
            return _call("vsac_check_subsumption", owner._tool_vsac_check_subsumption,
                         system=p.system, code_a=p.code_a, code_b=p.code_b)

        return [
            fhir_server_metadata, fhir_search, fhir_resource_sample,
            umls_search, umls_crosswalk,
            vsac_search_value_sets, vsac_expand_value_set, vsac_validate_code,
            vsac_lookup_code, vsac_check_subsumption,
        ]

    def generate_fhir_query(self, prompt: str, context: str = "") -> GeneratedQuery:
        self._tool_call_counts = {}
        tools = self._build_tools()
        system_prompt = self._tools_owner._system_prompt  # already built (tier 3 prepends methodology)
        user_msg = prompt if not context else f"{context}\n\n{prompt}"

        t0 = time.time()
        out_tokens_holder = {"n": None}

        async def _run() -> str:
            async with CopilotClient() as client:
                session = await client.create_session(
                    model=self.model,
                    on_permission_request=PermissionHandler.approve_all,
                    available_tools=[],  # drop Copilot's built-ins
                    tools=tools,
                    system_message=_system_replace(system_prompt),
                )
                resp = await session.send_and_wait(user_msg, timeout=self.timeout_sec)
                out_tokens_holder["n"] = _output_tokens(resp)
                return _final_text(resp)

        text = asyncio.run(_run()).strip()
        elapsed = time.time() - t0

        tool_calls_count = sum(self._tool_call_counts.values())
        self.last_run_metadata = RunMetadata(
            provider_backend="copilot",
            model_version=self.model,
            tool_transport="copilot-sdk",
            tier=self.tier,
            system_prompt_version=self._tools_owner._agentic_prompt_version,
            tool_schema_version=self._tool_schema_version,
            elapsed_sec=round(elapsed, 2),
            stop_reason="complete" if text else "empty",
            tool_calls_count=tool_calls_count,
            output_tokens=out_tokens_holder["n"],
            fallback_used=False,
        )

        if not text:
            raise RuntimeError(
                f"Copilot returned empty content "
                f"(tools called: {tool_calls_count}, elapsed: {int(elapsed)}s)"
            )
        return build_generated_query(text)
