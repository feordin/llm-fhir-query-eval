import click
import json
import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from src.fhir.client import FHIRClient
from src.llm import get_provider
from src.evaluation.runner import EvaluationRunner
from src.api.models.test_case import TestCase


@click.command()
@click.option("--test-case", "-t", required=True, help="Test case ID (e.g., phekb-type-2-diabetes)")
@click.option("--provider", "-p", default="claude-cli", help="LLM provider: anthropic, claude-cli, command")
@click.option("--model", "-m", default=None, help="Model name (provider-specific)")
@click.option("--command", "-c", default=None, help="Command for 'command' provider (e.g., 'ollama run llama3')")
@click.option("--fhir-url", default="http://localhost:8080", help="FHIR server base URL")
@click.option("--output-dir", "-o", default="results", help="Directory to save results")
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
def run(test_case, provider, model, command, fhir_url, output_dir, verbose):
    """Run FHIR query evaluation against an LLM.

    Examples:
        fhir-eval run -t phekb-type-2-diabetes -p claude-cli
        fhir-eval run -t phekb-type-2-diabetes -p anthropic -m claude-sonnet-4-20250514
        fhir-eval run -t phekb-type-2-diabetes -p command -c "ollama run llama3"
    """
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    project_root = Path(__file__).parent.parent.parent.parent

    click.echo("=" * 60)
    click.echo("FHIR Query Evaluation")
    click.echo("=" * 60)

    # Step 1: Load test case
    click.echo(f"\n[1/5] Loading test case: {test_case}")
    tc = _load_test_case(test_case, project_root)
    if not tc:
        sys.exit(1)
    click.echo(f"  Name: {tc.name}")
    click.echo(f"  Prompt: {tc.prompt[:80]}...")
    click.echo(f"  Expected query: {tc.expected_query.url}")

    # Step 2: Check FHIR server
    click.echo(f"\n[2/5] Checking FHIR server at {fhir_url}...")
    fhir_client = FHIRClient(base_url=fhir_url)
    if not fhir_client.health_check():
        click.echo("  ERROR: FHIR server not responding!")
        click.echo("  Start it with: docker-compose up -d fhir-candle")
        sys.exit(1)
    click.echo("  FHIR server is healthy.")

    # Check if data is loaded
    try:
        patient_count = fhir_client.get_resource_count("Patient?_summary=count")
        click.echo(f"  Patients in server: {patient_count}")
        if patient_count == 0:
            click.echo("  WARNING: No patients loaded! Run 'fhir-eval load synthea' first.")
    except Exception:
        pass

    # Step 3: Initialize LLM provider
    click.echo(f"\n[3/5] Initializing LLM provider: {provider}")
    try:
        kwargs = {}
        if command:
            kwargs["command"] = command
        llm = get_provider(provider, model=model, **kwargs)
        model_name = model or provider
        click.echo(f"  Provider: {provider}, Model: {model_name}")
    except Exception as e:
        click.echo(f"  ERROR: {e}")
        sys.exit(1)

    # Step 4: Run evaluation
    click.echo(f"\n[4/5] Running evaluation...")
    runner = EvaluationRunner(fhir_client, llm)

    try:
        result = runner.run_single(tc, provider_name=provider, model_name=model_name)
    except Exception as e:
        click.echo(f"  ERROR during evaluation: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Step 5: Display results
    click.echo(f"\n[5/5] Results")
    click.echo("=" * 60)

    er = result.evaluation_results

    if result.generated_query.is_multi_query:
        click.echo(f"\n  Generated Queries ({len(result.generated_query.all_queries)}):")
        for i, q in enumerate(result.generated_query.all_queries, 1):
            click.echo(f"    {i}. {q.url}")
        if tc.metadata.expected_queries:
            click.echo(f"\n  Expected Queries ({len(tc.metadata.expected_queries)}):")
            for i, url in enumerate(tc.metadata.expected_queries, 1):
                click.echo(f"    {i}. {url}")
    else:
        click.echo(f"\n  Generated Query: {result.generated_query.parsed_query.url}")
        click.echo(f"  Expected Query:  {tc.expected_query.url}")

    click.echo(f"\n  --- Execution-Based Evaluation ---")
    click.echo(f"  Expected results:  {er.execution_match.expected_count}")
    click.echo(f"  Generated results: {er.execution_match.actual_count}")
    click.echo(f"  Precision: {er.execution_match.precision:.4f}")
    click.echo(f"  Recall:    {er.execution_match.recall:.4f}")
    click.echo(f"  F1 Score:  {er.execution_match.f1_score:.4f}")
    click.echo(f"  Passed:    {'YES' if er.execution_match.passed else 'NO'}")

    click.echo(f"\n  --- Semantic Evaluation ---")
    click.echo(f"  Resource type match: {'YES' if er.semantic_match.resource_type_match else 'NO'}")
    click.echo(f"  Parameters match:    {'YES' if er.semantic_match.parameters_match else 'NO'}")
    if er.semantic_match.differences:
        for diff in er.semantic_match.differences:
            click.echo(f"    - {diff}")
    click.echo(f"  Passed: {'YES' if er.semantic_match.passed else 'NO'}")

    click.echo(f"\n  --- Overall ---")
    click.echo(f"  Score:  {result.overall_score:.4f}")
    click.echo(f"  Passed: {'YES' if result.passed else 'NO'}")
    click.echo("=" * 60)

    # Save results
    results_dir = project_root / output_dir
    results_dir.mkdir(exist_ok=True)

    result_file = results_dir / f"{result.evaluation_id}.json"
    with open(result_file, "w") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, default=str)

    click.echo(f"\nResults saved to: {result_file}")


def _load_test_case(test_case_id: str, project_root: Path) -> TestCase:
    """Load a test case by ID from the test-cases directories."""
    # Search in both manual and phekb directories
    for subdir in ["phekb", "manual"]:
        tc_file = project_root / "test-cases" / subdir / f"{test_case_id}.json"
        if tc_file.exists():
            with open(tc_file) as f:
                data = json.load(f)
            click.echo(f"  Loaded from: {tc_file}")
            return TestCase(**data)

    # Try finding by partial match
    for subdir in ["phekb", "manual"]:
        tc_dir = project_root / "test-cases" / subdir
        if tc_dir.exists():
            for f in tc_dir.glob("*.json"):
                if test_case_id in f.stem:
                    with open(f) as fh:
                        data = json.load(fh)
                    click.echo(f"  Loaded from: {f}")
                    return TestCase(**data)

    click.echo(f"  ERROR: Test case '{test_case_id}' not found in test-cases/phekb/ or test-cases/manual/")
    return None
