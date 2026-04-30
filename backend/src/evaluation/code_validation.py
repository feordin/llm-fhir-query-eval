"""Code system validation for FHIR queries.

Compares the (system, code) pairs in generated queries against the test case's
``metadata.required_codes`` to detect:
  - Wrong code system URIs (e.g., using ``RxNorm`` instead of
    ``http://www.nlm.nih.gov/research/umls/rxnorm``)
  - Missing codes the LLM should have included
  - Extra codes the LLM included that aren't relevant
  - Correct system usage even if the specific codes vary

This is independent of the execution-based evaluation: an LLM can return the
right *patients* by accident (e.g., querying with a parent code that subsumes
the requested children), but get low scores here for not naming the codes the
test author specified.
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlsplit

backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import CodeSystemValidationResult
from src.api.models.test_case import Code

logger = logging.getLogger(__name__)


# FHIR code-bearing search parameters. Composite parameters like
# ``code-value-quantity`` use ``$`` separators after the system|code pair.
# We strip everything after the first ``$`` when extracting tokens.
_CODE_PARAM_PATTERN = re.compile(
    r"(^|:)code(\b|-value-quantity)|"
    r"(^|:)medication(\b|-code)|"
    r"(^|:)diagnosis"
)

_SYSTEM_NORMALIZATIONS = {
    # Common LLM mistakes mapped to canonical FHIR URIs.
    "rxnorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "snomed": "http://snomed.info/sct",
    "snomed-ct": "http://snomed.info/sct",
    "snomedct": "http://snomed.info/sct",
    "loinc": "http://loinc.org",
    "icd10": "http://hl7.org/fhir/sid/icd-10-cm",
    "icd10cm": "http://hl7.org/fhir/sid/icd-10-cm",
    "icd-10": "http://hl7.org/fhir/sid/icd-10-cm",
    "icd-10-cm": "http://hl7.org/fhir/sid/icd-10-cm",
    "icd9cm": "http://hl7.org/fhir/sid/icd-9-cm",
    "icd-9-cm": "http://hl7.org/fhir/sid/icd-9-cm",
    "cpt": "http://www.ama-assn.org/go/cpt",
}


def _normalize_system(system: str | None) -> str | None:
    if not system:
        return None
    s = system.strip()
    canonical = _SYSTEM_NORMALIZATIONS.get(s.lower())
    return canonical if canonical else s


def _is_code_bearing_param(name: str) -> bool:
    """Identify search parameters that carry code values.

    Handles plain (``code``), chained via ``_has`` (``_has:Condition:patient:code``),
    and composite (``code-value-quantity``) forms. Also includes ``medication``
    (some servers use this on MedicationRequest) and ``diagnosis``.
    """
    if not name:
        return False
    return bool(_CODE_PARAM_PATTERN.search(name))


def _split_code_token(token: str) -> tuple[str | None, str]:
    """Parse a single ``system|code`` token, stripping any composite suffix.

    Examples:
      "http://loinc.org|4548-4"     -> ("http://loinc.org", "4548-4")
      "44054006"                     -> (None, "44054006")
      "http://loinc.org|4548-4$ge6.5" -> ("http://loinc.org", "4548-4")
      "system|code$prefix|value"    -> ("system", "code")  (composite stripped)
    """
    # Strip composite parameter trailing portion (after $)
    head = token.split("$", 1)[0]
    if "|" in head:
        system, code = head.split("|", 1)
        return (system or None), code
    return None, head


def extract_codes_from_url(url: str) -> list[tuple[str | None, str]]:
    """Extract all (system, code) pairs from a FHIR query URL.

    Returns codes from any code-bearing search parameter, including chained
    forms via ``_has``. System is None when the parameter has no system|code
    qualifier (which is itself a common LLM error worth flagging).
    """
    if not url:
        return []
    parsed = urlsplit(url)
    qs = parsed.query if parsed.query else url.split("?", 1)[1] if "?" in url else ""
    if not qs:
        return []

    pairs: list[tuple[str | None, str]] = []
    # keep_blank_values so we don't drop empty values silently
    for name, value in parse_qsl(qs, keep_blank_values=True):
        if not _is_code_bearing_param(name):
            continue
        # Comma separates multiple codes within a single parameter
        for token in value.split(","):
            token = token.strip()
            if not token:
                continue
            system, code = _split_code_token(token)
            system = _normalize_system(system)
            pairs.append((system, code))
    return pairs


class CodeSystemValidator:
    """Compare codes used by generated queries against ``metadata.required_codes``."""

    def evaluate(
        self,
        required_codes: list[Code],
        generated_query_urls: Iterable[str],
    ) -> CodeSystemValidationResult:
        """Run the validation.

        ``passed`` is True when:
          - Every required system is represented in the generated codes
            (``len(missing_systems) == 0``)
          - No generated code uses a system not in the required set
            (``len(incorrect_systems) == 0``)
        Missing/extra individual codes are reported but don't fail by
        themselves — they're useful diagnostics for whether the LLM used
        the full code family the test author specified.
        """
        required_pairs: set[tuple[str, str]] = set()
        required_systems: set[str] = set()
        for c in required_codes:
            sys_norm = _normalize_system(c.system) or ""
            required_pairs.add((sys_norm, c.code))
            if sys_norm:
                required_systems.add(sys_norm)

        generated_pairs: set[tuple[str | None, str]] = set()
        for url in generated_query_urls:
            for pair in extract_codes_from_url(url):
                generated_pairs.add(pair)

        generated_systems: set[str] = {s for s, _ in generated_pairs if s}
        # Treat None-system codes (no URI specified) as a quality issue
        codes_without_system = {c for s, c in generated_pairs if s is None}

        # Per-pair set ops
        normalized_generated_pairs = {(s or "", c) for s, c in generated_pairs}
        matched = required_pairs & normalized_generated_pairs
        missing = required_pairs - normalized_generated_pairs
        extra = normalized_generated_pairs - required_pairs

        correct_systems = sorted(required_systems & generated_systems)
        incorrect_systems = sorted(generated_systems - required_systems)
        missing_systems = sorted(required_systems - generated_systems)

        # Codes without a system URI are a quality issue (FHIR servers won't
        # match them correctly across multi-system queries) — flag them as
        # "extras" so test authors see them in reports.
        extra_codes = sorted({f"{s}|{c}" for s, c in extra if s} | {f"|{c}" for c in codes_without_system})
        missing_codes = sorted({f"{s}|{c}" for s, c in missing})

        passed = (
            len(missing_systems) == 0
            and len(incorrect_systems) == 0
            and len(codes_without_system) == 0
        )

        logger.debug(
            "CodeSystemValidation: passed=%s correct_systems=%s incorrect_systems=%s "
            "missing_systems=%s missing_codes=%d extra_codes=%d codes_without_system=%d "
            "matched=%d/%d required_pairs",
            passed, correct_systems, incorrect_systems, missing_systems,
            len(missing_codes), len(extra_codes), len(codes_without_system),
            len(matched), len(required_pairs),
        )

        return CodeSystemValidationResult(
            passed=passed,
            correct_systems=correct_systems,
            incorrect_systems=incorrect_systems,
            missing_codes=missing_codes,
            extra_codes=extra_codes,
        )
