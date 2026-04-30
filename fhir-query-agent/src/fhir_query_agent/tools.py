"""Tool definitions and implementations for the FHIR Query Agent.

Each tool has:
- A definition (JSON schema for the LLM to understand how to call it)
- An implementation (Python function that executes the tool call)

Tools are designed to return CONCISE results. Large JSON responses will blow
up the LLM context window, so we summarize and truncate aggressively.
"""

import asyncio
import json
import logging
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# Common FHIR R4 resource type corrections
RESOURCE_TYPE_CORRECTIONS = {
    "medicationorder": "MedicationRequest",
    "medicationprescription": "MedicationRequest",
    "medicationstatement": "MedicationStatement",
    "diagnosticorder": "ServiceRequest",
    "procedurerequest": "ServiceRequest",
    "referralrequest": "ServiceRequest",
    "deviceusestatement": "DeviceUseStatement",
}

# Code system URI mappings (short name -> full URI)
CODE_SYSTEM_URIS = {
    "SNOMEDCT_US": "http://snomed.info/sct",
    "SNOMEDCT": "http://snomed.info/sct",
    "LNC": "http://loinc.org",
    "LOINC": "http://loinc.org",
    "RXNORM": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "ICD10CM": "http://hl7.org/fhir/sid/icd-10-cm",
    "ICD10PCS": "http://www.cms.gov/Medicare/Coding/ICD10",
    "ICD9CM": "http://hl7.org/fhir/sid/icd-9-cm",
    "CPT": "http://www.ama-assn.org/go/cpt",
    "CVX": "http://hl7.org/fhir/sid/cvx",
    "HCPCS": "http://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets",
}

# UMLS source abbreviations used by the API
FHIR_TO_UMLS_SOURCE = {
    "http://snomed.info/sct": "SNOMEDCT_US",
    "http://loinc.org": "LNC",
    "http://www.nlm.nih.gov/research/umls/rxnorm": "RXNORM",
    "http://hl7.org/fhir/sid/icd-10-cm": "ICD10CM",
}


def _correct_resource_type(resource_type: str) -> str:
    """Auto-correct common resource type mistakes to FHIR R4 names."""
    corrected = RESOURCE_TYPE_CORRECTIONS.get(resource_type.lower())
    if corrected:
        return corrected
    return resource_type


