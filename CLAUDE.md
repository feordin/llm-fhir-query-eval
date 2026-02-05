# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Evaluation framework for testing LLM capabilities in generating FHIR queries from natural language. Benchmarks how well LLMs can translate clinical requirements into syntactically and semantically correct FHIR queries with proper clinical code systems (LOINC, SNOMED CT, ICD-10, etc.).

## Development Commands

### Backend (Python/FastAPI)

```bash
cd backend
poetry install                    # Install dependencies
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000  # Dev server
poetry run pytest                 # Run all tests
poetry run pytest tests/test_evaluation/test_semantic.py -k test_parse_query  # Single test
poetry run black src tests        # Format code
poetry run ruff check src tests   # Lint
```

### Frontend (React/TypeScript/Vite)

```bash
cd frontend
npm install      # Install dependencies
npm run dev      # Dev server (localhost:3000)
npm run build    # Production build
npm run lint     # ESLint
```

### CLI Tool

```bash
cd cli
pip install -e .         # Install in editable mode
fhir-eval --help         # Show commands
```

### Docker

```bash
docker-compose up -d fhir-candle   # Start FHIR server only
docker-compose up                   # Start all services
docker-compose down                 # Stop all services
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Web UI (React/TS)                         │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API (port 8000)
┌─────────────────────▼───────────────────────────────────────┐
│                 Backend API (FastAPI)                       │
│  Test Management | LLM Orchestration | Evaluation Engines  │
└─────────────────────┬───────────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
┌────────▼──────┐ ┌──▼────────┐ ┌─▼──────────────┐
│ Test Cases    │ │ LLM       │ │ FHIR Server    │
│ (JSON files)  │ │ Providers │ │ (fhir-candle)  │
└───────────────┘ └───────────┘ └────────────────┘
```

### Key Components

- **backend/src/api/**: FastAPI routes and Pydantic models. Main app in `main.py`
- **backend/src/evaluation/**: Evaluation engines (execution-based, semantic parsing, LLM judge)
- **backend/src/llm/**: LLM provider abstractions (Anthropic, OpenAI)
- **backend/src/scraper/**: PheKB phenotype scraper and test case generator
  - `phekb.py`: Web scraper using Selenium
  - `extractor.py`: Claude-based prompt extraction
  - `generator.py`: Orchestrates scraping → extraction → test case creation
- **cli/fhir_eval/commands/**: CLI commands (scrape, run, report)
- **test-cases/**: JSON test case files
  - `manual/`: Hand-curated test cases
  - `phekb/`: Auto-generated from PheKB phenotypes

### Data Flow for Evaluation

1. Load test case JSON (prompt + expected query)
2. Send prompt to LLM provider → get generated FHIR query
3. Run both queries against fhir-candle (localhost:5826/r4)
4. Compare results using evaluation engines
5. Generate scores/report

## FHIR Query Format

```
GET /[ResourceType]?[parameter]=[value]&[parameter]=[value]
```

Code system format: `code=http://loinc.org|2339-0` (system|code)

Common code systems:
- LOINC (`http://loinc.org`) - Lab observations
- SNOMED CT (`http://snomed.info/sct`) - Clinical findings
- ICD-10-CM (`http://hl7.org/fhir/sid/icd-10-cm`) - Diagnoses
- RxNorm (`http://www.nlm.nih.gov/research/umls/rxnorm`) - Medications

## Test Case Design Principle

**Prompts are code-free**: Test case prompts use natural clinical language WITHOUT codes. The expected FHIR query contains proper codes. This tests whether LLMs can determine appropriate clinical codes from context.

Example:
- Prompt: "Find all patients with a diagnosis of type 2 diabetes"
- Expected: `Condition?code=http://hl7.org/fhir/sid/icd-10-cm|E11`

## PheKB Scraping Workflow

Three-stage process to generate test cases from phekb.org phenotypes:

```bash
# Stage 1: Fetch all phenotype URLs (run once)
fhir-eval scrape list-urls

# Stage 2: Download details and files (no API credits)
fhir-eval scrape download --limit 10

# Stage 3: Generate test cases with Claude (requires ANTHROPIC_API_KEY)
fhir-eval scrape generate --limit 10
```

Data is saved to `data/phekb-raw/[phenotype-id]/` and test cases to `test-cases/phekb/`.

## Environment Variables

Required in `.env`:
- `ANTHROPIC_API_KEY` - For Claude API (test case generation, LLM judge)
- `OPENAI_API_KEY` - For OpenAI models (optional)
- `FHIR_SERVER_URL` - Defaults to `http://localhost:5826` (fhir-candle)

## FHIR Server (fhir-candle)

Lightweight .NET FHIR server for testing. Endpoints:
- R4: http://localhost:5826/r4
- Metadata: http://localhost:5826/r4/metadata

In-memory storage - data resets on restart.

## Custom Skills

### /synthea - Test Data Generation

Generate synthetic FHIR test data from PheKB phenotypes using Synthea.

```bash
/synthea create-module <phenotype>  # Create Synthea module from phenotype data
/synthea generate <phenotype>       # Run Synthea to generate FHIR data
/synthea load <phenotype>           # Load generated data to FHIR server
/synthea full <phenotype>           # Full pipeline: create + generate + load
/synthea status                     # Show status of all phenotypes
/synthea list                       # List phenotypes with modules ready
/synthea batch <phenotypes...>      # Process multiple phenotypes
```

**Examples:**
```bash
/synthea create-module asthma
/synthea full type-2-diabetes
/synthea batch asthma,heart-failure,copd
```

See `.claude/skills/synthea.md` for detailed instructions.

## Synthea Test Data

Custom Synthea modules are in `synthea/modules/custom/`. Each phenotype has:
- `phekb_<phenotype>.json` - Positive cases (patients matching phenotype)
- `phekb_<phenotype>_control.json` - Control cases (patients NOT matching)

Generated data goes to `synthea/output/<phenotype>/positive/` and `synthea/output/<phenotype>/control/`.

To run Synthea manually:
```bash
python synthea/generate_test_data.py --phenotype <name> --patients 20 --controls 20
```

### Synthea Bash Environment Notes

Claude Code runs in **git bash**, not cmd.exe. Three known issues:
1. **`.bat` files don't run** - Use `./gradlew` directly instead of `run_synthea.bat`
2. **JAVA_HOME not set** - Export before running: `export JAVA_HOME="/c/Program Files/Eclipse Adoptium/jdk-17.0.18.8-hotspot"`
3. **Backslash paths break Gradle** - Always use forward slashes (`C:/repos/...` not `C:\repos\...`)

The Python helper script (`synthea/generate_test_data.py`) handles all three automatically.
