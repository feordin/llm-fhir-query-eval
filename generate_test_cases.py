"""
Pass 2: Test Case Generation from PheKB Phenotypes

This script:
1. Loads each phenotype from data/phekb-raw/
2. Uses document_analysis.json (from Pass 1) if available
3. Uses Claude to generate FHIR test cases with code source tracking
4. Saves to test-cases/phekb/

Codes are tagged with source:
- "document": Code was found in phenotype documents
- "inferred": Code was determined by Claude based on context
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
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
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

    # Load document_analysis.json if available (from Pass 1)
    analysis_file = phenotype_dir / "document_analysis.json"
    if analysis_file.exists():
        with open(analysis_file, "r", encoding="utf-8") as f:
            data["document_analysis"] = json.load(f)
        logger.info("  Loaded document_analysis.json")
    else:
        data["document_analysis"] = None
        logger.info("  No document_analysis.json - will extract codes directly")

    # Extract text from PDFs and Word docs (for additional context)
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


def normalize_code_system(system: str) -> str:
    """Normalize code system name to FHIR URI"""
    system_map = {
        "ICD-9-CM": "http://hl7.org/fhir/sid/icd-9-cm",
        "ICD-9": "http://hl7.org/fhir/sid/icd-9-cm",
        "ICD-10-CM": "http://hl7.org/fhir/sid/icd-10-cm",
        "ICD-10": "http://hl7.org/fhir/sid/icd-10-cm",
        "LOINC": "http://loinc.org",
        "SNOMED CT": "http://snomed.info/sct",
        "SNOMED": "http://snomed.info/sct",
        "RxNorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
        "CPT": "http://www.ama-assn.org/go/cpt",
    }
    # Return as-is if already a URI
    if system.startswith("http"):
        return system
    return system_map.get(system, system)


def build_document_codes_lookup(document_analysis: dict) -> dict:
    """Build a lookup dict for codes found in documents"""
    if not document_analysis:
        return {}

    lookup = {}
    for code_entry in document_analysis.get("extracted_codes", []):
        system = normalize_code_system(code_entry.get("system", ""))
        code = code_entry.get("code", "")
        # Key is system|code for matching
        key = f"{system}|{code}".lower()
        lookup[key] = {
            "found_in": code_entry.get("found_in", ""),
            "context": code_entry.get("context", ""),
            "display": code_entry.get("display", "")
        }
    return lookup


def generate_test_case_with_claude(phenotype_data: dict, client: Anthropic) -> dict:
    """Use Claude to generate test case from phenotype data"""

    details = phenotype_data.get("details", {})
    description = phenotype_data.get("description", "")
    file_contents = phenotype_data.get("file_contents", {})
    document_analysis = phenotype_data.get("document_analysis")

    # Build comprehensive prompt
    system_prompt = """You are a clinical informatics expert creating FHIR query test cases from phenotype definitions.

Your task:
1. Analyze the phenotype definition, description, and any supplementary documents
2. Create a natural language prompt that a clinician would write (WITHOUT codes)
3. Generate the expected FHIR query with proper clinical codes (LOINC, SNOMED CT, ICD-10, etc.)
4. Track whether each code comes from the documents or is inferred

The prompt should be realistic clinical language like:
- "Find all patients with a diagnosis of type 2 diabetes"
- "Get blood pressure measurements for adults over age 40"

DO NOT include codes in the prompt. The LLM being tested must determine correct codes.

The expected FHIR query should be technically correct with appropriate code systems.

IMPORTANT for code sources:
- If a code was found in the phenotype documents, set source to "document"
- If you determine a code based on clinical knowledge (not in documents), set source to "inferred"

Implementation Guide:
- Set to "US Core 6.1.0" ONLY for phenotypes that align well with US Core profiles:
  - Simple vital signs (blood pressure, BMI, height, weight)
  - Basic lab observations with LOINC codes
  - Standard conditions, medications, allergies
