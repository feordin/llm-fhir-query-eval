# LLM FHIR Query Evaluation

A comprehensive framework for evaluating Large Language Model (LLM) performance in generating FHIR (Fast Healthcare Interoperability Resources) queries from natural language descriptions.

## Overview

This project provides a systematic approach to assess how well different LLMs can:
- Understand healthcare data requirements expressed in natural language
- Generate syntactically correct FHIR queries
- Produce semantically accurate queries that retrieve the intended healthcare data
- Use proper clinical code systems (LOINC, SNOMED CT, etc.)
- Handle complex clinical scenarios and edge cases

## Key Features

- **Multiple Evaluation Strategies**:
  - Execution-based: Compare results from running queries against test FHIR data
  - Semantic parsing: Compare query structure and parameters
  - LLM judge: Use an LLM to evaluate semantic equivalence
  - Code system validation: Verify correct code system usage

- **Test Case Management**:
  - JSON-based test cases (version-controllable and human-readable)
  - Manual curation and automated generation from PheKB phenotypes
  - Support for implementation guide references

- **Multi-Interface**:
  - Web UI for interactive test management and evaluation
  - REST API for programmatic access
  - CLI for automation and CI/CD pipelines

- **LLM Provider Support**:
  - Anthropic (Claude)
  - OpenAI (GPT-4, etc.)
  - Local models (via Ollama)
  - Optional MCP server integration for enhanced context

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Web UI (React/TS)                         │
│  Test Case Browser | Evaluation Runner | Results Dashboard │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────────────────┐
│                 Backend API (FastAPI)                       │
│  Test Management | LLM Orchestration | Evaluation Engines  │
└─────────────────────┬───────────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
┌────────▼──────┐ ┌──▼────────┐ ┌─▼──────────────┐
│ Test Cases    │ │ LLM       │ │ FHIR Server    │
│ (JSON)        │ │ Providers │ │ (fhir-candle)  │
└───────────────┘ └───────────┘ └────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker (for fhir-candle FHIR server)
- Poetry (for Python dependency management)

### Installation

1. Clone the repository:
```bash
git clone <repo-url>
cd llm-fhir-query-eval
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your API keys:
# ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
```

3. Start the FHIR server:
```bash
docker-compose up -d fhir-candle
```

4. Set up the backend:
```bash
cd backend
poetry install
poetry run uvicorn src.api.main:app --reload
```

5. Set up the frontend (in a new terminal):
```bash
cd frontend
npm install
npm run dev
```

6. Access the application:
- Web UI: http://localhost:3000
- API docs: http://localhost:8000/docs
- FHIR server: http://localhost:5826/r4/metadata

### Using Docker Compose (All Services)

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## Usage

### Web UI

1. Navigate to http://localhost:3000
2. Browse test cases
3. Run evaluations with different LLM providers
4. View detailed results and comparisons

### API

```bash
# List test cases
curl http://localhost:8000/api/test-cases

# Get specific test case
curl http://localhost:8000/api/test-cases/diabetes-glucose-observations

# Create test case
curl -X POST http://localhost:8000/api/test-cases \
  -H "Content-Type: application/json" \
  -d @test-case.json
```

### CLI

```bash
# Install CLI
cd cli
pip install -e .

# List available PheKB phenotypes
fhir-eval scrape --list

# Generate test case from PheKB phenotype
fhir-eval scrape --id diabetes-mellitus-type-2

# Generate multiple test cases (first 10 phenotypes)
fhir-eval scrape --all --limit 10

# Run evaluations (coming soon)
fhir-eval run --test-case diabetes-glucose-observations --provider anthropic

# Generate report (coming soon)
fhir-eval report --format markdown --output results.md
```

### Generating Test Cases from PheKB

The framework can automatically generate test cases from [PheKB](https://phekb.org) phenotypes:

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY=your_key_here

# Generate a test case from a phenotype
fhir-eval scrape --id phenotype-name
```

**Important**: Generated prompts use natural clinical language WITHOUT codes. This is intentional - the evaluation tests whether LLMs can determine the appropriate clinical codes (LOINC, SNOMED CT, etc.) from context or by using MCP servers.

Example:
- **Prompt**: "Find all patients with a diagnosis of type 2 diabetes"
- **Expected Query**: `Condition?code=http://hl7.org/fhir/sid/icd-10-cm|E11`

The LLM being evaluated must bridge the gap from natural language to properly coded FHIR queries.

## Test Case Format

Test cases are JSON files stored in `test-cases/manual/` or `test-cases/phekb/`:

```json
{
  "id": "diabetes-glucose-observations",
  "name": "Diabetes Glucose Observations",
  "prompt": "Find all blood glucose observations from 2020 onwards...",
  "expected_query": {
    "resource_type": "Observation",
    "parameters": {
      "code": "http://loinc.org|2339-0",
      "date": "ge2020-01-01"
    }
  },
  "metadata": {
    "implementation_guide": "US Core 5.0.0",
    "code_systems": ["LOINC"],
    "required_codes": [...]
  },
  "test_data": {
    "resources": ["data/fhir-resources/observations.json"],
    "expected_result_count": 15
  }
}
```

See `test-cases/manual/` for complete examples.

## Development

### Backend

```bash
cd backend
poetry install
poetry run uvicorn src.api.main:app --reload

# Run tests
poetry run pytest

# Format code
poetry run black src tests
poetry run ruff check src tests
```

### Frontend

```bash
cd frontend
npm install
npm run dev

# Build
npm run build

# Lint
npm run lint
```

## Project Status

### Phase 1: Core Infrastructure ✅ (Completed)
- Project setup (Python, TypeScript, Docker)
- Test case management API
- Basic FHIR server integration (fhir-candle)
- Example test cases with code-free prompts

### Phase 4: PheKB Scraper ✅ (Completed)
- Web scraper for phekb.org phenotypes
- Claude-based prompt extraction (natural language, no codes)
- Expected FHIR query generation (with proper codes)
- CLI commands for scraping and test case generation
- Automated test case creation from 100+ phenotypes

### Phase 2-3, 5-7: In Progress
- LLM provider integration (Anthropic, OpenAI, local)
- Evaluation engines (execution, semantic, LLM judge, code validation)
- Full web UI implementation
- CLI evaluation commands
- Testing and documentation

See [CLAUDE.md](CLAUDE.md) for detailed architecture and development guide.

## Contributing

Contributions are welcome! Areas of focus:

- Adding more test cases (manual or from clinical databases)
- Improving evaluation algorithms
- Supporting additional LLM providers
- Enhancing the web UI
- Documentation improvements

## About FHIR

FHIR (Fast Healthcare Interoperability Resources) is a standard for exchanging healthcare information electronically. It defines:

- **Resources**: Patient, Observation, Condition, Medication, etc.
- **RESTful API**: Standard HTTP operations for CRUD
- **Search parameters**: Flexible querying capabilities
- **Code systems**: LOINC, SNOMED CT, RxNorm, ICD-10, etc.

Learn more at [fhir.org](https://www.fhir.org)

## License

[Add license information]

## Acknowledgments

- PheKB for phenotype definitions
- FHIR community for the fhir-candle test server
- Anthropic and OpenAI for LLM APIs
