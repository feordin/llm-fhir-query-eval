"""Claude-based phenotype prompt and query extractor

Uses Claude to analyze PheKB phenotypes and generate:
1. Natural language prompts (without codes) - as a clinician would write
2. Expected FHIR queries with proper codes
"""

import anthropic
from typing import Dict, List, Optional
import logging
import json

logger = logging.getLogger(__name__)


class PhenotypeExtractor:
    """Extract test case prompts and queries from phenotype definitions using Claude"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        """Initialize extractor

        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def extract_test_case_data(self, phenotype_details: Dict) -> Dict:
        """Extract test case data from phenotype details

        Args:
            phenotype_details: Dictionary with phenotype information

        Returns:
            Dictionary with:
            - prompt: Natural language prompt (no codes)
            - expected_query: FHIR query with proper codes
            - metadata: Implementation guide, code systems, etc.
        """
        logger.info(f"Extracting test case data for: {phenotype_details['name']}")

        # Create prompt for Claude
        system_prompt = """You are a clinical informatics expert helping to create FHIR query test cases from phenotype definitions.

Your task is to:
1. Analyze the phenotype definition
2. Create a natural language prompt that a clinician or medical researcher would write (WITHOUT including any codes or code systems)
3. Generate the expected FHIR query that correctly implements this request (WITH proper LOINC, SNOMED CT, ICD-10, or other appropriate codes)

The prompt should be realistic clinical language like:
- "Find all patients with a diagnosis of type 2 diabetes"
- "Get blood pressure measurements for adults over age 40"
- "Retrieve lab results showing elevated cholesterol levels"

DO NOT include codes in the prompt. The evaluation framework will test whether LLMs can determine the correct codes.

The expected FHIR query should use proper clinical code systems and be technically correct."""

        user_prompt = f"""Analyze this phenotype definition and create a test case:

Phenotype Name: {phenotype_details['name']}
Description: {phenotype_details.get('description', 'Not provided')}
Category: {phenotype_details.get('category', 'Not provided')}

Based on this phenotype, provide:

1. A natural language prompt (1-3 sentences) that a clinician would write to request this data. DO NOT include any codes, code systems, or technical identifiers.

2. The expected FHIR query including:
   - Resource type (Patient, Observation, Condition, MedicationRequest, etc.)
   - Query parameters with proper codes (LOINC, SNOMED CT, ICD-10, RxNorm, etc.)
   - Full query URL

3. Metadata about the query including:
   - Which implementation guide(s) apply (e.g., "US Core 5.0.0")
   - Which code systems are used
   - List of required codes with system, code, and display name
   - Complexity level (simple, medium, complex)
   - Relevant tags

Return your response as a JSON object with this structure:
{{
  "prompt": "Natural language description without codes",
  "description": "Longer description of what this test case evaluates",
  "expected_query": {{
    "resource_type": "ResourceType",
    "parameters": {{
      "param1": "value1",
      "param2": "value2"
    }},
    "url": "ResourceType?param1=value1&param2=value2"
  }},
  "metadata": {{
    "implementation_guide": "US Core 5.0.0",
    "code_systems": ["LOINC", "SNOMED CT"],
    "required_codes": [
      {{
        "system": "http://loinc.org",
        "code": "12345-6",
        "display": "Code display name"
      }}
    ],
    "complexity": "medium",
    "tags": ["tag1", "tag2"]
  }}
}}

Important:
- The prompt must be in natural clinical language without any codes
- The expected_query must have technically correct FHIR syntax
- Use appropriate clinical code systems for the condition/observation
- If you're not certain about specific codes, use commonly accepted codes for that clinical concept"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Extract JSON from response
            response_text = message.content[0].text

            # Try to parse JSON from response
            # Claude might wrap it in markdown code blocks
            if "```json" in response_text:
                json_start = response_text.index("```json") + 7
                json_end = response_text.rindex("```")
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.index("```") + 3
                json_end = response_text.rindex("```")
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text.strip()

            result = json.loads(json_text)

            logger.info(f"Successfully extracted test case data")
            return result

        except Exception as e:
            logger.error(f"Failed to extract test case data: {e}")
            raise

    def validate_extraction(self, extracted_data: Dict) -> bool:
        """Validate that extracted data has required fields

        Args:
            extracted_data: Extracted test case data

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["prompt", "expected_query", "metadata"]

        for field in required_fields:
            if field not in extracted_data:
                logger.error(f"Missing required field: {field}")
                return False

        # Check that prompt doesn't contain obvious codes
        prompt = extracted_data["prompt"].lower()
        code_indicators = ["loinc", "snomed", "icd-10", "rxnorm", "code:", "system:"]

        for indicator in code_indicators:
            if indicator in prompt:
                logger.warning(
                    f"Prompt may contain code system reference: {indicator}"
                )
                # Don't fail, just warn
                break

        # Validate expected_query structure
        query = extracted_data.get("expected_query", {})
        if not all(k in query for k in ["resource_type", "parameters", "url"]):
            logger.error("expected_query missing required fields")
            return False

        return True

    def enhance_with_files(
        self,
        phenotype_details: Dict,
        file_contents: Dict[str, str]
    ) -> Dict:
        """Enhance extraction using downloaded file contents

        Args:
            phenotype_details: Basic phenotype details
            file_contents: Dictionary mapping filename to file content

        Returns:
            Enhanced test case data
        """
        logger.info("Enhancing extraction with file contents")

        # Add file contents to the extraction prompt
        files_text = "\n\n".join([
            f"File: {filename}\nContent:\n{content[:2000]}..."
            for filename, content in file_contents.items()
        ])

        # Update phenotype details with file info
        enhanced_details = phenotype_details.copy()
        enhanced_details["file_contents"] = files_text

        return self.extract_test_case_data(enhanced_details)
