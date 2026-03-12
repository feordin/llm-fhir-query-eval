import re
from abc import ABC, abstractmethod
from urllib.parse import urlparse, parse_qs
from typing import Optional

# Import from project - use relative imports within backend package
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import ParsedQuery, GeneratedQuery


FHIR_SYSTEM_PROMPT = """You are a FHIR query expert. Given a clinical data request in natural language, generate the appropriate FHIR REST API query URL(s).

Rules:
- Return FHIR query URLs, one per line
- Format: ResourceType?parameter=value&parameter=value
- Use proper code system URLs (e.g., http://loinc.org|code, http://snomed.info/sct|code, http://hl7.org/fhir/sid/icd-10-cm|code)
- Do not include the server base URL
- Use standard FHIR search parameters
- If the request requires searching multiple resource types, return multiple queries (one per line)
- For cross-resource searches, you may use _has, _include, _revinclude, or chained parameters

Example single query:
Condition?code=http://snomed.info/sct|73211009

Example multi-query response:
Condition?code=http://snomed.info/sct|44054006
MedicationRequest?code=http://www.nlm.nih.gov/research/umls/rxnorm|860975
Observation?code=http://loinc.org|4548-4&value-quantity=ge6.5||%25
"""


class LLMProvider(ABC):
    @abstractmethod
    def generate_fhir_query(self, prompt: str, context: str = "") -> GeneratedQuery:
        pass


def parse_fhir_query_from_text(text: str) -> ParsedQuery:
    """Extract a FHIR query URL from LLM response text and parse it into components.

    Handles various formats the LLM might return:
    - Condition?code=http://loinc.org|2339-0
    - GET /Condition?code=...
    - /r4/Condition?code=...
    - http://localhost:5826/r4/Condition?code=...
    - Wrapped in markdown code blocks
    """
    # Strip markdown code blocks
    cleaned = re.sub(r'```[a-z]*\n?', '', text).strip()
    cleaned = cleaned.strip('`').strip()

    # Known FHIR resource types to search for
    resource_types = [
        'Patient', 'Observation', 'Condition', 'MedicationRequest',
        'MedicationStatement', 'Procedure', 'Encounter', 'DiagnosticReport',
        'AllergyIntolerance', 'Immunization', 'CarePlan', 'Goal',
        'MedicationAdministration', 'ServiceRequest', 'DocumentReference'
    ]

    # Build regex: find ResourceType?params pattern
    rt_pattern = '|'.join(resource_types)
    # Match optional prefixes like GET, /r4/, http://.../ then ResourceType?params
    pattern = rf'(?:GET\s+)?(?:https?://[^\s/]*/)?(?:r[0-9]+/)?({rt_pattern})\?([^\s\n`"\']+)'

    match = re.search(pattern, cleaned)
    if match:
        resource_type = match.group(1)
        query_string = match.group(2)
        url = f"{resource_type}?{query_string}"

        # Parse parameters - use simple split since FHIR URLs have special chars
        params = {}
        for part in query_string.split('&'):
            if '=' in part:
                key, value = part.split('=', 1)
                params[key] = value

        return ParsedQuery(resource_type=resource_type, parameters=params, url=url)

    # Fallback: try to find just ResourceType? anywhere
    fallback = re.search(rf'({rt_pattern})\?(\S+)', cleaned)
    if fallback:
        resource_type = fallback.group(1)
        query_string = fallback.group(2).rstrip('.,;')
        url = f"{resource_type}?{query_string}"
        params = {}
        for part in query_string.split('&'):
            if '=' in part:
                key, value = part.split('=', 1)
                params[key] = value
        return ParsedQuery(resource_type=resource_type, parameters=params, url=url)

    # Nothing found - return raw text as-is
    raise ValueError(f"Could not parse FHIR query from LLM response: {text[:200]}")


def parse_fhir_queries_from_text(text: str) -> list[ParsedQuery]:
    """Extract ALL FHIR query URLs from LLM response text.

    Returns a list of ParsedQuery objects. Handles multi-line responses
    where the LLM returns multiple queries (one per line).
    """
    # Strip markdown code blocks
    cleaned = re.sub(r'```[a-z]*\n?', '', text).strip()
    cleaned = cleaned.strip('`').strip()

    resource_types = [
        'Patient', 'Observation', 'Condition', 'MedicationRequest',
        'MedicationStatement', 'Procedure', 'Encounter', 'DiagnosticReport',
        'AllergyIntolerance', 'Immunization', 'CarePlan', 'Goal',
        'MedicationAdministration', 'ServiceRequest', 'DocumentReference'
    ]
    rt_pattern = '|'.join(resource_types)
    pattern = rf'(?:GET\s+)?(?:https?://[^\s/]*/)?(?:r[0-9]+/)?(?:fhir/)?({rt_pattern})\?([^\s\n`"\']+)'

    queries = []
    seen_urls = set()
    for match in re.finditer(pattern, cleaned):
        resource_type = match.group(1)
        query_string = match.group(2).rstrip('.,;)')
        url = f"{resource_type}?{query_string}"

        if url in seen_urls:
            continue
        seen_urls.add(url)

        params = {}
        for part in query_string.split('&'):
            if '=' in part:
                key, value = part.split('=', 1)
                params[key] = value

        queries.append(ParsedQuery(resource_type=resource_type, parameters=params, url=url))

    return queries