- Set to null for:
  - Complex multi-query phenotypes
  - Research-specific phenotypes
  - Phenotypes requiring multiple resource types
  - Non-standard clinical patterns"""

    # Build context parts
    context_parts = []
    context_parts.append(f"Phenotype Name: {details.get('name', 'Unknown')}")
    context_parts.append(f"\nDescription:\n{description[:2000]}")

    # Include document analysis if available
    if document_analysis:
        context_parts.append("\n\n=== PRE-EXTRACTED CODES FROM DOCUMENTS ===")
        context_parts.append("These codes were found in the phenotype documents:")
        for code in document_analysis.get("extracted_codes", [])[:30]:  # Limit to 30
            context_parts.append(
                f"- {code.get('system')}: {code.get('code')} ({code.get('display', 'N/A')}) "
                f"[from: {code.get('found_in', 'unknown')}]"
            )

        if document_analysis.get("clinical_criteria"):
            context_parts.append("\n=== CLINICAL CRITERIA ===")
            for criteria in document_analysis.get("clinical_criteria", []):
                context_parts.append(f"- {criteria}")

        if document_analysis.get("algorithm_summary"):
            context_parts.append(f"\n=== ALGORITHM SUMMARY ===\n{document_analysis['algorithm_summary']}")

    # Add file contents (truncated if too long)
    if file_contents:
        context_parts.append("\n\n=== DOCUMENT EXCERPTS ===")
        for filename, content in file_contents.items():
            # Limit each file to 2000 chars to stay within token limits
            truncated = content[:2000]
            if len(content) > 2000:
                truncated += "\n... (truncated)"
            context_parts.append(f"\n--- {filename} ---\n{truncated}")

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
    "implementation_guide": null,  // Set to "US Core 6.1.0" only if appropriate, otherwise null
    "code_systems": ["LOINC", "SNOMED CT"],
    "required_codes": [
      {{
        "system": "http://loinc.org",
        "code": "12345-6",
        "display": "Code display name",
        "source": "document"  // "document" if from documents above, "inferred" if you determined it
      }}
    ],
    "complexity": "medium",
    "tags": ["diabetes", "condition"]
  }}
}}

Important:
- Prompt must be in natural clinical language WITHOUT codes
- Expected query must have correct FHIR syntax with appropriate codes
- Mark each code's source as "document" (found in documents) or "inferred" (you determined it)
- PREFER codes from the documents when available
- Set implementation_guide to null unless this is a simple US Core-aligned phenotype"""

    try:
        logger.info("  Calling Claude API...")
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
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
        logger.info("  Successfully generated test case data")
        return result

    except Exception as e:
        logger.error(f"  Failed to generate with Claude: {e}")
        raise


def verify_code_sources(test_case_data: dict, document_analysis: dict) -> dict:
    """Verify and correct code sources based on document analysis"""
    if not document_analysis:
        return test_case_data

    doc_codes_lookup = build_document_codes_lookup(document_analysis)

    required_codes = test_case_data.get("metadata", {}).get("required_codes", [])
    document_count = 0
    inferred_count = 0

    for code in required_codes:
        system = code.get("system", "")
        code_value = code.get("code", "")
        key = f"{system}|{code_value}".lower()

        # Check if this code was found in documents
        if key in doc_codes_lookup:
            code["source"] = "document"
            document_count += 1
        else:
            code["source"] = "inferred"
            inferred_count += 1

    logger.info(f"  Code sources: {document_count} from documents, {inferred_count} inferred")
    return test_case_data


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

    logger.info(f"  Saved to: {output_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate test cases from PheKB phenotypes")
    parser.add_argument("--limit", type=int, help="Limit number of phenotypes to process")
    parser.add_argument("--force", action="store_true", help="Regenerate even if test case exists")
    parser.add_argument("--phenotype", type=str, help="Process specific phenotype ID only")
    args = parser.parse_args()

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

    # Get phenotype directories
    if args.phenotype:
        phenotype_dirs = [data_dir / args.phenotype]
        if not phenotype_dirs[0].exists():
            logger.error(f"Phenotype directory not found: {args.phenotype}")
            sys.exit(1)
    else:
        phenotype_dirs = [
            d for d in data_dir.iterdir()
            if d.is_dir() and d.name != "__pycache__"
        ]

    if args.limit:
        phenotype_dirs = phenotype_dirs[:args.limit]

    logger.info("=" * 60)
    logger.info(f"Test Case Generation - Pass 2")
    logger.info(f"Processing {len(phenotype_dirs)} phenotypes")
    logger.info("=" * 60)

    success_count = 0
    error_count = 0
    skipped_count = 0

    for i, phenotype_dir in enumerate(phenotype_dirs, 1):
        phenotype_id = phenotype_dir.name
        logger.info(f"\n[{i}/{len(phenotype_dirs)}] {phenotype_id}")

        # Check if already exists
        output_file = output_dir / f"phekb-{phenotype_id}.json"
        if output_file.exists() and not args.force:
            logger.info("  Skipped - already exists (use --force to regenerate)")
            skipped_count += 1
            continue

        try:
            # Load all phenotype data
            logger.info("  Loading phenotype data...")
            phenotype_data = load_phenotype_data(phenotype_dir)

            # Generate test case with Claude
            test_case_data = generate_test_case_with_claude(phenotype_data, client)

            # Verify and correct code sources
            document_analysis = phenotype_data.get("document_analysis")
            test_case_data = verify_code_sources(test_case_data, document_analysis)

            # Save test case
            save_test_case(phenotype_id, phenotype_data, test_case_data, output_dir)

            success_count += 1

        except Exception as e:
            logger.error(f"  Error: {e}")
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
