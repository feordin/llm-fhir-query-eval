---
name: fhir_server_introspection
description: Teaches the LLM how to introspect a FHIR server's capabilities, loaded profiles, and valueset bindings to construct accurate queries. Used in agentic evaluation mode where the LLM has tool access.
allowed-tools: Read, Bash, Glob, Grep, mcp__nih-umls__search_umls, mcp__nih-umls__get_concept, mcp__nih-umls__crosswalk_codes, mcp__nih-umls__get_source_concept
---

# FHIR Server Introspection Skill

## Purpose

This skill teaches an LLM how an experienced FHIR developer approaches querying a new server. Instead of guessing codes and parameters, the LLM follows a systematic workflow:

1. **Introspect** the server's capabilities
2. **Identify** which profiles and implementation guides are in use
3. **Look up** valueset bindings from those profiles
4. **Verify** codes using UMLS
5. **Construct** queries using the right codes for THIS server

## The Problem This Solves

In "closed book" evaluation, LLMs often:
- Hallucinate clinical codes (wrong LOINC, fake RxNorm codes)
- Use the wrong code system (ICD-10 when the server only has SNOMED)
- Guess at search parameter names
- Don't know what the server actually supports

An experienced FHIR developer never guesses — they check the server first.

## Evaluation Tiers

This skill enables **Tier 3** evaluation:

| Tier | LLM Has Access To | What It Tests |
|------|-------------------|---------------|
| 1. Closed Book | Just the prompt | Raw FHIR + clinical knowledge |
| 2. Tool-Assisted | + UMLS MCP + server metadata | Reasoning + tool use |
| **3. Skill-Guided** | **+ IG profiles + valueset bindings + this skill** | **Can it follow a methodology?** |

---

## Workflow: How to Introspect a FHIR Server

### Step 1: Query the CapabilityStatement

```bash
curl -s http://localhost:8080/fhir/metadata
```

Extract:
- **FHIR version** (R4, R5, STU3)
- **Supported resource types** and their search parameters
- **Supported profiles** per resource type (tells you which IG is in use)
- **Search parameter details** (what you can actually query on)

Key things to check:
```
# What search parameters does Condition support?
rest[0].resource[type=Condition].searchParam[].name

# What profiles are supported for Condition?
rest[0].resource[type=Condition].supportedProfile[]

# Does the server support _has? _include?
rest[0].resource[type=Condition].searchInclude[]
rest[0].resource[type=Condition].searchRevInclude[]
```

### Step 2: Identify the Implementation Guide

The profiles tell you which IG is active. Common IGs and their implications:

| IG | Profile URL Pattern | Code System Implications |
|----|--------------------|-----------------------|
| **US Core** | `http://hl7.org/fhir/us/core/StructureDefinition/...` | Condition.code: SNOMED preferred, ICD-10 allowed. Observation.code: LOINC required. Medications: RxNorm required. |
| **International Patient Summary** | `http://hl7.org/fhir/uv/ips/StructureDefinition/...` | Similar to US Core but international |
| **C-CDA on FHIR** | `http://hl7.org/fhir/us/ccda/StructureDefinition/...` | Follows C-CDA vocabulary bindings |
| **Base FHIR (no IG)** | `http://hl7.org/fhir/StructureDefinition/...` | Any code system allowed |
| **Synthea-generated** | Usually base FHIR | SNOMED for conditions, LOINC for labs, RxNorm SCD for meds |

### Step 3: Look Up Valueset Bindings from Profiles

Each profile specifies which valuesets are bound to which elements. This tells you exactly which codes are valid.

**Pre-downloaded IG data** is stored in `data/ig-profiles/` in the most concise format available:

**Format preference**: FSH source > YAML StructureDefinition > JSON StructureDefinition

