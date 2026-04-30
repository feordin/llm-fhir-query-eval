"""Interactive FHIR query agent CLI.

Usage:
    fhir-query-agent --fhir-url http://localhost:8080/fhir --model qwen2.5:7b
    fhir-query-agent --fhir-url http://localhost:8080/fhir --umls-key YOUR_KEY
    fhir-query-agent --fhir-url http://localhost:8080/fhir --query "Find patients with diabetes"
"""

import json
import logging
import os
import sys

import click

from fhir_query_agent.agent import FHIRQueryAgent


@click.command()
@click.option(
    "--fhir-url",
    required=True,
    envvar="FHIR_SERVER_URL",
    help="FHIR server base URL (e.g., http://localhost:8080/fhir). Also reads FHIR_SERVER_URL env var.",
)
@click.option(
    "--model",
    default="qwen2.5:7b",
    show_default=True,
    help="Ollama model name for query generation.",
)
@click.option(
    "--ollama-host",
    envvar="OLLAMA_HOST",
    default=None,
    help="Ollama server URL (default: http://localhost:11434). Also reads OLLAMA_HOST env var.",
)
@click.option(
    "--umls-key",
    envvar="UMLS_API_KEY",
    default=None,
    help="NIH UMLS API key for clinical code lookups. Also reads UMLS_API_KEY env var.",
)
@click.option(
    "--max-iterations",
    default=10,
    show_default=True,
    help="Maximum number of agent loop iterations.",
)
@click.option(
    "--query", "-q",
    default=None,
    help="Single query to run (non-interactive mode). If omitted, starts interactive mode.",
)
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Output results as JSON (useful for scripting).",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Enable verbose logging.",
)
@click.option(
    "--provider",
    type=click.Choice(["ollama", "anthropic"]),
    default="ollama",
    show_default=True,
    help="LLM provider to use.",
)
def main(
    fhir_url: str,
    model: str,
    ollama_host: str,
    umls_key: str,
    max_iterations: int,
    query: str,
    json_output: bool,
    verbose: bool,
    provider: str,
):
    """FHIR Query Agent - Generate accurate FHIR queries from natural language.

    Uses clinical terminology lookup (UMLS) and FHIR server introspection
    to produce correct FHIR REST API search queries.
    """
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    # Create LLM adapter
    if provider == "ollama":
        from fhir_query_agent.adapters.ollama_adapter import OllamaAdapter
        llm = OllamaAdapter(model=model, host=ollama_host)
    elif provider == "anthropic":
        from fhir_query_agent.adapters.anthropic_adapter import AnthropicAdapter
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        llm = AnthropicAdapter(model=model, api_key=api_key)
    else:
        click.echo(f"Unknown provider: {provider}", err=True)
        sys.exit(1)

    # Create agent
    agent = FHIRQueryAgent(
        llm_adapter=llm,
        fhir_base_url=fhir_url,
        umls_api_key=umls_key,
        max_iterations=max_iterations,
    )

    try:
        if query:
            # Single query mode
            result = agent.generate_query(query)

            if json_output:
                output = {
                    "queries": result.queries,
                    "explanation": result.explanation,
                    "iterations": result.iterations,
                    "tool_calls": [
                        {
                            "iteration": tc.iteration,
                            "tool": tc.tool_name,
                            "args": tc.arguments,
                            "duration_ms": tc.duration_ms,
                        }
                        for tc in result.tool_trace
                    ],
                    "success": result.success,
                    "error": result.error,
                }
                click.echo(json.dumps(output, indent=2))
            else:
                # Human-readable output
                if result.tool_trace:
                    click.echo("--- Tool Calls ---")
                    for tc in result.tool_trace:
                        status = tc.result.get("status", "?")
                        click.echo(
                            f"  [{tc.iteration}] {tc.tool_name} -> {status} ({tc.duration_ms}ms)"
                        )
                    click.echo()

                if result.queries:
                    click.echo("--- FHIR Queries ---")
                    for q in result.queries:
                        click.echo(f"  {q}")
                    click.echo()

                if result.explanation:
                    click.echo("--- Explanation ---")
                    click.echo(result.explanation)
                    click.echo()

                if not result.success:
                    click.echo(f"Error: {result.error}", err=True)
                    sys.exit(1)
        else:
            # Interactive mode
            agent.interactive()
    finally:
        agent.close()


if __name__ == "__main__":
    main()
