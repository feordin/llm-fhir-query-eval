import click
import json
import sys
import os
from pathlib import Path
from glob import glob

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from src.fhir.client import FHIRClient


@click.group()
def load():
    """Load FHIR test data into the server"""
    pass


@load.command()
@click.option("--phenotype", "-p", required=True, help="Phenotype name (e.g., type-2-diabetes)")
@click.option("--positive-only", is_flag=True, help="Only load positive cases")
@click.option("--control-only", is_flag=True, help="Only load control cases")
@click.option("--fhir-url", default="http://localhost:8080", help="FHIR server base URL")
@click.option("--update-test-case", is_flag=True, help="Update test case JSON with expected results")
def synthea(phenotype, positive_only, control_only, fhir_url, update_test_case):
    """Load Synthea-generated FHIR bundles for a phenotype.

    Example:
        fhir-eval load synthea -p type-2-diabetes
        fhir-eval load synthea -p type-2-diabetes --positive-only
        fhir-eval load synthea -p type-2-diabetes --update-test-case
    """
    client = FHIRClient(base_url=fhir_url)

    # Health check
    click.echo(f"Connecting to FHIR server at {fhir_url}...")
    if not client.health_check():
        click.echo("ERROR: FHIR server is not responding. Is it running?")
        click.echo("  Start it with: docker-compose up -d fhir-candle")
        sys.exit(1)
    click.echo("FHIR server is healthy.")

    # Find bundle files
    project_root = Path(__file__).parent.parent.parent.parent
    output_dir = project_root / "synthea" / "output" / phenotype

    if not output_dir.exists():
        click.echo(f"ERROR: No Synthea output found at {output_dir}")
        click.echo(f"  Run: python synthea/generate_test_data.py --phenotype {phenotype}")
        sys.exit(1)

    # Load infrastructure files first (hospitals, practitioners) - required by HAPI FHIR
    infra_files = []
    for subdir in ["positive", "control"]:
        fhir_dir = output_dir / subdir / "fhir"
        if fhir_dir.exists():
            for f in sorted(fhir_dir.glob("hospitalInformation*.json")):
                infra_files.append(("infra", f))
            for f in sorted(fhir_dir.glob("practitionerInformation*.json")):
                infra_files.append(("infra", f))

    if infra_files:
        click.echo(f"Found {len(infra_files)} infrastructure bundles (hospitals/practitioners)")

    bundles_to_load = []

    if not control_only:
        positive_dir = output_dir / "positive" / "fhir"
        if positive_dir.exists():
            positive_files = sorted(positive_dir.glob("*.json"))
            positive_files = [f for f in positive_files if not f.name.startswith(("hospital", "practitioner"))]
            bundles_to_load.extend(("positive", f) for f in positive_files)
            click.echo(f"Found {len(positive_files)} positive case bundles")
        else:
            click.echo(f"No positive cases found at {positive_dir}")

    if not positive_only:
        control_dir = output_dir / "control" / "fhir"
        if control_dir.exists():
            control_files = sorted(control_dir.glob("*.json"))
            control_files = [f for f in control_files if not f.name.startswith(("hospital", "practitioner"))]
            bundles_to_load.extend(("control", f) for f in control_files)
            click.echo(f"Found {len(control_files)} control case bundles")
        else:
            click.echo(f"No control cases found at {control_dir}")

    # Prepend infrastructure files so they load first
    bundles_to_load = infra_files + bundles_to_load

    if not bundles_to_load:
        click.echo("No bundles to load.")
        sys.exit(1)

    # Load bundles
    click.echo(f"\nLoading {len(bundles_to_load)} bundles...")
    loaded = 0
    errors = 0

    with click.progressbar(bundles_to_load, label="Loading bundles") as bar:
        for case_type, bundle_file in bar:
            try:
                client.load_bundle_from_file(str(bundle_file))
                loaded += 1
            except Exception as e:
                errors += 1
                click.echo(f"\n  ERROR loading {bundle_file.name}: {e}")

    click.echo(f"\nLoaded: {loaded} bundles, Errors: {errors}")

    # Show counts
    try:
        patient_count = client.get_resource_count("Patient?_summary=count")
        condition_count = client.get_resource_count("Condition?_summary=count")
        observation_count = client.get_resource_count("Observation?_summary=count")
        click.echo(f"\nServer now contains:")
        click.echo(f"  Patients:     {patient_count}")
        click.echo(f"  Conditions:   {condition_count}")
        click.echo(f"  Observations: {observation_count}")
    except Exception:
        pass

    # Optionally update test case
    if update_test_case:
        _update_test_case(client, phenotype, project_root)


def _update_test_case(client, phenotype, project_root):
    """Update the test case JSON with actual expected results from FHIR server."""
    # Find matching test case file
    test_case_file = None
    for pattern in [f"phekb-{phenotype}.json", f"phekb-{phenotype.replace('-', '_')}.json"]:
        candidate = project_root / "test-cases" / "phekb" / pattern
        if candidate.exists():
            test_case_file = candidate
            break

    if not test_case_file:
        # Try scanning all test cases for matching source_id
        for f in (project_root / "test-cases" / "phekb").glob("*.json"):
            with open(f) as fh:
                tc = json.load(fh)
            # Match on phenotype name in source_id
            sid = tc.get("source_id", "")
            if phenotype in sid or sid in phenotype:
                test_case_file = f
                break

    if not test_case_file:
        click.echo(f"Could not find test case file for phenotype '{phenotype}'")
        return

    click.echo(f"\nUpdating test case: {test_case_file.name}")

    with open(test_case_file) as f:
        test_case = json.load(f)

    expected_url = test_case["expected_query"]["url"]
    click.echo(f"Running expected query: {expected_url}")

    try:
        resource_ids = client.get_resource_ids(expected_url)
        count = len(resource_ids)

        click.echo(f"  Found {count} results")

        # Update test_data
        test_case["test_data"]["expected_result_count"] = count
        test_case["test_data"]["expected_resource_ids"] = resource_ids
        test_case["test_data"]["resources"] = [
            f"synthea/output/{phenotype}/positive/fhir/",
            f"synthea/output/{phenotype}/control/fhir/",
        ]

        with open(test_case_file, "w") as f:
            json.dump(test_case, f, indent=2)

        click.echo(f"  Updated {test_case_file.name} with {count} expected results")
    except Exception as e:
        click.echo(f"  ERROR running expected query: {e}")
