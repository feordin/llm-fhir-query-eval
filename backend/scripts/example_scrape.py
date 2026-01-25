"""Example script showing how to use the PheKB scraper programmatically

This demonstrates the scraper/extractor/generator workflow.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper.phekb import PheKBScraper
from src.scraper.extractor import PhenotypeExtractor
from src.scraper.generator import TestCaseGenerator


def main():
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    # Example 1: List phenotypes
    print("=== Listing PheKB Phenotypes ===\n")
    scraper = PheKBScraper()
    phenotypes = scraper.list_phenotypes()
    print(f"Found {len(phenotypes)} phenotypes\n")

    # Show first 5
    for i, phenotype in enumerate(phenotypes[:5], 1):
        print(f"{i}. {phenotype.name}")
        print(f"   ID: {phenotype.id}")
        print(f"   URL: {phenotype.url}\n")

    # Example 2: Get phenotype details
    if phenotypes:
        print(f"\n=== Getting Details for: {phenotypes[0].name} ===\n")
        details = scraper.get_phenotype_details(phenotypes[0])
        print(f"Description: {details.get('description', 'N/A')[:200]}...")
        print(f"Files: {len(details.get('files', []))} files found")

    # Example 3: Extract test case data (requires API key)
    print("\n=== Extracting Test Case Data ===\n")
    extractor = PhenotypeExtractor(api_key=api_key)

    # Use first phenotype as example
    if phenotypes and details:
        print(f"Analyzing phenotype with Claude: {phenotypes[0].name}")
        print("This may take a minute...\n")

        try:
            test_case_data = extractor.extract_test_case_data(details)

            print("Extracted Data:")
            print(f"  Prompt: {test_case_data['prompt']}")
            print(f"  Query: {test_case_data['expected_query']['url']}")
            print(f"  Code Systems: {test_case_data['metadata']['code_systems']}")
            print(f"  Complexity: {test_case_data['metadata']['complexity']}")

            # Validate
            is_valid = extractor.validate_extraction(test_case_data)
            print(f"\n  Validation: {'✓ Passed' if is_valid else '✗ Failed'}")

        except Exception as e:
            print(f"Error during extraction: {e}")

    # Example 4: Generate complete test case
    print("\n=== Generating Complete Test Case ===\n")
    generator = TestCaseGenerator(
        anthropic_api_key=api_key,
        output_dir="test-cases/phekb",
        download_dir="data/phekb-downloads"
    )

    # Note: This would actually generate a test case file
    # Commented out to avoid creating files during example run
    # test_case = generator.generate_from_phenotype_id(phenotypes[0].id)
    # print(f"Generated test case: {test_case.id}")

    print("To generate actual test cases, use the CLI:")
    print("  fhir-eval scrape --id <phenotype-id>")


if __name__ == "__main__":
    main()
