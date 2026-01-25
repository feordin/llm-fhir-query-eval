# PheKB Scraping and Test Case Generation

This document describes how the framework collects phenotype data from PheKB.

## Overview

The PheKB scraper uses a **two-stage process** to collect all phenotype data locally:

**Stage 1: List URLs** (Run once)
- Visit phekb.org/phenotypes
- Handle pagination to get ALL phenotypes (100+)
- Save complete list to `data/phekb-raw/phenotypes.json`
- NO API credits required!

**Stage 2: Download Details** (Run for each phenotype)
- Visit each phenotype page
- Extract description paragraph
- Download PDF and Word documents (skip Excel)
- Save to `data/phekb-raw/[phenotype-id]/`
- NO API credits required!

**Later: Process with Claude** (Optional, requires API credits)
- Use Claude to analyze downloaded data
- Generate natural language prompts (without codes)
- Create expected FHIR queries (with proper codes)

## Key Design Principle

**Prompts are code-free**: The generated prompts are written in natural clinical language without any code systems or codes. This is intentional because part of the evaluation is testing whether LLMs can:

- Determine the appropriate code systems (LOINC, SNOMED CT, ICD-10, etc.)
- Select the correct codes for clinical concepts
- Use MCP servers (if available) to look up proper codes

Example:
- ✓ Good prompt: "Find all patients with a diagnosis of type 2 diabetes"
- ✗ Bad prompt: "Find all patients with ICD-10 code E11 (Type 2 diabetes mellitus)"

The expected FHIR query, however, contains the proper codes that the LLM should generate.

## Components

### 1. PheKBScraper (`backend/src/scraper/phekb.py`)

Handles web scraping of phekb.org:

```python
scraper = PheKBScraper()

# List all phenotypes
phenotypes = scraper.list_phenotypes()

# Get details for a specific phenotype
details = scraper.get_phenotype_details(phenotype)

# Download associated files
scraper.download_file(file_url, output_path)
```

Features:
- Respectful rate limiting (1 second delay between requests)
- Downloads associated documentation files
- Extracts description, category, and other metadata

### 2. PhenotypeExtractor (`backend/src/scraper/extractor.py`)

Uses Claude to analyze phenotypes and extract test case data:

```python
extractor = PhenotypeExtractor(api_key=anthropic_api_key)

# Extract test case data
test_case_data = extractor.extract_test_case_data(phenotype_details)

# Enhance with file contents
test_case_data = extractor.enhance_with_files(
    phenotype_details,
    file_contents
)
```

Claude is instructed to:
- Create natural language prompts without codes
- Generate FHIR queries with proper clinical codes
- Identify appropriate implementation guides
- Assign complexity levels and tags

### 3. TestCaseGenerator (`backend/src/scraper/generator.py`)

Orchestrates the entire process:

```python
generator = TestCaseGenerator(anthropic_api_key=api_key)

# Generate from specific phenotype
test_case = generator.generate_from_phenotype_id("diabetes-mellitus-type-2")

# Generate from all phenotypes
test_cases = generator.generate_from_all_phenotypes(
    limit=10,
    skip_existing=True
)
```

## Usage

### Stage 1: Fetch All URLs

```bash
# Run this ONCE to get the complete list
fhir-eval scrape list-urls
```

This will:
- Load phekb.org/phenotypes
- Click through pagination to get ALL phenotypes
- Save to `data/phekb-raw/phenotypes.json`
- Takes a few minutes

### Stage 2: Download Details

```bash
# Download first 5 phenotypes (test)
fhir-eval scrape download --limit 5

# Download specific phenotype
fhir-eval scrape download --id 123

# Download ALL phenotypes (takes hours!)
fhir-eval scrape download
```

### Check Status

```bash
# See what's been downloaded
fhir-eval scrape status
```

### No API Credits Needed!

Both stages use only web scraping - **no Anthropic API credits required**!

### Programmatically

```python
from src.scraper.generator import TestCaseGenerator

generator = TestCaseGenerator(
    anthropic_api_key="your_key",
    output_dir="test-cases/phekb"
)

# Generate single test case
test_case = generator.generate_from_phenotype_id("phenotype-id")

# Process multiple phenotypes
test_cases = generator.generate_from_all_phenotypes(limit=5)
```

## Output

Generated test cases are saved to `test-cases/phekb/` with the format:

```json
{
  "id": "phekb-diabetes-mellitus-type-2",
  "source": "phekb",
  "source_id": "diabetes-mellitus-type-2",
  "name": "Type 2 Diabetes Mellitus",
  "description": "Phenotype for identifying patients with type 2 diabetes",
  "prompt": "Find all patients diagnosed with type 2 diabetes mellitus",
  "metadata": {
    "implementation_guide": "US Core 5.0.0",
    "code_systems": ["ICD-10-CM", "SNOMED CT"],
    "required_codes": [
      {
        "system": "http://hl7.org/fhir/sid/icd-10-cm",
        "code": "E11",
        "display": "Type 2 diabetes mellitus"
      }
    ],
    "complexity": "medium",
    "tags": ["diabetes", "endocrine", "chronic-condition"]
  },
  "expected_query": {
    "resource_type": "Condition",
    "parameters": {
      "code": "http://hl7.org/fhir/sid/icd-10-cm|E11"
    },
    "url": "Condition?code=http://hl7.org/fhir/sid/icd-10-cm|E11"
  },
  "test_data": {
    "resources": [],
    "expected_result_count": 0,
    "expected_resource_ids": []
  }
}
```

Note: The `test_data` section is initially empty. Actual FHIR test resources would need to be created separately.

## Rate Limiting and Ethics

The scraper is designed to be respectful:

- 1 second delay between requests (configurable)
- User-Agent identifies the tool as a research project
- Downloads only publicly available phenotypes
- Skips existing test cases by default

## Limitations

1. **Test Data**: The scraper generates test case definitions but not actual FHIR test resources. Those need to be created separately.

2. **Code Accuracy**: Claude makes best-effort attempts to select appropriate codes, but they should be reviewed by clinical informatics experts.

3. **Phenotype Complexity**: Some phenotypes may be too complex to represent as a single FHIR query. These may need manual curation.

4. **Web Scraping Fragility**: The scraper depends on PheKB's HTML structure, which may change. Selectors may need updates.

## Manual Curation

Generated test cases should be reviewed and curated:

1. **Review prompts**: Ensure they're realistic clinical language
2. **Validate codes**: Confirm codes are appropriate for the clinical concept
3. **Add test data**: Create FHIR resources for testing
4. **Set expected results**: Define expected result counts and IDs
5. **Test queries**: Verify queries work against FHIR server

## Future Enhancements

- Automatic FHIR test resource generation
- Integration with terminology services for code validation
- Support for complex phenotypes requiring multiple queries
- Batch processing with progress persistence
- PheKB API integration (if/when available)
