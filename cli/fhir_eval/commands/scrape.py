import click
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# Add backend to path so we can import modules
backend_path = Path(__file__).parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from src.scraper.phekb import PheKBScraper
from src.scraper.generator import TestCaseGenerator
import logging


@click.group()
def scrape():
    """Scrape PheKB phenotypes (two-stage process)"""
    pass


@scrape.command()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def list_urls(verbose):
    """STAGE 1: Fetch all phenotype URLs (with pagination)

    This scrapes the PheKB website, handles pagination, and saves
    all phenotype URLs to data/phekb-raw/phenotypes.json

    You only need to run this once (or when you want to refresh the list).

    Example:
        fhir-eval scrape list-urls
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    click.echo("=" * 60)
    click.echo("STAGE 1: Fetching all phenotype URLs from PheKB")
    click.echo("=" * 60)
    click.echo("\nThis will:")
    click.echo("  1. Load the phenotypes page")
    click.echo("  2. Handle pagination to get ALL phenotypes")
    click.echo("  3. Save the list to data/phekb-raw/phenotypes.json")
    click.echo("\nThis may take a few minutes...\n")

    scraper = PheKBScraper()

    try:
        phenotypes = scraper.list_all_phenotypes(save=True)

        click.echo("\n" + "=" * 60)
        click.echo(f"SUCCESS! Found {len(phenotypes)} phenotypes")
        click.echo("=" * 60)
        click.echo(f"\nSaved to: data/phekb-raw/phenotypes.json")
        click.echo("\nFirst 10 phenotypes:")
        for i, p in enumerate(phenotypes[:10], 1):
            click.echo(f"  {i}. {p.name}")

        if len(phenotypes) > 10:
            click.echo(f"  ... and {len(phenotypes) - 10} more")

        click.echo("\nNext step: Run 'fhir-eval scrape download' to download details")

    except Exception as e:
        click.echo(f"\n[ERROR] Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@scrape.command()
@click.option("--limit", type=int, help="Limit number of phenotypes to download")
@click.option("--id", "phenotype_id", help="Download specific phenotype by ID")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def download(limit, phenotype_id, verbose):
    """STAGE 2: Download phenotype details and files

    This downloads the description and files (PDFs, Word docs) for each
    phenotype and saves them to data/phekb-raw/[phenotype-id]/

    You must run 'fhir-eval scrape list-urls' first!

    Examples:
        # Download specific phenotype
        fhir-eval scrape download --id 123

        # Download first 5 phenotypes
        fhir-eval scrape download --limit 5

        # Download all phenotypes (takes hours!)
        fhir-eval scrape download
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    scraper = PheKBScraper()

    # Load phenotype list
    try:
        phenotypes = scraper.load_phenotype_list()
    except FileNotFoundError:
        click.echo("Error: Phenotype list not found!", err=True)
        click.echo("Run 'fhir-eval scrape list-urls' first to fetch the URLs", err=True)
        sys.exit(1)

    # Filter if specific ID requested
    if phenotype_id:
        phenotypes = [p for p in phenotypes if p.id == phenotype_id]
        if not phenotypes:
            click.echo(f"Error: Phenotype '{phenotype_id}' not found", err=True)
            sys.exit(1)
    elif limit:
        phenotypes = phenotypes[:limit]

    click.echo("=" * 60)
    click.echo(f"STAGE 2: Downloading details for {len(phenotypes)} phenotypes")
    click.echo("=" * 60)
    click.echo("\nFor each phenotype, this will download:")
    click.echo("  - Summary description (saved as description.txt)")
    click.echo("  - Metadata (saved as details.json)")
    click.echo("  - PDF files")
    click.echo("  - Word documents")
    click.echo("  (Excel files are skipped)")
    click.echo(f"\nEach phenotype is saved in: data/phekb-raw/[phenotype-id]/")
    click.echo(f"\nEstimated time: ~{len(phenotypes) * 5} seconds (~5 sec/phenotype)")
    click.echo()

    if len(phenotypes) > 5 and not click.confirm("Continue?"):
        return

    # Download details
    try:
        for i, phenotype in enumerate(phenotypes, 1):
            click.echo(f"\n[{i}/{len(phenotypes)}] {phenotype.name}")
            click.echo(f"  URL: {phenotype.url}")

            try:
                details = scraper.download_phenotype_details(phenotype)
                file_count = len(details['downloaded_files']) if details.get('downloaded_files') else 0
                click.echo(f"  ✓ Downloaded {file_count} files")
                click.echo(f"  ✓ Saved to: {details['phenotype_dir']}")
            except Exception as e:
                click.echo(f"  ✗ Error: {e}", err=True)
                continue

        click.echo("\n" + "=" * 60)
        click.echo("✓ Download complete!")
        click.echo("=" * 60)
        click.echo("\nData saved to: data/phekb-raw/")
        click.echo("\nEach phenotype folder contains:")
        click.echo("  - description.txt (summary paragraph)")
        click.echo("  - details.json (metadata)")
        click.echo("  - Downloaded PDF/Word files")
        click.echo("\nNext: Use this data to generate FHIR test cases")

    except Exception as e:
        click.echo(f"\n[ERROR] Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@scrape.command()
def status():
    """Check scraping status

    Shows what's been downloaded and what's remaining.
    """
    scraper = PheKBScraper()

    try:
        phenotypes = scraper.load_phenotype_list()
        total = len(phenotypes)

        # Check how many have been downloaded
        downloaded = 0
        for p in phenotypes:
            phenotype_dir = scraper.data_dir / p.id
            if (phenotype_dir / "details.json").exists():
                downloaded += 1

        click.echo("=" * 60)
        click.echo("PheKB Scraping Status")
        click.echo("=" * 60)
        click.echo(f"\nTotal phenotypes: {total}")
        click.echo(f"Downloaded:       {downloaded} ({downloaded/total*100:.1f}%)")
        click.echo(f"Remaining:        {total - downloaded}")
        click.echo(f"\nData directory: {scraper.data_dir}")

    except FileNotFoundError:
        click.echo("No phenotype list found.")
        click.echo("Run 'fhir-eval scrape list-urls' to start")
        sys.exit(1)


@scrape.command()
@click.option("--limit", type=int, help="Limit number of test cases to generate")
@click.option("--id", "phenotype_id", help="Generate test case for specific phenotype by ID")
@click.option("--skip-existing", is_flag=True, default=True, help="Skip phenotypes that already have test cases (default: True)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def generate(limit, phenotype_id, skip_existing, verbose):
    """STAGE 3: Generate FHIR test cases from downloaded phenotypes

    This uses Claude to analyze each phenotype and generate:
    - Natural language prompt (without codes)
    - Expected FHIR query (with proper codes)
    - Test case metadata

    Test cases are saved to test-cases/phekb/

    You must run 'fhir-eval scrape download' first!

    Requires ANTHROPIC_API_KEY in .env file.

    Examples:
        # Generate test case for specific phenotype
        fhir-eval scrape generate --id abdominal-aortic-aneurysm-aaa

        # Generate first 5 test cases
        fhir-eval scrape generate --limit 5

        # Generate all test cases (expensive!)
        fhir-eval scrape generate
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        click.echo("Error: ANTHROPIC_API_KEY not found in environment", err=True)
        click.echo("Add it to your .env file or set it as an environment variable", err=True)
        sys.exit(1)

    # Initialize generator
    generator = TestCaseGenerator(
        anthropic_api_key=api_key,
        output_dir="test-cases/phekb",
        download_dir="data/phekb-raw"
    )

    # Load phenotype list
    try:
        scraper = PheKBScraper(data_dir="data/phekb-raw")
        phenotypes = scraper.load_phenotype_list()
    except FileNotFoundError:
        click.echo("Error: Phenotype list not found!", err=True)
        click.echo("Run 'fhir-eval scrape list-urls' and 'fhir-eval scrape download' first", err=True)
        sys.exit(1)

    # Filter if specific ID requested
    if phenotype_id:
        phenotypes = [p for p in phenotypes if p.id == phenotype_id]
        if not phenotypes:
            click.echo(f"Error: Phenotype '{phenotype_id}' not found", err=True)
            sys.exit(1)
        
        # Check if downloaded
        phenotype_dir = Path("data/phekb-raw") / phenotype_id
        if not (phenotype_dir / "details.json").exists():
            click.echo(f"Error: Phenotype '{phenotype_id}' not downloaded yet", err=True)
            click.echo(f"Run: fhir-eval scrape download --id {phenotype_id}", err=True)
            sys.exit(1)
    elif limit:
        phenotypes = phenotypes[:limit]

    # Filter only downloaded phenotypes
    downloaded_phenotypes = []
    for p in phenotypes:
        phenotype_dir = Path("data/phekb-raw") / p.id
        if (phenotype_dir / "details.json").exists():
            downloaded_phenotypes.append(p)
    
    phenotypes = downloaded_phenotypes

    if not phenotypes:
        click.echo("No downloaded phenotypes found!", err=True)
        click.echo("Run 'fhir-eval scrape download' first", err=True)
        sys.exit(1)

    click.echo("=" * 60)
    click.echo(f"STAGE 3: Generating test cases for {len(phenotypes)} phenotypes")
    click.echo("=" * 60)
    click.echo("\nThis will:")
    click.echo("  - Use Claude to analyze each phenotype")
    click.echo("  - Generate natural language prompts (no codes)")
    click.echo("  - Generate expected FHIR queries (with codes)")
    click.echo("  - Save test cases to test-cases/phekb/")
    click.echo(f"\nEstimated time: ~{len(phenotypes) * 10} seconds (~10 sec/phenotype)")
    click.echo(f"Estimated cost: ~${len(phenotypes) * 0.02:.2f} (Claude API)")
    click.echo()

    if len(phenotypes) > 5 and not phenotype_id and not click.confirm("Continue?"):
        return

    # Generate test cases
    success_count = 0
    error_count = 0

    try:
        for i, phenotype in enumerate(phenotypes, 1):
            click.echo(f"\n[{i}/{len(phenotypes)}] {phenotype.name}")
            click.echo(f"  ID: {phenotype.id}")

            # Check if already exists
            test_case_path = Path("test-cases/phekb") / f"phekb-{phenotype.id}.json"
            if skip_existing and test_case_path.exists():
                click.echo(f"  ⊘ Already exists, skipping")
                continue

            try:
                test_case = generator.generate_from_phenotype_id(phenotype.id)
                if test_case:
                    click.echo(f"  ✓ Generated test case")
                    click.echo(f"  ✓ Saved to: {test_case_path}")
                    success_count += 1
                else:
                    click.echo(f"  ✗ Failed to generate", err=True)
                    error_count += 1
            except Exception as e:
                click.echo(f"  ✗ Error: {e}", err=True)
                if verbose:
                    import traceback
                    traceback.print_exc()
                error_count += 1
                continue

        click.echo("\n" + "=" * 60)
        click.echo("✓ Test case generation complete!")
        click.echo("=" * 60)
        click.echo(f"\nGenerated: {success_count}")
        click.echo(f"Errors:    {error_count}")
        click.echo(f"\nTest cases saved to: test-cases/phekb/")

    except Exception as e:
        click.echo(f"\n[ERROR] Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
