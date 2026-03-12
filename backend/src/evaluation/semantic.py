import re
import sys
from pathlib import Path
from urllib.parse import parse_qs

backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import SemanticMatchResult


class SemanticEvaluator:
    """Compares FHIR query structure without executing against a server."""

    def evaluate(self, expected_query_url: str, generated_query_url: str) -> SemanticMatchResult:
        """Parse both query URLs and compare their structure."""
        expected = self._parse_query(expected_query_url)
        generated = self._parse_query(generated_query_url)

        differences = []

        # Compare resource types
        resource_type_match = (
            expected["resource_type"].lower() == generated["resource_type"].lower()
        )
        if not resource_type_match:
            differences.append(
                f"Resource type mismatch: expected '{expected['resource_type']}', "
                f"got '{generated['resource_type']}'"
            )

        # Compare parameters
        expected_keys = set(expected["params"].keys())
        generated_keys = set(generated["params"].keys())

        missing_params = expected_keys - generated_keys
        extra_params = generated_keys - expected_keys

        if missing_params:
            differences.append(f"Missing parameters: {', '.join(sorted(missing_params))}")
        if extra_params:
            differences.append(f"Extra parameters: {', '.join(sorted(extra_params))}")

        # Compare shared parameters
        params_match = True
        for key in expected_keys & generated_keys:
            if key == "code":
                # Special handling: compare code sets
                expected_codes = self._parse_codes(expected["params"][key])
                generated_codes = self._parse_codes(generated["params"][key])

                missing_codes = expected_codes - generated_codes
                extra_codes = generated_codes - expected_codes

                if missing_codes:
                    differences.append(f"Missing codes: {', '.join(sorted(missing_codes))}")
                    params_match = False
                if extra_codes:
                    differences.append(f"Extra codes: {', '.join(sorted(extra_codes))}")
                    # Extra codes don't fail params_match (LLM found more)

                if not missing_codes:
                    # All expected codes present
                    pass
                else:
                    params_match = False
            else:
                if expected["params"][key] != generated["params"][key]:
                    differences.append(
                        f"Parameter '{key}' mismatch: expected '{expected['params'][key]}', "
                        f"got '{generated['params'][key]}'"
                    )
                    params_match = False

        if missing_params:
            params_match = False

        passed = resource_type_match and params_match

        return SemanticMatchResult(
            passed=passed,
            resource_type_match=resource_type_match,
            parameters_match=params_match,
            differences=differences,
        )

    def _parse_query(self, query_url: str) -> dict:
        """Parse a FHIR query URL into resource type and parameters."""
        # Strip any leading slash or server prefix
        url = query_url.strip()
        if '/' in url and '?' in url:
            # Take everything from the last path segment with ?
            parts = url.split('/')
            for part in reversed(parts):
                if '?' in part:
                    url = part
                    break

        if '?' in url:
            resource_type, query_string = url.split('?', 1)
        else:
            resource_type = url
            query_string = ""

        # Parse params manually (not parse_qs which splits on value lists)
        params = {}
        if query_string:
            for part in query_string.split('&'):
                if '=' in part:
                    key, value = part.split('=', 1)
                    params[key] = value

        return {"resource_type": resource_type, "params": params}

    def _parse_codes(self, code_value: str) -> set:
        """Parse a FHIR code parameter value into a set of system|code pairs."""
        return set(code_value.split(','))
