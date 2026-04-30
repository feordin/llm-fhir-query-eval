import subprocess
from .provider import LLMProvider, FHIR_SYSTEM_PROMPT, parse_fhir_query_from_text, parse_fhir_queries_from_text

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import GeneratedQuery


class CommandProvider(LLMProvider):
    def __init__(self, command: str):
        self.command = command

    def generate_fhir_query(self, prompt: str, context: str = "") -> GeneratedQuery:
        full_prompt = f"{FHIR_SYSTEM_PROMPT}\n\n"
        if context:
            full_prompt += f"{context}\n\n"
        full_prompt += prompt

        try:
            result = subprocess.run(
                self.command, input=full_prompt.encode("utf-8"), shell=True,
                capture_output=True, timeout=120
            )
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")
                raise RuntimeError(f"Command failed (exit {result.returncode}): {stderr[:500]}")

            raw_text = result.stdout.decode("utf-8", errors="replace").strip()
            if not raw_text:
                raise RuntimeError("Command returned empty output")

            # Try to parse all queries (supports multi-query responses)
            all_parsed = parse_fhir_queries_from_text(raw_text)
            if all_parsed:
                parsed = all_parsed[0]
                additional = all_parsed[1:]
            else:
                parsed = parse_fhir_query_from_text(raw_text)
                additional = []
            return GeneratedQuery(raw_response=raw_text, parsed_query=parsed, additional_queries=additional)
        except FileNotFoundError:
            raise RuntimeError(f"Command not found: {self.command}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Command timed out after 120 seconds")