- **FSH (FHIR Shorthand)**: ~30-80 lines per profile. Designed for human readability. If the IG is authored in FSH (check `input/fsh/` in the IG's GitHub repo), use the FSH source directly.
- **YAML**: ~100-200 lines per profile. US Core 8+ uses this format. Far more readable than JSON.
- **JSON**: ~500-2000 lines per profile. Last resort. Can convert to FSH using `npx gofsh`.

```
data/ig-profiles/
├── us-core-8.0.1/
│   ├── StructureDefinition-us-core-condition-problems-health-concerns.yml
│   ├── StructureDefinition-us-core-observation-lab.yml
│   ├── StructureDefinition-us-core-medicationrequest.yml
│   ├── ValueSet-us-core-condition-code-current.yml
│   └── ...
├── ips-1.1.0/
│   └── ... (FSH or YAML preferred)
└── README.md
```

Key valueset bindings for US Core:

| Element | Valueset | Binding Strength | Code Systems |
|---------|----------|-----------------|--------------|
| `Condition.code` | US Core Condition Codes | extensible | SNOMED CT (preferred), ICD-10-CM, ICD-9-CM |
| `Condition.category` | US Core Condition Category | extensible | `problem-list-item`, `health-concern`, `encounter-diagnosis` |
| `Observation.code` | LOINC Codes | extensible | LOINC (required for labs) |
| `Observation.value[x]` | (varies by observation type) | - | Units from UCUM |
| `MedicationRequest.medication[x]` | US Core Medication Codes | extensible | RxNorm (required) |

### Step 4: Verify Codes via UMLS

Once you know which code systems the server uses, verify specific codes:

```
# For a condition: find the SNOMED code
search_umls(query="type 2 diabetes mellitus", search_type="exact")
# → CUI C0011860, SNOMED 44054006

# For a lab: find the LOINC code
search_umls(query="hemoglobin A1c", search_type="words")
# → LOINC 4548-4

# For a medication: find the RxNorm code at the right level
search_umls(query="metformin", search_type="exact")
# → RxNorm 6809 (ingredient) or 860975 (SCD, depends on what server has)
```

### Step 5: Check What's Actually in the Data

Before constructing your query, sample the data to confirm code systems:

```bash
# What code systems are Conditions using?
curl -s "http://localhost:8080/fhir/Condition?_count=5" | \
  jq '.entry[].resource.code.coding[].system' | sort -u

# What code systems are MedicationRequests using?
curl -s "http://localhost:8080/fhir/MedicationRequest?_count=5" | \
  jq '.entry[].resource.medicationCodeableConcept.coding[].system' | sort -u

# What LOINC codes are Observations using?
curl -s "http://localhost:8080/fhir/Observation?_count=5&category=laboratory" | \
  jq '.entry[].resource.code.coding[] | "\(.system)|\(.code) \(.display)"' | sort -u
```

This step is critical because:
- The profile may ALLOW ICD-10, but the data may only CONTAIN SNOMED
- The profile may ALLOW ingredient-level RxNorm, but Synthea generates SCD-level codes
- Some servers have data from multiple sources with mixed code systems

### Step 6: Construct the Query

Now you have everything needed:
- Which search parameters the server supports (from Step 1)
- Which code systems are appropriate (from Steps 2-3)
- The exact codes to use (from Steps 4-5)

---

## Pre-Downloaded Implementation Guide Data

To avoid requiring the LLM to fetch IG packages at runtime, we pre-download key profile and valueset data.

### How to Download IG Data

```bash
# Download US Core 6.1.0 package
mkdir -p data/ig-profiles/us-core-6.1.0
cd data/ig-profiles/us-core-6.1.0

# From the FHIR package registry
npm --registry https://packages.fhir.org install hl7.fhir.us.core@6.1.0

# Or download individual StructureDefinitions from the IG website
curl -o StructureDefinition-us-core-condition-problems-health-concerns.json \
  "http://hl7.org/fhir/us/core/STU6.1/StructureDefinition-us-core-condition-problems-health-concerns.json"
```

### Key Files to Pre-Download per IG

For each implementation guide, download:

1. **StructureDefinitions** for key clinical resource types:
   - Condition (diagnosis)
   - Observation (labs, vitals)
   - MedicationRequest (medication orders)
   - Patient
   - Encounter

2. **ValueSets** bound to key elements:
   - Condition.code valueset
   - Observation.code valueset
   - MedicationRequest.medication valueset
   - Observation category valueset

3. **CodeSystems** if custom (most use standard systems like SNOMED, LOINC, RxNorm)

### Loading Profiles into the FHIR Server

For evaluation, load the IG profiles so the server can validate and the CapabilityStatement reflects them:

```bash
# Load US Core profiles into HAPI FHIR
for f in data/ig-profiles/us-core-6.1.0/StructureDefinition-*.json; do
  curl -X POST http://localhost:8080/fhir/StructureDefinition \
    -H "Content-Type: application/fhir+json" \
    -d @"$f"
done

# Load ValueSets
for f in data/ig-profiles/us-core-6.1.0/ValueSet-*.json; do
  curl -X POST http://localhost:8080/fhir/ValueSet \
    -H "Content-Type: application/fhir+json" \
    -d @"$f"
done
```

---

## Agentic Evaluation Architecture

For Tier 2 and 3 evaluation, the LLM needs to execute this skill as part of its reasoning loop:

```
User Prompt → LLM Agent
                ├→ [Step 1] Query /metadata (Bash tool)
                ├→ [Step 2] Identify IG from profiles
                ├→ [Step 3] Read pre-downloaded profile data (Read tool)
                ├→ [Step 4] Verify codes via UMLS MCP
                ├→ [Step 5] Sample actual data (Bash/curl)
                └→ [Step 6] Construct and return FHIR query
```

### Implementation Options

| Approach | How It Works | Supports MCP | Multi-turn |
|----------|-------------|:---:|:---:|
| **Anthropic API + tools** | Define UMLS + FHIR as function tools | Via tool definitions | Yes |
| **Claude Agent SDK** | Build agent with MCP server access | Native MCP | Yes |
| **Claude CLI + MCP config** | Run `claude --print` with `.mcp.json` | Yes | Limited |
| **Custom agent loop** | Wrap any LLM with tool dispatch | Manual | Yes |

### Evaluation Metrics for Agentic Mode

| Metric | Description |
|--------|-------------|
| **Final F1** | Same as closed-book: query correctness |
| **Code accuracy** | Did it use the right codes? (SNOMED vs ICD-10, correct LOINC) |
| **Tool calls made** | How many UMLS lookups, /metadata queries, data samples |
| **Self-correction** | Did it try a query, see an error, and fix it? |
| **Server introspection** | Did it check /metadata before querying? |
| **Code verification** | Did it verify codes via UMLS before using them? |
| **Profile awareness** | Did it check which IG/profiles are in use? |

---

## Synthea Data and Code System Reality

Important context for the skill: Synthea-generated data has specific code system patterns:

| Resource | Code System Used | Notes |
|----------|-----------------|-------|
| Condition | SNOMED CT only | Even though US Core allows ICD-10, Synthea only generates SNOMED |
| Observation (labs) | LOINC | Standard LOINC codes |
| Observation (vitals) | LOINC | Standard vital sign LOINC codes |
| MedicationRequest | RxNorm (SCD level) | Specific drug forms, not ingredient codes |
| Encounter | SNOMED CT | Encounter type codes |
| Immunization | CVX | Vaccine codes |

An LLM that checks the actual data (Step 5) will discover this and use SNOMED for conditions, even if the profile technically allows ICD-10.
