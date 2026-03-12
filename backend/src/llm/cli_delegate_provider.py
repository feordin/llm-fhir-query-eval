import os
import subprocess
import tempfile
from typing import Optional
from .provider import LLMProvider, FHIR_SYSTEM_PROMPT, parse_fhir_query_from_text

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import GeneratedQuery


class CLIDelegateProvider(LLMProvider):
    def __init__(self, cli_command: str = "claude", model: str = None):
        self.cli_command = cli_command
        self.model = model

    def generate_fhir_query(self, prompt: str, context: str = "") -> GeneratedQuery:
        full_prompt = f"{FHIR_SYSTEM_PROMPT}\n\n"
        if context:
            full_prompt += f"{context}\n\n"
        full_prompt += prompt

        # claude CLI: -p/--print for non-interactive output, prompt is positional arg
        # For long prompts with special chars, write to temp file and use --file or
        # pass via --append-system-prompt for the system part, prompt as positional
        cmd = [self.cli_command, "--print", "--append-system-prompt", FHIR_SYSTEM_PROMPT]
        if self.model:
            cmd.extend(["--model", self.model])

        # The user prompt (with optional context) goes as the positional argument
        user_prompt = ""
        if context:
            user_prompt += f"{context}\n\n"
        user_prompt += prompt
        cmd.append(user_prompt)

        # Remove CLAUDECODE env var to allow spawning a new CLI session
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)
        env.pop("CLAUDE_SESSION_ID", None)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=180,
                env=env,
            )
            if result.returncode != 0:
                error_detail = result.stderr[:500] if result.stderr else result.stdout[:500]
                raise RuntimeError(
                    f"CLI command failed (exit {result.returncode}): {error_detail}"
                )

            raw_text = result.stdout.strip()
            if not raw_text:
                raise RuntimeError("CLI returned empty output")

            parsed = parse_fhir_query_from_text(raw_text)
            return GeneratedQuery(raw_response=raw_text, parsed_query=parsed)
        except FileNotFoundError:
            raise RuntimeError(
                f"CLI command '{self.cli_command}' not found. "
                "Make sure Claude Code CLI is installed and on PATH."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("CLI command timed out after 180 seconds")
