# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an evaluation framework for testing LLM capabilities in generating FHIR (Fast Healthcare Interoperability Resources) queries from natural language inputs. The project aims to benchmark how well different LLMs can:

- Understand healthcare data requirements expressed in natural language
- Generate syntactically correct FHIR queries
- Produce semantically accurate queries that retrieve the intended healthcare data
- Handle complex clinical scenarios and edge cases
- Properly use clinical code systems (LOINC, SNOMED CT, etc.)

## Architecture

### Technology Stack

- **Backend**: Python 3.10+ with FastAPI
- **Frontend**: TypeScript/React with Vite
- **CLI**: Python Click-based command-line tool
- **FHIR Server**: fhir-candle (lightweight .NET test server via Docker)
- **Storage**: JSON files for test cases (version-controllable)
- **LLM SDKs**: Anthropic SDK, OpenAI SDK

### Project Structure

```
llm-fhir-query-eval/
├── backend/               # Python FastAPI backend
│   ├── src/
│   │   ├── api/          # API routes and models
│   │   ├── evaluation/   # Evaluation engines (execution, semantic, LLM judge)
│   │   ├── llm/          # LLM provider integrations
│   │   ├── fhir/         # FHIR server management and client
│   │   ├── scraper/      # PheKB phenotype scraper
│   │   └── utils/        # Configuration and utilities
│   └── tests/            # Backend tests
├── frontend/             # React/TypeScript frontend
│   └── src/
│       ├── components/   # React components
│       ├── pages/        # Page components
│       └── api/          # API client
├── cli/                  # Command-line interface
│   └── fhir_eval/
│       └── commands/     # CLI commands (run, scrape, report)
├── test-cases/           # Test case JSON files
│   ├── manual/           # Manually curated test cases
│   └── phekb/            # Auto-generated from PheKB
├── data/                 # Test FHIR resources and code systems
└── docs/                 # Documentation
```

## Development Commands

### Initial Setup

```bash
# Clone repository (if not already done)
git clone <repo-url>
cd llm-fhir-query-eval

# Copy environment file and configure
cp .env.example .env
# Edit .env and add your API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY)
```

### Backend Development

```bash
cd backend

# Install dependencies with Poetry
poetry install

# Run backend server (development mode)
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
poetry run pytest

# Format code
poetry run black src tests
poetry run ruff check src tests
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run linter
npm run lint
```

### CLI Tool

```bash
cd cli

# Install CLI in editable mode
pip install -e .

# Use CLI commands
fhir-eval --help
fhir-eval run --help
fhir-eval scrape --help
fhir-eval report --help
```

### Docker (Full Stack)

```bash
# Start all services (fhir-candle, backend, frontend)
docker-compose up

# Start only FHIR server
docker-compose up -d fhir-candle

# Stop all services
docker-compose down
```

### FHIR Server Access

- **fhir-candle endpoints**:
  - R4: http://localhost:5826/r4
  - R4B: http://localhost:5826/r4b
  - R5: http://localhost:5826/r5
  - Metadata: http://localhost:5826/r4/metadata

## FHIR Context

FHIR is a standard for exchanging healthcare information electronically. When working with FHIR queries in this project:

- **Resource Types**: Patient, Observation, Condition, Medication, Encounter, etc.
- **Query Format**: `GET /[ResourceType]?[parameter]=[value]&[parameter]=[value]`
- **Common Parameters**:
  - `_id`: Resource ID
  - `_count`: Number of results
  - `_sort`: Sort order
  - Resource-specific parameters (e.g., `code` for Observation, `family` for Patient)
- **Code Systems**:
  - LOINC for lab observations
  - SNOMED CT for clinical findings
  - Format: `code=http://loinc.org|2339-0`

## Test Case Format

Test cases are stored as JSON files in `test-cases/manual/` or `test-cases/phekb/`. Each test case includes:

- **prompt**: Natural language description of the query
- **expected_query**: The correct FHIR query
- **test_data**: FHIR resources to load for testing
- **metadata**: Implementation guide, code systems, complexity, tags

Example test case: `test-cases/manual/diabetes-glucose-observations.json`

## Evaluation Methods

The framework uses three evaluation strategies:

1. **Execution-based**: Compare results from running expected vs generated queries against test FHIR data
2. **Semantic parsing**: Parse and compare query semantics (resource type, parameters)
3. **LLM judge**: Use an LLM (Claude) to evaluate if queries are semantically equivalent
4. **Code system validation**: Verify correct use of code systems and codes

## API Endpoints

### Test Cases

- `GET /api/test-cases` - List all test cases
- `GET /api/test-cases/{id}` - Get specific test case
- `POST /api/test-cases` - Create new test case
- `PUT /api/test-cases/{id}` - Update test case
- `DELETE /api/test-cases/{id}` - Delete test case

### Health Check

- `GET /api/health` - API health check
- `GET /` - API information

## Common Tasks

### Adding a New Test Case

1. Create JSON file in `test-cases/manual/`
2. Use the test case schema (see existing examples)
3. Include prompt, expected query, test data references, and metadata
4. API will automatically pick up new test cases

### Running Evaluations

Via API:
```bash
POST /api/evaluations
{
  "test_case_ids": ["test-case-id"],
  "llm_provider": "anthropic",
  "model": "claude-sonnet-4-5"
}
```

Via CLI (when implemented):
```bash
fhir-eval run --test-case diabetes-glucose-observations --provider anthropic
```

### Code System References

When creating test cases with clinical codes:
- Always include full system URI (e.g., `http://loinc.org`)
- Include code and display name
- Reference implementation guides when applicable (e.g., US Core)

### PheKB Scraping

The framework can automatically generate test cases from PheKB phenotypes:

```bash
# List available phenotypes
fhir-eval scrape --list

# Generate test case from specific phenotype
fhir-eval scrape --id diabetes-mellitus-type-2

# Generate first 10 test cases
fhir-eval scrape --all --limit 10
```

**Important Design Principle**:
- **Prompts are code-free**: Generated prompts use natural clinical language WITHOUT codes
- **Expected queries have codes**: The expected FHIR queries contain proper clinical codes
- **Why?**: Part of the evaluation is testing whether LLMs can determine appropriate codes
- LLMs should either know the codes or use MCP servers to look them up

Example:
- Prompt: "Find all patients with a diagnosis of type 2 diabetes"
- Expected query: `Condition?code=http://hl7.org/fhir/sid/icd-10-cm|E11`

See [docs/phekb-scraping.md](docs/phekb-scraping.md) for details.

## Notes for Claude Code

- Test cases are file-based (JSON) for easy version control and manual curation
- The fhir-candle server runs in Docker and provides in-memory FHIR storage
- Backend uses Pydantic for data validation and FastAPI for routing
- Frontend communicates with backend via REST API
- All LLM integrations go through provider abstraction in `backend/src/llm/`
