"""Smoke test for FoundryLocalProvider.

Runs three checks against a live Foundry Local server:
  1. Provider constructs (port discovery + model load + alias resolution).
  2. generate_fhir_query returns a parseable FHIR URL for a trivial prompt.
  3. recover_tool_calls_from_content() correctly parses both the proper
     <tool_call>...</tool_call> form and the mangled )((((...)))) form
     observed in Foundry Local 0.8.119.

Usage:
    python scripts/smoke_foundry_local.py
    python scripts/smoke_foundry_local.py --model qwen2.5-7b
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from src.llm.foundry_local_provider import FoundryLocalProvider


def check_recovery_parser() -> None:
    proper = (
        "Sure, I'll look that up.\n"
        '<tool_call>{"name": "lookup_loinc", "arguments": {"concept": "HbA1c"}}</tool_call>'
    )
    mangled = ')(((({"name": "lookup_loinc", "arguments": {"concept": "HbA1c"}}))))'
    array = (
        '<tool_call>[{"name": "lookup_loinc", "parameters": {"concept": "HbA1c"}}]</tool_call>'
    )

    for label, text in [("proper", proper), ("mangled", mangled), ("array", array)]:
        calls = FoundryLocalProvider.recover_tool_calls_from_content(text)
        assert len(calls) == 1, f"{label}: expected 1 call, got {len(calls)}"
        fn = calls[0]["function"]
        assert fn["name"] == "lookup_loinc", f"{label}: bad name {fn['name']}"
        assert "HbA1c" in fn["arguments"], f"{label}: bad args {fn['arguments']}"
        print(f"  [OK] recovery parser handles '{label}' form")


def check_generate(provider: FoundryLocalProvider) -> None:
    prompt = "Find all patients with a diagnosis of type 2 diabetes."
    result = provider.generate_fhir_query(prompt)
    print(f"  raw_response (first 200 chars): {result.raw_response[:200]!r}")
    if result.parsed_query is None:
        raise SystemExit("FAILED: provider returned no parsed FHIR query")
    print(f"  parsed_query.url: {result.parsed_query.url}")
    print(f"  parsed_query.resource_type: {result.parsed_query.resource_type}")
    print("  [OK] generate_fhir_query returned a parseable FHIR URL")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="qwen2.5-7b")
    p.add_argument("--base-url", default=None,
                   help="Override service URL (default: discover via `foundry service status`)")
    args = p.parse_args()

    print("== FoundryLocalProvider smoke test ==\n")

    print("1. recovery parser unit checks")
    check_recovery_parser()

    print(f"\n2. constructing provider (model={args.model}) — model load may take ~10-30s")
    provider = FoundryLocalProvider(model=args.model)
    print(f"  model_id:   {provider.model_id}")

    print("\n3. generate_fhir_query (closed-book)")
    check_generate(provider)

    print("\n== ALL CHECKS PASSED ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
