"""
Direct test case generation from downloaded PheKB phenotypes

This script:
1. Loads each phenotype from data/phekb-raw/
2. Extracts text from PDFs and Word docs
3. Uses Claude to generate FHIR test cases
4. Saves to test-cases/phekb/
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import logging

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from pypdf import PdfReader
from docx import Document
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF file"""
    try:
        reader = PdfReader(str(pdf_path))
        text = []
        for page in reader.pages:
            text.append(page.extract_text())
        return "\n\n".join(text)
    except Exception as e:
        logger.warning(f"Could not extract text from PDF {pdf_path.name}: {e}")
        return ""


def extract_text_from_docx(docx_path: Path) -> str:
    """Extract text from Word document"""
    try:
        doc = Document(str(docx_path))
        text = []
        for para in doc.paragraphs:
            if para.text.strip():
                text.append(para.text)
        return "\n\n".join(text)
    except Exception as e:
        logger.warning(f"Could not extract text from Word doc {docx_path.name}: {e}")
        return ""


def load_phenotype_data(phenotype_dir: Path) -> dict:
    """Load all data for a phenotype"""
    data = {}
    
    # Load details.json
    details_file = phenotype_dir / "details.json"
    if details_file.exists():
        with open(details_file, "r", encoding="utf-8") as f:
            data["details"] = json.load(f)
    
    # Load description.txt
    desc_file = phenotype_dir / "description.txt"
    if desc_file.exists():
        with open(desc_file, "r", encoding="utf-8") as f:
            data["description"] = f.read()
    
    # Extract text from PDFs and Word docs
    file_contents = {}
    for file_path in phenotype_dir.iterdir():
        if file_path.suffix.lower() == ".pdf":
            logger.info(f"  Extracting text from: {file_path.name}")
            text = extract_text_from_pdf(file_path)
            if text:
                file_contents[file_path.name] = text
        elif file_path.suffix.lower() in [".doc", ".docx"]:
            logger.info(f"  Extracting text from: {file_path.name}")
            text = extract_text_from_docx(file_path)
            if text:
                file_contents[file_path.name] = text
    
    data["file_contents"] = file_contents
    
    return data


def generate_test_case_with_claude(phenotype_data: dict, client: Anthropic) -> dict:
    """Use Claude to generate test case from phenotype data"""
    
    details = phenotype_data.get("details", {})
    description = phenotype_data.get("description", "")
    file_contents = phenotype_data.get("file_contents", {})
    
    # Build comprehensive prompt
    system_prompt = """You are a clinical informatics expert creating FHIR query test cases from phenotype definitions.

Your task:
1. Analyze the phenotype definition, description, and any supplementary documents
2. Create a natural language prompt that a clinician would write (WITHOUT codes)
3. Generate the expected FHIR query with proper clinical codes (LOINC, SNOMED CT, ICD-10, etc.)

The prompt should be realistic clinical language like:
- "Find all patients with a diagnosis of type 2 diabetes"
- "Get blood pressure measurements for adults over age 40"

DO NOT include codes in the prompt. The LLM being tested must determine correct codes.

The expected FHIR query should be technically correct with appropriate code systems."""

    # Build detailed context
    context_parts = []
    context_parts.append(f"Phenotype Name: {details.get('name', 'Unknown')}")
    context_parts.append(f"\nDescription:\n{description[:2000]}")
    
    # Add file contents (truncated if too long)
    if file_contents:
        context_parts.append("\n\nSupplementary Documents:")
        for filename, content in file_contents.items():
            # Limit each file to 3000 chars to stay within token limits
            truncated = content[:3000]
            if len(content) > 3000:
                truncated += "\n... (truncated)"
            context_parts.append(f"\n\n--- {filename} ---\n{truncated}")
    
    full_context = "".join(context_parts)
    
    user_prompt = f"""Analyze this phenotype and create a FHIR test case:

{full_context}

Provide a JSON response with:
{{
  "prompt": "Natural language description WITHOUT codes (1-3 sentences)",
  "description": "Longer description of what this test case evaluates",
  "expected_query": {{
    "resource_type": "ResourceType",
    "parameters": {{"param1": "value1"}},
    "url": "ResourceType?param1=value1"
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
    "tags": ["diabetes", "condition"]
  }}
}}

Important:
- Prompt must be in natural clinical language WITHOUT codes
- Expected query must have correct FHIR syntax with appropriate codes
- Use common clinical code systems for the condition/observation
- Focus on the most important criteria from the phenotype definition"""

    try:
        logger.info("  Calling Claude API...")
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        response_text = message.content[0].text
        
        # Extract JSON
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
        logger.info("  ✓ Successfully generated test case data")
        return result
        
    except Exception as e:
        logger.error(f"  ✗ Failed to generate with Claude: {e}")
        raise


def save_test_case(phenotype_id: str, phenotype_data: dict, test_case_data: dict, output_dir: Path):
    """Save test case as JSON file"""
    
    details = phenotype_data.get("details", {})
    
    test_case = {
        "id": f"phekb-{phenotype_id}",
        "source": "phekb",
        "source_id": phenotype_id,
        "name": details.get("name", phenotype_id),
        "description": test_case_data.get("description", ""),
        "prompt": test_case_data["prompt"],
        "metadata": test_case_data["metadata"],
        "expected_query": test_case_data["expected_query"],
        "test_data": {
            "resources": [],
            "expected_result_count": 0,
            "expected_resource_ids": []
        },
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    
    output_file = output_dir / f"phekb-{phenotype_id}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(test_case, f, indent=2)
    
    logger.info(f"  ✓ Saved to: {output_file}")


def main():
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment")
        logger.error("Add it to your .env file")
        sys.exit(1)
    
    # Initialize Claude client
    client = Anthropic(api_key=api_key)
    
    # Setup directories
    data_dir = Path("data/phekb-raw")
    output_dir = Path("test-cases/phekb")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all phenotype directories
    phenotype_dirs = [d for d in data_dir.iterdir() if d.is_dir() and d.name != "__pycache__"]
    
    logger.info("=" * 60)
    logger.info(f"Generating test cases for {len(phenotype_dirs)} phenotypes")
    logger.info("=" * 60)
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for i, phenotype_dir in enumerate(phenotype_dirs, 1):
        phenotype_id = phenotype_dir.name
        logger.info(f"\n[{i}/{len(phenotype_dirs)}] {phenotype_id}")
        
        # Check if already exists
        output_file = output_dir / f"phekb-{phenotype_id}.json"
        if output_file.exists():
            logger.info("  ⊘ Already exists, skipping")
            skipped_count += 1
            continue
        
        try:
            # Load all phenotype data
            logger.info("  Loading phenotype data...")
            phenotype_data = load_phenotype_data(phenotype_dir)
            
            # Generate test case with Claude
            test_case_data = generate_test_case_with_claude(phenotype_data, client)
            
            # Save test case
            save_test_case(phenotype_id, phenotype_data, test_case_data, output_dir)
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            error_count += 1
            continue
    
    logger.info("\n" + "=" * 60)
    logger.info("Test case generation complete!")
    logger.info("=" * 60)
    logger.info(f"Generated: {success_count}")
    logger.info(f"Skipped:   {skipped_count}")
    logger.info(f"Errors:    {error_count}")
    logger.info(f"\nTest cases saved to: {output_dir}")


if __name__ == "__main__":
    main()