class FHIRQueryTools:
    """Tools available to the FHIR Query Agent.

    Provides both tool definitions (for the LLM) and implementations
    (for execution). Tools cover UMLS terminology lookup and FHIR
    server interaction.
    """

    def __init__(self, fhir_base_url: str, umls_api_key: Optional[str] = None):
        """Initialize tools with server connections.

        Args:
            fhir_base_url: Base URL of the FHIR server (e.g., http://localhost:8080/fhir).
            umls_api_key: NIH UMLS API key for terminology lookups. Optional;
                UMLS tools will return a helpful error if not configured.
        """
        self.fhir_base_url = fhir_base_url.rstrip("/")
        self.umls_api_key = umls_api_key
        self._umls_client = None
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/fhir+json"})

    def _get_umls_client(self):
        """Lazily initialize the UMLS client."""
        if self._umls_client is None:
            if not self.umls_api_key:
                return None
            try:
                from nih_umls_mcp.umls_client import UMLSClient
                self._umls_client = UMLSClient(api_key=self.umls_api_key)
            except ImportError:
                logger.warning(
                    "nih-umls-mcp package not installed. UMLS tools unavailable."
                )
                return None
        return self._umls_client

    def _run_async(self, coro):
        """Run an async coroutine synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, coro).result(timeout=30)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    def get_tool_definitions(self) -> list[dict]:
        """Return tool definitions in Ollama/OpenAI function calling format.

        These definitions tell the LLM what tools are available, what
        parameters they accept, and what they do.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "umls_search",
                    "description": (
                        "Search UMLS for clinical concepts. Returns concept names, "
                        "CUIs, and source codes (SNOMED, LOINC, RxNorm, ICD-10, etc.). "
                        "Use this to find the right clinical codes for a concept."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "term": {
                                "type": "string",
                                "description": (
                                    "Clinical term to search for "
                                    "(e.g., 'type 2 diabetes', 'metformin', 'hemoglobin A1c')"
                                ),
                            },
                            "search_type": {
                                "type": "string",
                                "enum": ["words", "exact", "approximate"],
                                "description": (
                                    "Search strategy. 'words' (default) matches any word. "
                                    "'exact' requires exact match. 'approximate' is fuzzy."
                                ),
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
                        "Map a code from one system to another (e.g., SNOMED -> ICD-10, "
                        "RxNorm ingredient -> RxNorm SCD). Use when the server uses a "
                        "different code system than what you found."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source": {
                                "type": "string",
                                "description": (
                                    "Source vocabulary: SNOMEDCT_US, RXNORM, ICD10CM, LNC"
                                ),
                            },
                            "code": {
                                "type": "string",
                                "description": "Code in the source vocabulary",
                            },
                            "target_source": {
                                "type": "string",
                                "description": (
                                    "Target vocabulary to map to (optional). "
                                    "If omitted, returns all mappings."
                                ),
                            },
                        },
                        "required": ["source", "code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fhir_server_metadata",
                    "description": (
                        "Get the FHIR server's CapabilityStatement. Returns supported "
                        "resource types, search parameters, and FHIR version. "
                        "Use this to check what the server supports."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fhir_resource_sample",
                    "description": (
                        "Fetch a small sample of resources from the FHIR server. "
                        "Use this to see what code systems and codes are actually in the "
                        "data before constructing queries. CRITICAL: always sample before "
                        "assuming which code system to use."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "resource_type": {
                                "type": "string",
                                "description": (
                                    "FHIR resource type (e.g., Condition, Observation, "
                                    "MedicationRequest, Patient)"
                                ),
                            },
                            "count": {
                                "type": "integer",
                                "description": "Number of resources to sample (1-5, default 3)",
                            },
                        },
                        "required": ["resource_type"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fhir_search",
                    "description": (
                        "Execute a FHIR search query and return results. Use this to "
                        "test your constructed query before finalizing it. Returns the "
                        "count and a summary of matching resources."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": (
                                    "FHIR search query as a relative URL "
                                    "(e.g., 'Condition?code=http://snomed.info/sct|44054006')"
                                ),
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
        ]

    def execute(self, tool_name: str, args: dict) -> dict:
        """Execute a tool call and return results.

        Args:
            tool_name: Name of the tool to execute.
            args: Arguments for the tool.

        Returns:
            Dict with tool results. Always includes a "status" key
            ("success" or "error") and tool-specific data.
        """
        dispatch = {
            "umls_search": self.umls_search,
            "umls_crosswalk": self.umls_crosswalk,
            "fhir_server_metadata": self.fhir_server_metadata,
            "fhir_search": self.fhir_search,
            "fhir_resource_sample": self.fhir_resource_sample,
        }

        handler = dispatch.get(tool_name)
        if not handler:
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}

        try:
            return handler(**args)
        except Exception as e:
            logger.exception(f"Tool {tool_name} failed")
            return {"status": "error", "message": f"{tool_name} failed: {str(e)}"}

    # -------------------------------------------------------------------------
    # UMLS Tools
    # -------------------------------------------------------------------------

    def umls_search(self, term: str, search_type: str = "words") -> dict:
        """Search UMLS for clinical concepts and return codes.

        Args:
            term: Clinical term to search for.
            search_type: Search strategy (words, exact, approximate).

        Returns:
            Dict with matching concepts and their codes across systems.
        """
        client = self._get_umls_client()
        if client is None:
            return {
                "status": "error",
                "message": (
                    "UMLS not available. Set --umls-key or install nih-umls-mcp. "
                    "You can still use fhir_resource_sample to find codes in the data."
                ),
            }

        try:
            result = self._run_async(
                client.search(query=term, search_type=search_type, page_size=10)
            )
        except Exception as e:
            return {"status": "error", "message": f"UMLS search failed: {str(e)}"}

        # Extract and summarize results concisely
        concepts = []
        results = result.get("result", {}).get("results", [])

        for r in results[:8]:  # Limit to top 8
            concept = {
                "name": r.get("name", ""),
                "cui": r.get("ui", ""),
                "source": r.get("rootSource", ""),
            }
            concepts.append(concept)

        if not concepts:
            return {
                "status": "success",
                "message": f"No results found for '{term}'",
                "concepts": [],
            }

        # For the top concepts, try to get source-specific codes
        enriched = []
        for c in concepts[:5]:  # Enrich top 5 with atoms
            cui = c["cui"]
            try:
                atoms_result = self._run_async(
                    client.get_atoms(cui, page_size=25)
                )
                codes_by_source = {}
                for atom in atoms_result.get("result", []):
                    src = atom.get("rootSource", "")
                    code = atom.get("sourceUi", "") if isinstance(atom, dict) else ""
                    name = atom.get("name", "")
                    tty = atom.get("termType", "")
                    if src in ("SNOMEDCT_US", "LNC", "RXNORM", "ICD10CM", "ICD9CM", "CPT"):
                        if src not in codes_by_source:
                            codes_by_source[src] = []
                        if len(codes_by_source[src]) < 3:  # Max 3 per source
                            entry = {"code": code, "display": name}
                            if tty:
                                entry["type"] = tty
                            codes_by_source[src].append(entry)

                c["codes"] = codes_by_source
            except Exception:
                pass  # Skip enrichment on error
            enriched.append(c)

        return {"status": "success", "concepts": enriched}

    def umls_crosswalk(
        self, source: str, code: str, target_source: str = None
    ) -> dict:
        """Map a code from one vocabulary to another.

        Args:
            source: Source vocabulary (e.g., SNOMEDCT_US, RXNORM, ICD10CM).
            code: Code in the source vocabulary.
            target_source: Target vocabulary (optional).

        Returns:
            Dict with mapped codes.
        """
        client = self._get_umls_client()
        if client is None:
            return {
                "status": "error",
                "message": "UMLS not available. Set --umls-key or install nih-umls-mcp.",
            }

        try:
            result = self._run_async(
                client.crosswalk(
                    source=source,
                    source_id=code,
                    target_source=target_source,
                    page_size=25,
                )
            )
        except Exception as e:
            return {"status": "error", "message": f"UMLS crosswalk failed: {str(e)}"}

        # Summarize results concisely
        mappings = []
        results = result.get("result", [])

        for r in results[:15]:  # Limit results
            if isinstance(r, dict):
                mapping = {
                    "source": r.get("rootSource", ""),
                    "code": r.get("ui", ""),
                    "name": r.get("name", ""),
                }
                # Add FHIR system URI if known
                fhir_system = CODE_SYSTEM_URIS.get(mapping["source"])
                if fhir_system:
                    mapping["fhir_system"] = fhir_system
                mappings.append(mapping)

        if not mappings:
            return {
                "status": "success",
                "message": f"No crosswalk results for {source}/{code}",
                "mappings": [],
            }

        return {"status": "success", "mappings": mappings}

    # -------------------------------------------------------------------------
    # FHIR Server Tools
    # -------------------------------------------------------------------------

    def fhir_server_metadata(self) -> dict:
        """Get summarized FHIR server CapabilityStatement.

        Returns:
            Dict with FHIR version, supported resources, and search parameters.
        """
        try:
            resp = self._session.get(
                f"{self.fhir_base_url}/metadata", timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return {"status": "error", "message": f"Failed to reach FHIR server: {e}"}

        # Summarize - don't dump the entire CapabilityStatement
        fhir_version = data.get("fhirVersion", "unknown")
        software = data.get("software", {}).get("name", "unknown")

        resources = []
        for rest in data.get("rest", []):
            for res in rest.get("resource", []):
                res_info = {
                    "type": res.get("type", ""),
                    "search_params": [
                        p.get("name") for p in res.get("searchParam", [])
                    ],
                }
                profiles = res.get("supportedProfile", [])
                if profiles:
                    res_info["profiles"] = profiles[:3]  # Limit
                resources.append(res_info)

        return {
            "status": "success",
            "fhir_version": fhir_version,
            "software": software,
            "resource_count": len(resources),
            "resources": resources[:30],  # Limit to 30 resource types
        }

    def fhir_resource_sample(self, resource_type: str, count: int = 3) -> dict:
        """Fetch a sample of resources to inspect code systems in use.

        Args:
            resource_type: FHIR resource type (e.g., Condition, Observation).
            count: Number of resources to sample (1-5).

        Returns:
            Dict with summarized resource data showing code systems and codes.
        """
        resource_type = _correct_resource_type(resource_type)
        count = min(max(count, 1), 5)

        try:
            resp = self._session.get(
                f"{self.fhir_base_url}/{resource_type}",
                params={"_count": count},
                timeout=15,
            )
            resp.raise_for_status()
            bundle = resp.json()
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Failed to fetch {resource_type}: {e}",
            }

        entries = bundle.get("entry", [])
        total = bundle.get("total", len(entries))

        samples = []
        for entry in entries:
            resource = entry.get("resource", {})
            sample = self._summarize_resource(resource)
            samples.append(sample)

        return {
            "status": "success",
            "resource_type": resource_type,
            "total_on_server": total,
            "samples": samples,
        }

    def fhir_search(self, query: str) -> dict:
        """Execute a FHIR search query and return summarized results.

        Args:
            query: Relative FHIR search URL (e.g., "Condition?code=http://snomed.info/sct|44054006").

        Returns:
            Dict with result count and summarized matches.
        """
        # Clean up the query
        query = query.lstrip("/")
        if query.startswith("http"):
            # Strip any accidental full URL
            parts = query.split("/", 3)
            if len(parts) > 3:
                query = parts[3]

        try:
            resp = self._session.get(
                f"{self.fhir_base_url}/{query}", timeout=15
            )
            resp.raise_for_status()
            bundle = resp.json()
        except requests.RequestException as e:
            return {"status": "error", "message": f"FHIR search failed: {e}"}

        entries = bundle.get("entry", [])
        total = bundle.get("total", len(entries))

        # Summarize first few results
        summaries = []
        for entry in entries[:5]:
            resource = entry.get("resource", {})
            summaries.append(self._summarize_resource(resource))

        return {
            "status": "success",
            "query": query,
            "total": total,
            "returned": len(entries),
            "results": summaries,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _summarize_resource(self, resource: dict) -> dict:
        """Create a concise summary of a FHIR resource.

        Extracts the most useful fields (codes, references, dates) without
        dumping the entire resource JSON.
        """
        resource_type = resource.get("resourceType", "Unknown")
        summary: dict[str, Any] = {
            "resourceType": resource_type,
            "id": resource.get("id", ""),
        }

        # Extract codes from common code fields
        for field in ("code", "medicationCodeableConcept", "vaccineCode", "type"):
            if field in resource:
                cc = resource[field]
                if isinstance(cc, dict) and "coding" in cc:
                    summary["codes"] = [
                        {
                            "system": c.get("system", ""),
                            "code": c.get("code", ""),
                            "display": c.get("display", ""),
                        }
                        for c in cc["coding"][:3]
                    ]
                    break

        # Extract category
        if "category" in resource:
            cats = resource["category"]
            if isinstance(cats, list) and cats:
                cat = cats[0]
                if isinstance(cat, dict) and "coding" in cat:
                    summary["category"] = [
                        c.get("code", "") for c in cat["coding"][:2]
                    ]

        # Extract value for Observations
        for vfield in ("valueQuantity", "valueCodeableConcept", "valueString"):
            if vfield in resource:
                val = resource[vfield]
                if vfield == "valueQuantity":
                    summary["value"] = f"{val.get('value', '')} {val.get('unit', '')}"
                elif vfield == "valueCodeableConcept" and "coding" in val:
                    summary["value"] = val["coding"][0].get("display", "")
                else:
                    summary["value"] = str(val)[:100]
                break

        # Extract subject reference
        if "subject" in resource:
            ref = resource["subject"]
            if isinstance(ref, dict):
                summary["subject"] = ref.get("reference", "")

        # Extract date fields
        for dfield in (
            "onsetDateTime",
            "recordedDate",
            "effectiveDateTime",
            "authoredOn",
            "issued",
        ):
            if dfield in resource:
                summary["date"] = resource[dfield][:10]  # Just the date part
                break

        # Extract medication reference (for MedicationRequest)
        if "medicationReference" in resource:
            ref = resource["medicationReference"]
            if isinstance(ref, dict):
                summary["medication_ref"] = ref.get("reference", "")
                if ref.get("display"):
                    summary["medication_display"] = ref["display"]

        return summary

    def close(self):
        """Clean up resources."""
        self._session.close()
        if self._umls_client:
            try:
                self._run_async(self._umls_client.close())
            except Exception:
                pass
