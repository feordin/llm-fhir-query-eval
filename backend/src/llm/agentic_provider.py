"""Agentic LLM provider that gives models tool access during FHIR query generation.

Uses Ollama's native tool calling API to let the LLM introspect the FHIR server,
look up clinical codes via UMLS, search VSAC value sets, check code subsumption,
and test queries before producing a final answer.
This is the Tier 2 evaluation mode.
"""

import asyncio
import base64
import json
import logging
import os
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional

import ollama

from .provider import LLMProvider, parse_fhir_query_from_text

import sys
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import GeneratedQuery

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Resource type corrections for common FHIR version mistakes
# ---------------------------------------------------------------------------

RESOURCE_TYPE_CORRECTIONS = {
    "MedicationOrder": "MedicationRequest",
    "MedicationStatement": "MedicationRequest",
}


# ---------------------------------------------------------------------------
# System prompt for the agentic loop
# ---------------------------------------------------------------------------

AGENTIC_SYSTEM_PROMPT = """\
You are a FHIR query expert with access to tools that let you inspect a live FHIR server and look up clinical codes via the NIH UMLS API.

Your goal: given a clinical data request in natural language, produce the most accurate FHIR REST API search query URL(s).

WORKFLOW - follow these steps:
1. Use `umls_search` to find the correct clinical codes (SNOMED CT, ICD-10, LOINC, RxNorm) for the concepts mentioned in the request.
2. If needed, use `umls_crosswalk` to map codes between systems (e.g., RxNorm ingredient to SCD, or SNOMED to ICD-10-CM).
3. Use `vsac_search_value_sets` to find curated value sets for the clinical concept (e.g., quality measure code lists for diabetes). Use `vsac_expand_value_set` to get all codes in a value set — this is more comprehensive than manual crosswalking.
4. Use `vsac_lookup_code` to verify individual codes using FHIR-native system URIs.
5. Use `vsac_check_subsumption` to check if a broader SNOMED code covers a narrower one, helping you choose the right code level.
6. Use `fhir_resource_sample` to inspect what code systems and codes are actually present on the server for the relevant resource type(s).
7. Construct a candidate FHIR query based on your findings.
8. Use `fhir_search` to test your candidate query and verify it returns results.
9. Refine if needed, then give your final answer.

RESPONSE FORMAT:
When you are done, respond with ONLY the FHIR query URL(s), one per line. Do NOT include the server base URL.
Format: ResourceType?parameter=value&parameter=value

Use proper code system URLs:
- LOINC: http://loinc.org|<code>
- SNOMED CT: http://snomed.info/sct|<code>
- ICD-10-CM: http://hl7.org/fhir/sid/icd-10-cm|<code>
- RxNorm: http://www.nlm.nih.gov/research/umls/rxnorm|<code>

Example final answer:
Condition?code=http://snomed.info/sct|44054006
"""


