"""Test case generator from PheKB phenotypes

Orchestrates scraping, extraction, and test case file generation.
"""

import os
import json
from datetime import datetime
from typing import List, Optional, Dict
import logging
from pathlib import Path

from src.scraper.phekb import PheKBScraper, Phenotype
from src.scraper.extractor import PhenotypeExtractor
from src.api.models.test_case import TestCase, TestCaseMetadata, ExpectedQuery, TestData

logger = logging.getLogger(__name__)


class TestCaseGenerator:
    """Generate test cases from PheKB phenotypes"""

    def __init__(
        self,
        anthropic_api_key: str,
        output_dir: str = "test-cases/phekb",
        download_dir: str = "data/phekb-raw"
    ):
        """Initialize generator

        Args:
            anthropic_api_key: Anthropic API key for Claude
            output_dir: Directory to save generated test cases
            download_dir: Directory where phenotype data was downloaded
        """
        self.scraper = PheKBScraper(data_dir=download_dir)
        self.extractor = PhenotypeExtractor(api_key=anthropic_api_key)
        self.output_dir = Path(output_dir)
        self.download_dir = Path(download_dir)

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_phenotype_id(self, phenotype_id: str) -> Optional[TestCase]:
        """Generate test case from a specific phenotype ID

        Args:
            phenotype_id: PheKB phenotype ID

        Returns:
            Generated TestCase or None if failed
        """
        logger.info(f"Generating test case for phenotype: {phenotype_id}")

        try:
            # Load details from downloaded data
            phenotype_dir = self.scraper.data_dir / phenotype_id
            details_file = phenotype_dir / "details.json"
            
            if not details_file.exists():
                logger.error(f"Phenotype details not found: {details_file}")
                return None
            
            with open(details_file, "r", encoding="utf-8") as f:
                details = json.load(f)
            
            # Load description from text file
            description_file = phenotype_dir / "description.txt"
            if description_file.exists():
                with open(description_file, "r", encoding="utf-8") as f:
                    description_text = f.read()
                # Add description to details if longer than JSON version
                if len(description_text) > len(details.get("description", "")):
                    details["description"] = description_text

            # Extract test case data using Claude
            extracted_data = self.extractor.extract_test_case_data(details)

            # Validate extraction
            if not self.extractor.validate_extraction(extracted_data):
                logger.error("Extraction validation failed")
                return None

            # Create test case
            test_case = self._create_test_case(phenotype_id, details, extracted_data)

            # Save test case
            self._save_test_case(test_case)

            logger.info(f"Successfully generated test case: {test_case.id}")
            return test_case

        except Exception as e:
            logger.error(f"Failed to generate test case for {phenotype_id}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def generate_from_all_phenotypes(
        self,
        limit: Optional[int] = None,
        skip_existing: bool = True
    ) -> List[TestCase]:
        """Generate test cases from all PheKB phenotypes

        Args:
            limit: Maximum number of test cases to generate (None for all)
            skip_existing: Skip phenotypes that already have test cases

        Returns:
            List of generated test cases
        """
        logger.info("Fetching all phenotypes from PheKB")

        # Get list of phenotypes
        phenotypes = self.scraper.list_phenotypes()

        if limit:
            phenotypes = phenotypes[:limit]

        logger.info(f"Will process {len(phenotypes)} phenotypes")

        test_cases = []
        for i, phenotype in enumerate(phenotypes, 1):
            logger.info(f"Processing phenotype {i}/{len(phenotypes)}: {phenotype.name}")

            # Check if already exists
            if skip_existing:
                test_case_path = self.output_dir / f"{phenotype.id}.json"
                if test_case_path.exists():
                    logger.info(f"Test case already exists, skipping: {phenotype.id}")
                    continue

            # Generate test case
            test_case = self.generate_from_phenotype_id(phenotype.id)

            if test_case:
                test_cases.append(test_case)
            else:
                logger.warning(f"Failed to generate test case for: {phenotype.id}")

            # Be respectful with rate limiting
            if i < len(phenotypes):
                logger.info("Waiting before next phenotype...")

        logger.info(f"Generated {len(test_cases)} test cases")
        return test_cases

    def _create_test_case(
        self,
        phenotype_id: str,
        phenotype_details: Dict,
        extracted_data: Dict
    ) -> TestCase:
        """Create TestCase object from extracted data

        Args:
            phenotype_id: PheKB phenotype ID
            phenotype_details: Phenotype details from scraper
            extracted_data: Extracted data from Claude

        Returns:
            TestCase object
        """
        # Generate test case ID
        test_case_id = f"phekb-{phenotype_id}"

        # Create metadata
        metadata = TestCaseMetadata(**extracted_data["metadata"])

        # Create expected query
        expected_query = ExpectedQuery(**extracted_data["expected_query"])

        # Create test data reference
        # Note: Actual FHIR test resources would need to be generated separately
        test_data = TestData(
            resources=[],  # To be populated with actual test data
            expected_result_count=0,  # To be determined from actual test data
            expected_resource_ids=[]
        )

        # Create test case
        now = datetime.utcnow()
        test_case = TestCase(
            id=test_case_id,
            source="phekb",
            source_id=phenotype_id,
            name=phenotype_details["name"],
            description=extracted_data.get("description", phenotype_details.get("description", "")),
            prompt=extracted_data["prompt"],
            metadata=metadata,
            expected_query=expected_query,
            test_data=test_data,
            created_at=now,
            updated_at=now
        )

        return test_case

    def _save_test_case(self, test_case: TestCase) -> None:
        """Save test case to JSON file

        Args:
            test_case: TestCase to save
        """
        output_path = self.output_dir / f"{test_case.id}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                test_case.model_dump(),
                f,
                indent=2,
                default=str  # Handle datetime serialization
            )

        logger.info(f"Saved test case to: {output_path}")

    def load_test_case(self, test_case_id: str) -> Optional[TestCase]:
        """Load a generated test case

        Args:
            test_case_id: Test case ID

        Returns:
            TestCase or None if not found
        """
        test_case_path = self.output_dir / f"{test_case_id}.json"

        if not test_case_path.exists():
            logger.error(f"Test case not found: {test_case_id}")
            return None

        with open(test_case_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return TestCase(**data)

    def list_generated_test_cases(self) -> List[str]:
        """List all generated test case IDs

        Returns:
            List of test case IDs
        """
        test_case_files = self.output_dir.glob("*.json")
        return [f.stem for f in test_case_files]
