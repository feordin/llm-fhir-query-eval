---
name: fhir-query-agent
description: Generate accurate FHIR queries from natural language using an agentic workflow with UMLS code lookup and FHIR server introspection.
allowed-tools: Read, Bash, Glob, Grep
---

# FHIR Query Agent Skill

Use this when the user needs to generate FHIR REST API queries from clinical descriptions.

## Usage

```
/fhir-query-agent <natural language query>
```

## What It Does

This skill runs a standalone FHIR query agent that:

1. Parses the clinical request to identify needed FHIR resource types and clinical concepts
2. Looks up clinical codes via UMLS (SNOMED CT, LOINC, RxNorm, ICD-10)
3. Samples the FHIR server to see what code systems are actually in the data
4. Crosswalks codes if the server uses a different system than expected
5. Tests the query against the server
6. Returns working FHIR search URLs

## How to Run

```bash
# Interactive mode
cd fhir-query-agent
pip install -e .
fhir-query-agent --fhir-url http://localhost:8080/fhir --umls-key $UMLS_API_KEY

# Single query
fhir-query-agent --fhir-url http://localhost:8080/fhir -q "Find patients with type 2 diabetes on metformin"
```

## Example

```
/fhir-query-agent Find all patients diagnosed with type 2 diabetes who are on metformin
```

Expected output: Two FHIR queries - one for Condition (diabetes diagnosis) and one for MedicationRequest (metformin), potentially linked via patient reference.

## Configuration

- `FHIR_SERVER_URL` - FHIR server base URL (or use --fhir-url)
- `UMLS_API_KEY` - NIH UMLS API key for code lookups (or use --umls-key)
- `OLLAMA_HOST` - Ollama server if not localhost (or use --ollama-host)