# ---------------------------------------------------------------------------
# Tool definitions in Ollama format
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "fhir_server_metadata",
            "description": (
                "Get the FHIR server's CapabilityStatement to understand what resource types, "
                "search parameters, and operations are supported."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fhir_search",
            "description": (
                "Execute a FHIR search query against the server and return results. "
                "Use this to test queries and see what data is available. "
                "Returns a summary: total count, resource types found, and sample codes from the first few entries."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "FHIR search query path, e.g. "
                            "'Condition?code=http://snomed.info/sct|44054006' or 'Patient?_summary=count'"
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fhir_resource_sample",
            "description": (
                "Get a sample of FHIR resources of a given type to inspect what code systems "
                "and codes are actually present in the server data. Returns up to 5 sample "
                "resources with their codes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_type": {
                        "type": "string",
                        "description": "FHIR resource type, e.g. 'Condition', 'MedicationRequest', 'Observation'",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of sample resources to return (max 5, default 3)",
                    },
                },
                "required": ["resource_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "umls_search",
            "description": (
                "Search the NIH UMLS (Unified Medical Language System) for a clinical concept. "
                "Returns matching concepts with their CUIs and codes across standard systems "
                "(SNOMED CT, ICD-10-CM, RxNorm, LOINC). Use this to find the correct clinical "
                "code for a disease, medication, or lab test."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "Clinical term to search for, e.g. 'type 2 diabetes', 'metformin', 'hemoglobin A1c'",
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Search type: 'exact' for precise matches, 'words' for broader word-based search. Default: 'words'",
                        "enum": ["exact", "words"],
                    },
                },
                "required": ["term"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "umls_crosswalk",
            "description": (
                "Map a clinical code from one system to another. For example, map an RxNorm "
                "ingredient code to SCD (specific drug formulation) codes, or map a SNOMED "
                "code to ICD-10-CM. This is essential for finding the exact code level that "
                "a FHIR server uses."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source vocabulary: SNOMEDCT_US, ICD10CM, RXNORM, LNC (for LOINC)",
                    },
                    "code": {
                        "type": "string",
                        "description": "Code in the source vocabulary",
                    },
                    "target_source": {
                        "type": "string",
                        "description": "Optional target vocabulary to filter results. Same vocabulary names as source.",
                    },
                },
                "required": ["source", "code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vsac_search_value_sets",
            "description": (
                "Search the VSAC (Value Set Authority Center) for curated value sets. "
                "Value sets are collections of medical codes from standard code systems "
                "(SNOMED CT, ICD-10, LOINC, RxNorm, etc.) maintained by organizations like "
                "NCQA and CMS for quality measures. Use this to find comprehensive, "
                "authoritative code lists — more complete than manual crosswalking."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Search value sets by title, e.g. 'Diabetes', 'Hypertension', 'HbA1c'",
                    },
                    "code": {
                        "type": "string",
                        "description": "Find value sets containing this specific code",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vsac_expand_value_set",
            "description": (
                "Expand a VSAC value set to get ALL its member codes. Returns every code "
                "(with code system, code value, and display name) in the value set. "
                "Use this after vsac_search_value_sets to get the complete code list."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "oid": {
                        "type": "string",
                        "description": "The value set OID from vsac_search_value_sets results",
                    },
                    "filter": {
                        "type": "string",
                        "description": "Optional text to filter codes within the expansion",
                    },
                },
                "required": ["oid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vsac_validate_code",
            "description": (
                "Check if a specific code is a member of a VSAC value set. "
                "Useful for verifying that a code qualifies for a quality measure "
                "or matches a profile's valueset binding."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "oid": {
                        "type": "string",
                        "description": "The value set OID to check against",
                    },
                    "code": {
                        "type": "string",
                        "description": "The code to validate",
                    },
                    "system": {
                        "type": "string",
                        "description": "Code system URI, e.g. 'http://snomed.info/sct'",
                    },
                },
                "required": ["oid", "code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vsac_lookup_code",
            "description": (
                "Look up details about a specific code using FHIR-native code system URIs. "
                "Returns the display name, properties, and designations. "
                "Uses FHIR URIs directly: 'http://snomed.info/sct', 'http://loinc.org', "
                "'http://hl7.org/fhir/sid/icd-10-cm', 'http://www.nlm.nih.gov/research/umls/rxnorm'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "system": {
                        "type": "string",
                        "description": "Code system URI",
                    },
                    "code": {
                        "type": "string",
                        "description": "The code to look up",
                    },
                },
                "required": ["system", "code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vsac_check_subsumption",
            "description": (
                "Check if one code subsumes (is an ancestor of) another in a hierarchical "
                "code system like SNOMED CT. Returns 'subsumes', 'subsumed-by', 'equivalent', "
                "or 'not-subsumed'. Use this to decide whether to query with a broad parent "
                "code or a specific child code. "
                "IMPORTANT: Use actual clinical codes (e.g., SNOMED numeric codes like '44054006'), "
                "NOT UMLS CUIs (which start with 'C'). CUIs like C0011860 will fail."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "system": {
                        "type": "string",
                        "description": "Code system URI, e.g. 'http://snomed.info/sct'",
                    },
                    "code_a": {
                        "type": "string",
                        "description": "The potential ancestor/broader code (e.g., SNOMED '73211009', NOT a CUI)",
                    },
                    "code_b": {
                        "type": "string",
                        "description": "The potential descendant/narrower code (e.g., SNOMED '44054006', NOT a CUI)",
                    },
                },
                "required": ["system", "code_a", "code_b"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Agentic provider
# ---------------------------------------------------------------------------

class OllamaAgenticProvider(LLMProvider):
    """LLM provider that gives the model access to tools during FHIR query generation.

    Implements a Tier 2 agentic evaluation loop:
      prompt -> tool calls -> refinement -> final FHIR query

    Tools available to the model:
      - fhir_server_metadata: inspect server capabilities
      - fhir_search: run a FHIR search and see summarised results
      - fhir_resource_sample: sample resources to discover codes on the server
      - umls_search: search UMLS for clinical concepts and their codes
      - umls_crosswalk: map codes between clinical vocabularies
      - vsac_search_value_sets: search VSAC for curated value sets
      - vsac_expand_value_set: get all codes in a value set
      - vsac_validate_code: check if a code belongs to a value set
      - vsac_lookup_code: look up code details using FHIR system URIs
      - vsac_check_subsumption: check parent/child code relationships
    """

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        fhir_base_url: str = "http://localhost:8080/fhir",
        max_iterations: int = 10,
        request_timeout: int = 30,
    ):
        self.model = model
        self.fhir_base_url = fhir_base_url.rstrip("/")
        self.max_iterations = max_iterations
        self.request_timeout = request_timeout
        self.tool_trace: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public interface (matches LLMProvider base class)
    # ------------------------------------------------------------------

    def generate_fhir_query(self, prompt: str, context: str = "") -> GeneratedQuery:
        """Run the agentic loop and return a GeneratedQuery."""
        self.tool_trace = []

        user_content = prompt
        if context:
            user_content = f"{context}\n\n{prompt}"

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": AGENTIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        tools = TOOL_DEFINITIONS

        for iteration in range(self.max_iterations):
            logger.debug("Agentic iteration %d/%d", iteration + 1, self.max_iterations)

            try:
                response = ollama.chat(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                )
            except Exception as e:
                raise RuntimeError(
                    f"Ollama chat failed (model={self.model}): {e}"
                ) from e

            msg = response["message"]
            messages.append(msg)

            # If no tool calls, the model is done -- extract the final query
            if not msg.get("tool_calls"):
                raw_text = msg.get("content", "")
                logger.debug("Model finished after %d iteration(s)", iteration + 1)
                parsed = parse_fhir_query_from_text(raw_text)
                return GeneratedQuery(raw_response=raw_text, parsed_query=parsed)

            # Execute each tool call and append tool-role messages
            for tool_call in msg["tool_calls"]:
                func_name = tool_call["function"]["name"]
                func_args = tool_call["function"].get("arguments", {})

                logger.debug("Tool call: %s(%s)", func_name, json.dumps(func_args)[:200])

                result = self._execute_tool(func_name, func_args)

                self.tool_trace.append({
                    "iteration": iteration,
                    "tool": func_name,
                    "args": func_args,
                    "result": result,
                })

                result_str = json.dumps(result) if not isinstance(result, str) else result
                messages.append({
                    "role": "tool",
                    "content": result_str,
                })

        # Max iterations exhausted -- try to extract a query from the last assistant message
        logger.warning("Max iterations (%d) reached without final answer", self.max_iterations)
        last_assistant = ""
        for m in reversed(messages):
            if m.get("role") == "assistant" and m.get("content"):
                last_assistant = m["content"]
                break

        parsed = parse_fhir_query_from_text(last_assistant)
        return GeneratedQuery(raw_response=last_assistant, parsed_query=parsed)

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """Dispatch a tool call to the appropriate handler."""
        handlers = {
            "fhir_server_metadata": self._tool_fhir_server_metadata,
            "fhir_search": self._tool_fhir_search,
            "fhir_resource_sample": self._tool_fhir_resource_sample,
            "umls_search": self._tool_umls_search,
            "umls_crosswalk": self._tool_umls_crosswalk,
            "vsac_search_value_sets": self._tool_vsac_search_value_sets,
            "vsac_expand_value_set": self._tool_vsac_expand_value_set,
            "vsac_validate_code": self._tool_vsac_validate_code,
            "vsac_lookup_code": self._tool_vsac_lookup_code,
            "vsac_check_subsumption": self._tool_vsac_check_subsumption,
        }
        handler = handlers.get(name)
        if handler is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            return handler(**args)
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # UMLS API key resolution
    # ------------------------------------------------------------------

    def _get_umls_api_key(self) -> str:
        """Get UMLS API key from environment or .mcp.json."""
        key = os.environ.get("UMLS_API_KEY")
        if key:
            return key
        # Try .mcp.json in the project root
        mcp_json = Path(__file__).parent.parent.parent.parent / ".mcp.json"
        if mcp_json.exists():
            try:
                with open(mcp_json) as f:
                    config = json.load(f)
                return (
                    config.get("mcpServers", {})
                    .get("nih-umls", {})
                    .get("env", {})
                    .get("UMLS_API_KEY", "")
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read .mcp.json for UMLS API key: %s", e)
        return ""

    # ------------------------------------------------------------------
    # Async helper
    # ------------------------------------------------------------------

    @staticmethod
    def _run_async(coro):
        """Run an async coroutine from synchronous code, handling existing event loops."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're inside an existing event loop (e.g. Jupyter, FastAPI background)
            # Create a new loop in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=60)
        else:
            return asyncio.run(coro)

    # ------------------------------------------------------------------
    # Tool implementations - FHIR server tools
    # ------------------------------------------------------------------

    def _tool_fhir_server_metadata(self) -> Dict[str, Any]:
        """Return a concise summary of the FHIR server CapabilityStatement."""
        url = f"{self.fhir_base_url}/metadata"
        resp = requests.get(url, headers={"Accept": "application/fhir+json"}, timeout=self.request_timeout)
        resp.raise_for_status()
        cap = resp.json()

        # Extract a concise summary instead of returning the full (huge) document
        resources_summary = []
        for rest in cap.get("rest", []):
            for resource in rest.get("resource", []):
                rtype = resource.get("type", "")
                search_params = [sp.get("name") for sp in resource.get("searchParam", [])]
                resources_summary.append({
                    "type": rtype,
                    "searchParams": search_params[:15],  # cap to keep it small
                })

        return {
            "fhirVersion": cap.get("fhirVersion", "unknown"),
            "status": cap.get("status", "unknown"),
            "resourceCount": len(resources_summary),
            "resources": resources_summary[:30],  # limit to 30 most common
        }

    def _tool_fhir_search(self, query: str) -> Dict[str, Any]:
        """Execute a FHIR search and return a concise summary of the Bundle."""
        # Strip leading slash if present
        query = query.lstrip("/")

        # Auto-correct common FHIR resource type mistakes
        for wrong, correct in RESOURCE_TYPE_CORRECTIONS.items():
            if query.startswith(wrong + "?") or query.startswith(wrong + "/") or query == wrong:
                logger.info("Auto-correcting resource type: %s -> %s", wrong, correct)
                query = correct + query[len(wrong):]
                break

        url = f"{self.fhir_base_url}/{query}"

        resp = requests.get(url, headers={"Accept": "application/fhir+json"}, timeout=self.request_timeout)
        if resp.status_code != 200:
            return {
                "error": f"HTTP {resp.status_code}",
                "detail": resp.text[:300],
            }

        bundle = resp.json()
        total = bundle.get("total", None)
        entries = bundle.get("entry", [])

        # Summarise entries
        resource_types_found: List[str] = []
        sample_codes: List[Dict[str, str]] = []

        for entry in entries[:5]:  # inspect first 5
            resource = entry.get("resource", {})
            rt = resource.get("resourceType", "")
            resource_types_found.append(rt)
            codes = self._extract_codes_from_resource(resource)
            if codes:
                sample_codes.extend(codes[:3])

        return {
            "total": total,
            "entriesReturned": len(entries),
            "resourceTypes": list(set(resource_types_found)),
            "sampleCodes": sample_codes[:10],
        }

    def _tool_fhir_resource_sample(self, resource_type: str, count: int = 3) -> Dict[str, Any]:
        """Get sample resources and extract their codes."""
        count = min(count or 3, 5)

        # Auto-correct common FHIR resource type mistakes
        corrected = RESOURCE_TYPE_CORRECTIONS.get(resource_type)
        if corrected:
            logger.info("Auto-correcting resource type: %s -> %s", resource_type, corrected)
            resource_type = corrected

        url = f"{self.fhir_base_url}/{resource_type}?_count={count}"

        resp = requests.get(url, headers={"Accept": "application/fhir+json"}, timeout=self.request_timeout)
        if resp.status_code != 200:
            return {
                "error": f"HTTP {resp.status_code}",
                "detail": resp.text[:300],
            }

        bundle = resp.json()
        total = bundle.get("total", None)
        entries = bundle.get("entry", [])

        samples = []
        for entry in entries[:count]:
            resource = entry.get("resource", {})
            rid = resource.get("id", "unknown")
            codes = self._extract_codes_from_resource(resource)
            samples.append({"id": rid, "codes": codes})

        return {
            "resourceType": resource_type,
            "totalOnServer": total,
            "samplesReturned": len(samples),
            "samples": samples,
        }

    # ------------------------------------------------------------------
    # Tool implementations - UMLS tools
    # ------------------------------------------------------------------

    def _tool_umls_search(self, term: str, search_type: str = "words") -> Dict[str, Any]:
        """Search UMLS for a clinical concept and return matching concepts with codes."""
        api_key = self._get_umls_api_key()
        if not api_key:
            return {
                "error": "UMLS API key not configured. Set UMLS_API_KEY env var or configure in .mcp.json.",
                "term": term,
            }

        async def _search():
            # Import here to avoid hard dependency at module level
            nih_umls_path = Path(__file__).parent.parent.parent.parent.parent / "nih-umls-mcp" / "src"
            if str(nih_umls_path) not in sys.path:
                sys.path.insert(0, str(nih_umls_path))
            from nih_umls_mcp.umls_client import UMLSClient

            async with UMLSClient(api_key) as client:
                result = await client.search(term, search_type=search_type)
                # Parse and return concise results
                concepts = []
                for item in result.get("result", {}).get("results", [])[:10]:
                    concepts.append({
                        "name": item.get("name", ""),
                        "cui": item.get("ui", ""),
                        "rootSource": item.get("rootSource", ""),
                    })
                return {"term": term, "results": concepts}

        try:
            return self._run_async(_search())
        except Exception as e:
            logger.error("UMLS search failed for term '%s': %s", term, e)
            return {"error": f"UMLS search failed: {str(e)}", "term": term}

    def _tool_umls_crosswalk(self, source: str, code: str, target_source: str = None) -> Dict[str, Any]:
        """Crosswalk a code between clinical vocabularies via UMLS."""
        api_key = self._get_umls_api_key()
        if not api_key:
            return {
                "error": "UMLS API key not configured. Set UMLS_API_KEY env var or configure in .mcp.json.",
                "source": source,
                "code": code,
            }

        async def _crosswalk():
            nih_umls_path = Path(__file__).parent.parent.parent.parent.parent / "nih-umls-mcp" / "src"
            if str(nih_umls_path) not in sys.path:
                sys.path.insert(0, str(nih_umls_path))
            from nih_umls_mcp.umls_client import UMLSClient

            async with UMLSClient(api_key) as client:
                result = await client.crosswalk(source, code, target_source=target_source)
                # Parse results
                mappings = []
                for item in result.get("result", [])[:15]:
                    mappings.append({
                        "source": item.get("rootSource", ""),
                        "code": item.get("ui", ""),
                        "name": item.get("name", ""),
                    })
                return {"source": source, "code": code, "mappings": mappings}

        try:
            return self._run_async(_crosswalk())
        except Exception as e:
            logger.error("UMLS crosswalk failed for %s/%s: %s", source, code, e)
            return {"error": f"UMLS crosswalk failed: {str(e)}", "source": source, "code": code}

    # ------------------------------------------------------------------
    # Tool implementations - VSAC tools
    # ------------------------------------------------------------------

    def _vsac_auth_header(self) -> Dict[str, str]:
        """Build auth headers for VSAC FHIR API requests."""
        api_key = self._get_umls_api_key()
        # VSAC uses Basic auth with apikey:<key>
        credentials = base64.b64encode(f"apikey:{api_key}".encode()).decode()
        return {
            "Accept": "application/fhir+json",
            "Authorization": f"Basic {credentials}",
        }

    def _tool_vsac_search_value_sets(self, title: str = None, code: str = None) -> Dict[str, Any]:
        """Search VSAC for curated value sets."""
        api_key = self._get_umls_api_key()
        if not api_key:
            return {"error": "UMLS API key not configured."}

        params: Dict[str, str] = {"_count": "10"}
        if title:
            params["title:contains"] = title
        if code:
            params["code"] = code

        try:
            resp = requests.get(
                "https://cts.nlm.nih.gov/fhir/ValueSet",
                params=params,
                headers=self._vsac_auth_header(),
                timeout=self.request_timeout,
            )
            resp.raise_for_status()
            bundle = resp.json()

            results = []
            for entry in bundle.get("entry", [])[:10]:
                vs = entry.get("resource", {})
                results.append({
                    "oid": vs.get("id", ""),
                    "title": vs.get("title", vs.get("name", "")),
                    "publisher": vs.get("publisher", ""),
                    "status": vs.get("status", ""),
                })

            return {"total": bundle.get("total"), "results": results}
        except Exception as e:
            logger.error("VSAC search failed: %s", e)
            return {"error": f"VSAC search failed: {str(e)}"}

    def _tool_vsac_expand_value_set(self, oid: str, filter: str = None) -> Dict[str, Any]:
        """Expand a VSAC value set to get all member codes."""
        api_key = self._get_umls_api_key()
        if not api_key:
            return {"error": "UMLS API key not configured."}

        params: Dict[str, str] = {"count": "100"}
        if filter:
            params["filter"] = filter

        try:
            resp = requests.get(
                f"https://cts.nlm.nih.gov/fhir/ValueSet/{oid}/$expand",
                params=params,
                headers=self._vsac_auth_header(),
                timeout=self.request_timeout,
            )
            resp.raise_for_status()
            vs = resp.json()

            codes = []
            expansion = vs.get("expansion", {})
            for item in expansion.get("contains", [])[:100]:
                codes.append({
                    "system": item.get("system", ""),
                    "code": item.get("code", ""),
                    "display": item.get("display", ""),
                })

            return {
                "oid": oid,
                "title": vs.get("title", vs.get("name", "")),
                "totalCodes": expansion.get("total", len(codes)),
                "codes": codes,
            }
        except Exception as e:
            logger.error("VSAC expand failed for %s: %s", oid, e)
            return {"error": f"VSAC expand failed: {str(e)}"}

    def _tool_vsac_validate_code(self, oid: str, code: str, system: str = None) -> Dict[str, Any]:
        """Check if a code is a member of a VSAC value set."""
        api_key = self._get_umls_api_key()
        if not api_key:
            return {"error": "UMLS API key not configured."}

        params: Dict[str, str] = {"code": code}
        if system:
            params["system"] = system

        try:
            resp = requests.get(
                f"https://cts.nlm.nih.gov/fhir/ValueSet/{oid}/$validate-code",
                params=params,
                headers=self._vsac_auth_header(),
                timeout=self.request_timeout,
            )
            resp.raise_for_status()
            result = resp.json()

            is_member = False
            display = ""
            for param in result.get("parameter", []):
                if param.get("name") == "result":
                    is_member = param.get("valueBoolean", False)
                elif param.get("name") == "display":
                    display = param.get("valueString", "")

            return {
                "oid": oid,
                "code": code,
                "system": system,
                "isMember": is_member,
                "display": display,
            }
        except Exception as e:
            logger.error("VSAC validate failed: %s", e)
            return {"error": f"VSAC validate failed: {str(e)}"}

    def _tool_vsac_lookup_code(self, system: str, code: str) -> Dict[str, Any]:
        """Look up a code using FHIR-native system URIs via VSAC."""
        api_key = self._get_umls_api_key()
        if not api_key:
            return {"error": "UMLS API key not configured."}

        try:
            resp = requests.get(
                "https://cts.nlm.nih.gov/fhir/CodeSystem/$lookup",
                params={"system": system, "code": code},
                headers=self._vsac_auth_header(),
                timeout=self.request_timeout,
            )
            resp.raise_for_status()
            result = resp.json()

            info: Dict[str, str] = {"system": system, "code": code}
            for param in result.get("parameter", []):
                name = param.get("name", "")
                if name == "display":
                    info["display"] = param.get("valueString", "")
                elif name == "name":
                    info["codeSystemName"] = param.get("valueString", "")
                elif name == "version":
                    info["version"] = param.get("valueString", "")

            return info
        except Exception as e:
            logger.error("VSAC lookup failed: %s", e)
            return {"error": f"VSAC lookup failed: {str(e)}"}

    def _tool_vsac_check_subsumption(self, system: str, code_a: str, code_b: str) -> Dict[str, Any]:
        """Check if code_a subsumes code_b in a hierarchical code system."""
        # Validate inputs - CUIs (C0123456) are not valid here
        for label, code in [("code_a", code_a), ("code_b", code_b)]:
            if code and code[0] == "C" and code[1:].isdigit():
                return {
                    "error": f"{label}='{code}' looks like a UMLS CUI, not a clinical code. "
                             f"Use the actual SNOMED numeric code (e.g., '44054006'), not the CUI. "
                             f"Use umls_search to find the SNOMED code for a CUI.",
                    "system": system,
                    "codeA": code_a,
                    "codeB": code_b,
                }

        api_key = self._get_umls_api_key()
        if not api_key:
            return {"error": "UMLS API key not configured."}

        try:
            resp = requests.get(
                "https://cts.nlm.nih.gov/fhir/CodeSystem/$subsumes",
                params={"system": system, "codeA": code_a, "codeB": code_b},
                headers=self._vsac_auth_header(),
                timeout=self.request_timeout,
            )
            resp.raise_for_status()
            result = resp.json()

            outcome = "unknown"
            for param in result.get("parameter", []):
                if param.get("name") == "outcome":
                    outcome = param.get("valueCode", "unknown")

            return {
                "system": system,
                "codeA": code_a,
                "codeB": code_b,
                "outcome": outcome,
            }
        except Exception as e:
            logger.error("VSAC subsumption check failed: %s", e)
            return {"error": f"VSAC subsumption check failed: {str(e)}"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_codes_from_resource(resource: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract coding information from a FHIR resource.

        Looks at common code-bearing fields: code, medicationCodeableConcept,
        category, type, and vaccineCode.
        """
        codes: List[Dict[str, str]] = []

        code_fields = [
            "code",
            "medicationCodeableConcept",
            "category",
            "type",
            "vaccineCode",
        ]

        for field_name in code_fields:
            field = resource.get(field_name)
            if not field:
                continue

            # Handle both single CodeableConcept and list of them
            concepts = field if isinstance(field, list) else [field]
            for concept in concepts:
                if not isinstance(concept, dict):
                    continue
                for coding in concept.get("coding", []):
                    codes.append({
                        "system": coding.get("system", ""),
                        "code": coding.get("code", ""),
                        "display": coding.get("display", ""),
                    })

        return codes
