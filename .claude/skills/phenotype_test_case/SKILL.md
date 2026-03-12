---
name: phenotype_test_case
description: Create phenotype-based test cases for the FHIR query evaluation framework. Analyzes PheKB phenotype algorithms, generates per-path test case JSON files, and validates them against FHIR server data.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, mcp__nih-umls__search_umls, mcp__nih-umls__get_concept, mcp__nih-umls__crosswalk_codes, mcp__nih-umls__get_source_concept, mcp__nih-umls__get_definitions
---

# Phenotype Test Case Creation Skill

## Usage

```
/phenotype_test_case <command> <phenotype>
```

## Commands

| Command | Description |
|---------|-------------|
| `analyze <phenotype>` | Analyze a phenotype's algorithm from downloaded PheKB docs and identify all decision paths |
| `create <phenotype>` | Create test case JSON files from algorithm analysis (one per path) |
| `validate <phenotype>` | Validate test cases against loaded FHIR server data |

---

## Instructions for Claude

### For `analyze <phenotype>`:

The goal is to read ALL available phenotype documents and produce a structured analysis of the algorithm's decision paths.

1. **Read all available phenotype data:**
   ```
   Read: data/phekb-raw/<phenotype>/document_analysis.json
   Read: data/phekb-raw/<phenotype>/description.txt
   Glob: data/phekb-raw/<phenotype>/*
   ```
   Read any PDFs, docs, or other files that describe the phenotyping algorithm.

2. **Identify ALL algorithm paths:**

   PheKB phenotype algorithms are NOT simple code lookups. They are multi-path decision trees. The critical step is identifying every distinct path through the algorithm that qualifies a patient as a case.

   For each path, document:
   - **Path number and name** (e.g., "Path 1: T2DM dx + T2DM meds + T1DM meds (T2DM Rx first)")
   - **Required resources** - Which FHIR resource types are needed (Condition, MedicationRequest, Observation, etc.)
   - **Required codes** - Diagnosis codes, medication codes, lab codes
   - **Value thresholds** - Lab value cutoffs (e.g., HbA1c >= 6.5%)
   - **Temporal requirements** - Ordering constraints (e.g., T2DM meds prescribed before T1DM meds)
   - **Exclusion criteria** - What must NOT be present
   - **Logical operators** - AND/OR relationships between criteria

   Example from the T2D proof of concept (5 paths):
   - Path 1: T2DM diagnosis + T2DM medications + T1DM medications (T2DM Rx ordered first)
   - Path 2: T2DM diagnosis + T2DM medications (no T1DM medications)
   - Path 3: T2DM diagnosis + abnormal labs (no medications)
   - Path 4: NO diagnosis + T2DM medications + abnormal labs
   - Path 5: T2DM diagnosis + T1DM medications (>= 2 physician-entered T2DM diagnoses)

3. **Verify ALL codes using the UMLS MCP tools (CRITICAL):**

   Do NOT trust codes from `document_analysis.json` blindly. They may be incomplete, have placeholder descriptions, or use wrong code levels. For every code category:

   a. **Diagnosis codes** - Verify across SNOMED, ICD-10-CM, and ICD-9-CM:
      ```
      search_umls(query="<condition name>", search_type="exact")
      get_concept(cui="<CUI>")
      crosswalk_codes(source="SNOMEDCT_US", code="<code>", target_source="ICD10CM")
      crosswalk_codes(source="SNOMEDCT_US", code="<code>", target_source="ICD9CM")
      ```

   b. **Lab LOINC codes** - Find the correct observation code:
      ```
      search_umls(query="<lab name>", search_type="words")
      ```
      Look for results with semantic type "Laboratory Procedure" or "Clinical Attribute".

   c. **Medication RxNorm codes** - Verify at the right level (ingredient vs. SCD):
      ```
      search_umls(query="<medication name>", search_type="exact")
      get_source_concept(source="RXNORM", id="<code>")
      ```
      For FHIR queries, ingredient-level codes (e.g., "6809" for Metformin) are preferred because they match any formulation. SCD-level codes (specific dose forms) are too narrow.

   d. **Cross-check codes from document_analysis.json:**
      ```
      get_source_concept(source="ICD10CM", id="<CODE>")
      get_source_concept(source="RXNORM", id="<CODE>")
      ```
      Verify the display name matches the intended concept. Discard obsolete codes.

   See the `/umls` skill for full details on crosswalk behavior and gotchas.

4. **Output a structured analysis** summarizing:
   - Total number of algorithm paths
   - Each path with its criteria, required FHIR resources, and verified codes
   - Control/exclusion criteria
   - Recommended test case breakdown (which paths become which test cases)

---

### For `create <phenotype>`:

Creates one or more test case JSON files. Each algorithm path that targets a distinct FHIR resource type should become a SEPARATE test case.

1. **Read the analysis** (run `analyze` first if not already done):
   ```
   Read: data/phekb-raw/<phenotype>/document_analysis.json
   Read: test-cases/phekb/phekb-<phenotype>.json (if exists, use as base)
   ```

2. **Determine test case breakdown:**

   Each test case should target a SINGLE FHIR resource type query. This is a deliberate design choice: it tests whether the LLM can:
   - Choose the correct resource type for the clinical question
   - Use the right code system and codes
   - Apply value filters correctly (e.g., `value-quantity` for lab thresholds)

   Typical breakdown for a multi-resource phenotype:

   | Test Case | Resource Type | What It Tests |
   |-----------|---------------|---------------|
   | `<phenotype>-dx` | Condition | Finding patients by diagnosis codes |
   | `<phenotype>-meds` | MedicationRequest | Finding patients by medication orders |
   | `<phenotype>-labs` | Observation | Finding patients by lab values with thresholds |
   | `<phenotype>-path4-meds-no-dx` | MedicationRequest/Patient | Subtle: patients identified by meds who have NO Condition |
   | **`<phenotype>-comprehensive`** | **Multi-query** | **Provider-level: find ALL patients using multiple queries** |

   For complex phenotypes with multiple paths, create path-specific test cases:
   - `phekb-<phenotype>-path1-<description>`
   - `phekb-<phenotype>-path2-<description>`
   - etc.

   **ALWAYS create a comprehensive "provider query" test case** for every phenotype. This is the most realistic and important test case:

   #### The Comprehensive Provider Query Pattern

   This test case simulates an experienced healthcare provider who knows that not all patients have perfect documentation. The prompt:
   - Acknowledges that some patients may lack formal diagnosis codes
   - Explicitly asks the LLM to run MULTIPLE FHIR queries
   - Lists the evidence types to search (diagnoses, medications, labs)
   - Asks for the union of all patients found

   The test case uses `metadata.multi_query: true` and `metadata.expected_queries` (a list of query URLs). The evaluation runner:
   1. Parses ALL queries from the LLM response (not just the first one)
   2. Executes each query against the FHIR server
   3. Extracts patient IDs from all results
   4. Unions the patient IDs across all queries
   5. Compares the union against `test_data.expected_patient_ids`
   6. Scores based on patient-level precision/recall/F1
   7. Also scores query coverage (how many of the expected resource types the LLM searched)

   Example comprehensive prompt (from T2D):
   ```
   I need to identify my complete type 2 diabetes patient population for a quality
   improvement initiative. I know from experience that not all diabetic patients have
   a formal diagnosis code in their chart — some were started on metformin or other
   oral hypoglycemics by outside providers, and others have consistently elevated A1c
   results but the diagnosis was never formally documented.

   Please run multiple FHIR queries to capture the full population:
   1. Patients with a type 2 diabetes diagnosis on their problem list
   2. Patients prescribed oral diabetes medications (metformin, sulfonylureas, etc.)
   3. Patients with hemoglobin A1c results at or above 6.5%

   For each query, return the matching resources. I want to see the union of all
   patients found across these three approaches.
   ```

   This prompt is designed to:
   - Sound like a real clinician (quality improvement initiative context)
   - Explain WHY multiple queries are needed (outside providers, undocumented diagnoses)
   - Name specific medication classes (not codes) to guide code selection
   - Specify the lab threshold (6.5%) without using LOINC codes
   - Explicitly request a union approach

   Evaluation results from T2D showed:
   - Naive LLM (dx only): 70% recall, misses 30% of patients
   - Good LLM (dx + meds): 95% recall
   - Excellent LLM (all 3 queries): 100% recall

   JSON structure for comprehensive test cases:
   ```json
   {
     "metadata": {
       "multi_query": true,
       "expected_queries": [
         "Condition?code=...",
         "MedicationRequest?code=...",
         "Observation?code=...&value-quantity=..."
       ]
     },
     "test_data": {
       "expected_patient_ids": ["id1", "id2", ...],
       "expected_result_count": 20
     }
   }
   ```

3. **Write prompts using natural clinical language (CRITICAL):**

   Prompts MUST be code-free. They use natural clinical language only. This is the core test: can the LLM determine the appropriate codes from clinical context?

   Prompt design principles:
   - **No codes in prompts** - Never mention SNOMED, ICD-10, LOINC codes, or code system URIs
   - **May target one or multiple resource types** - Some test cases target a single resource type (easy), others require cross-resource queries using `_has`, `_include`, `_revinclude`, or chained searches (hard)
   - **Include clinical context** - Give enough context for the LLM to determine the right approach
   - **Vary difficulty levels:**
     - Easy: "Find all patients diagnosed with type 2 diabetes" (obvious Condition query)
     - Medium: "Find patients prescribed metformin or other oral diabetes medications" (MedicationRequest)
     - Hard: "Find patients with hemoglobin A1c lab results at or above 6.5%" (Observation with value filter)
     - Subtle: "Find patients on diabetes medications who may not have a formal diabetes diagnosis" (tests whether LLM queries MedicationRequest, not Condition)

4. **Construct expected FHIR queries:**

   Common query patterns for phenotype test cases:

   | Pattern | Example |
   |---------|---------|
   | Condition by code | `Condition?code=http://snomed.info/sct\|44054006` |
   | Condition by multiple codes | `Condition?code=http://hl7.org/fhir/sid/icd-10-cm\|E11,http://snomed.info/sct\|44054006` |
   | MedicationRequest by code | `MedicationRequest?code=http://www.nlm.nih.gov/research/umls/rxnorm\|6809` |
   | MedicationRequest multiple meds | `MedicationRequest?code=http://www.nlm.nih.gov/research/umls/rxnorm\|6809,http://www.nlm.nih.gov/research/umls/rxnorm\|4821` |
   | Observation by code + value | `Observation?code=http://loinc.org\|4548-4&value-quantity=ge6.5\|\|%25` |
   | Observation by code only | `Observation?code=http://loinc.org\|2339-0` |
   | Patient-level `_has` | `Patient?_has:Condition:patient:code=http://snomed.info/sct\|44054006` |
   | `_include` (pull related resources) | `Condition?code=http://snomed.info/sct\|44054006&_include=Condition:patient` |
   | `_revinclude` (pull referencing resources) | `Patient?_revinclude=Condition:patient&_revinclude=MedicationRequest:patient` |
   | Chained search | `MedicationRequest?patient.name=Smith&code=http://www.nlm.nih.gov/research/umls/rxnorm\|860975` |
   | Multi-resource via `_has` (complex) | `Patient?_has:Condition:patient:code=http://snomed.info/sct\|44054006&_has:MedicationRequest:patient:code=http://www.nlm.nih.gov/research/umls/rxnorm\|860975` |

   **Cross-resource query patterns (advanced):**

   Some phenotype paths require combining evidence from multiple resource types in a SINGLE query. FHIR supports this through:

   - **`_has` parameter**: Find resources that are referenced by other resources matching criteria. E.g., find Patients who _have_ both a T2DM Condition AND a Metformin MedicationRequest.
   - **`_include` / `_revinclude`**: Return related resources alongside the primary results. Useful for getting Patient + Condition + Medication in one response.
   - **Chained search**: Search on properties of referenced resources. E.g., `Observation?patient._has:Condition:patient:code=...` to find labs for patients with a specific condition.
   - **Composite search parameters**: Some servers support composite parameters for AND logic within a single resource type.

   Test cases should vary in complexity:
   - **Easy**: Single resource type, single code (e.g., `Condition?code=...`)
   - **Medium**: Single resource type, multiple codes or value filters
   - **Hard**: Cross-resource using `_has`, `_include`, or chained searches
   - **Expert**: Multi-`_has` combining Condition + MedicationRequest + Observation evidence

   Notes on value-quantity encoding:
   - `ge6.5||%25` means >= 6.5 % (percent, URL-encoded as %25)
   - `gt200||mg/dL` means > 200 mg/dL
   - The format is `[prefix][value]||[unit]` where `||` separates value from unit (system is empty)

5. **Build the test case JSON structure:**

   ```json
   {
     "id": "phekb-<phenotype>-<path-description>",
     "source": "phekb",
     "source_id": "<phenotype-slug>",
     "name": "<Human Readable Name>",
     "description": "Description of what this test case evaluates and which algorithm path it covers.",
     "prompt": "<Natural language clinical prompt - NO CODES>",
     "metadata": {
       "implementation_guide": "US Core 5.0.0",
       "code_systems": ["ICD-10-CM", "SNOMED CT", "RxNorm", "LOINC"],
       "required_codes": [
         {
           "system": "http://snomed.info/sct",
           "code": "44054006",
           "display": "Type 2 diabetes mellitus"
         }
       ],
       "complexity": "easy|medium|hard",
       "algorithm_path": "Path N: <brief description>",
       "tags": ["condition", "endocrinology", "type-2-diabetes"]
     },
     "expected_query": {
       "resource_type": "Condition|MedicationRequest|Observation|Patient",
       "parameters": {
         "code": "<system>|<code>,<system>|<code>"
       },
       "url": "<full FHIR query URL>"
     },
     "test_data": {
       "resources": [
         "synthea/output/<phenotype>/positive/fhir/",
         "synthea/output/<phenotype>/control/fhir/"
       ],
       "expected_result_count": null,
       "expected_resource_ids": []
     },
     "created_at": "<ISO timestamp>",
     "updated_at": "<ISO timestamp>"
   }
   ```

   Key fields:
   - `id`: Unique, descriptive, uses format `phekb-<phenotype>-<path-or-focus>`
   - `metadata.algorithm_path`: Which phenotype algorithm path this tests (e.g., "Path 2: T2DM dx + T2DM meds, no T1DM meds")
   - `metadata.complexity`: "easy" for straightforward single-code queries, "medium" for multi-code or multi-system, "hard" for value filters or subtle logic
   - `metadata.required_codes`: ALL codes that the expected query should use, verified via UMLS
   - `metadata.tags`: Include resource type, clinical domain, phenotype name, difficulty indicators
   - `test_data.expected_result_count` and `expected_resource_ids`: Populate after Synthea data is generated and loaded; leave as `null`/`[]` initially

6. **Write the test case files:**
   ```
   Write: test-cases/phekb/phekb-<phenotype>.json           (single-resource or primary test case)
   Write: test-cases/phekb/phekb-<phenotype>-meds.json      (medication-focused)
   Write: test-cases/phekb/phekb-<phenotype>-labs.json       (lab-focused)
   Write: test-cases/phekb/phekb-<phenotype>-path4.json      (path-specific)
   ```

   If a single combined test case already exists (like `phekb-type-2-diabetes.json`), keep it as the primary and create additional path-specific files alongside it.

7. **Validate JSON syntax** by reading back each file.

---

### For `validate <phenotype>`:

Validates that test cases produce expected results when run against FHIR server data.

1. **Check prerequisites:**
   ```bash
   curl -s http://localhost:8080/fhir/metadata | head -5
   ```
   FHIR server must be running with data loaded for this phenotype.

2. **Read all test cases for the phenotype:**
   ```
   Glob: test-cases/phekb/phekb-<phenotype>*.json
   ```

3. **For each test case, execute the expected query:**
   ```bash
   curl -s "http://localhost:8080/fhir/<expected_query.url>" | python -m json.tool
   ```

4. **Verify results:**

   a. **Positive cases match:** The query should return resources from positive patients.
      - Check that `total` or `entry` count matches `expected_result_count` (if set)
      - Check that returned resource IDs match `expected_resource_ids` (if set)

   b. **Controls excluded:** The query should NOT return resources from control patients.
      - Cross-reference returned Patient references against control patient IDs

   c. **Code coverage:** Check that the returned resources use the expected code systems:
      ```bash
      # Check what codes are actually in the returned Conditions
      curl -s "http://localhost:8080/fhir/Condition?code=http://snomed.info/sct|44054006" | \
        python -c "import json,sys; d=json.load(sys.stdin); [print(e['resource']['code']['coding']) for e in d.get('entry',[])]"
      ```

5. **Update test case with actual results:**

   After validation, update the test case JSON:
   - Set `test_data.expected_result_count` to the actual count
   - Set `test_data.expected_resource_ids` to the actual resource IDs returned
   - Note any discrepancies in the description

6. **Report validation results:**

   ```
   Test Case: phekb-type-2-diabetes-dx
   Query: Condition?code=http://snomed.info/sct|44054006
   Expected: 20 results
   Actual: 20 results
   Status: PASS

   Test Case: phekb-type-2-diabetes-labs
   Query: Observation?code=http://loinc.org|4548-4&value-quantity=ge6.5||%25
   Expected: 18 results
   Actual: 15 results
   Status: FAIL - 3 missing (investigate Synthea module lab generation)
   ```

---

## Methodology Reference

This section documents the methodology learned from the Type 2 Diabetes Mellitus proof of concept.

### Step 1: Algorithm Path Analysis

PheKB phenotype algorithms are complex decision trees, not simple code lookups. The T2D algorithm had 5 distinct paths to identify positive cases:

| Path | Requires | Notes |
|------|----------|-------|
| 1 | T2DM dx + T2DM meds + T1DM meds | T2DM Rx must be ordered BEFORE T1DM Rx (temporal) |
| 2 | T2DM dx + T2DM meds | No T1DM medications at all |
| 3 | T2DM dx + abnormal labs | No medications; labs meet thresholds |
| 4 | T2DM meds + abnormal labs | NO diagnosis code; identified purely by meds + labs |
| 5 | T2DM dx + T1DM meds only | Must have >= 2 physician-entered T2DM diagnoses |

Each path exercises different FHIR resource types and query patterns, so each should become a separate test case.

### Step 2: Multi-Resource Query Decomposition

Many phenotypes cannot be expressed as a single FHIR query. The algorithm may simultaneously require:
- **Condition** resources (diagnosis codes)
- **MedicationRequest** resources (medication orders)
- **Observation** resources (lab values with thresholds)
- Logical combination across resource types

Create test cases at multiple complexity levels:

**Simple test cases** (one resource type per path):
- Tests whether the LLM chooses the correct resource type
- Tests whether it uses the right code system and codes
- Tests value filters (e.g., `value-quantity` for Observation)

**Cross-resource test cases** (combine evidence from multiple resource types):
- Uses `_has` to find Patients matching criteria across Condition + MedicationRequest + Observation
- Uses `_include`/`_revinclude` to pull related resources in one query
- Uses chained searches for complex phenotype logic
- Example: `Patient?_has:MedicationRequest:patient:code=http://www.nlm.nih.gov/research/umls/rxnorm|860975&_has:Observation:patient:code=http://loinc.org|4548-4&_has:Observation:patient:value-quantity=ge6.5||%25`
- These are the hardest test cases and most accurately reflect real clinical informatics needs

### Step 3: Code Verification via UMLS

ALWAYS verify codes before putting them in test cases. The `document_analysis.json` may contain:
- Placeholder descriptions instead of actual codes (e.g., "T2DM ICD-9 codes" instead of "250.00")
- Codes at the wrong level (SCD instead of ingredient for RxNorm)
- Obsolete or retired codes

Use the `/umls` skill to get authoritative codes. Key patterns:
- **RxNorm ingredient codes** are preferred for FHIR queries (e.g., "6809" for Metformin) because they match any dose form or strength
- **SNOMED codes** are the most interoperable and usually the best choice for Condition queries
- **ICD-10 codes** may need to include the parent code (e.g., "E11" covers E11.0 through E11.9)
- **LOINC codes** can have multiple codes for the same lab test (e.g., HbA1c has "4548-4" general and "17856-6" by HPLC)

### Step 4: Synthea Module Alignment

The Synthea module MUST generate patients that match each test case path:
- **Path-specific patients**: Path 4 patients must have MedicationRequest and Observation resources but NO Condition resource for the phenotype
- **Control patients**: Must NOT match any path
- **Code alignment**: The Synthea module must use the SAME codes that appear in the test case `required_codes`

Use the `/synthea` skill to create aligned modules after test cases are defined.

### Step 5: Prompt Design

Prompts are the most important part of the test case. They must:
- Use **natural clinical language only** - no codes, no system URIs, no technical FHIR terminology
- Be **unambiguous about the target resource type** - the reader should know whether to query Condition, MedicationRequest, or Observation
- Include **enough clinical context** to determine the right codes without being prescriptive
- **Vary in difficulty** across the test suite

Examples of good prompts:
- Easy: "Find all patients who have been diagnosed with type 2 diabetes mellitus."
- Medium: "Retrieve medication orders for patients prescribed oral hypoglycemic agents such as metformin, glipizide, or pioglitazone."
- Hard: "Find laboratory observations for hemoglobin A1c tests where the result was at or above 6.5 percent."
- Subtle: "Identify patients who are receiving diabetes medications but may not yet have a formal diabetes diagnosis recorded."

Examples of bad prompts:
- "Query Condition resources for SNOMED code 44054006" (contains codes)
- "Find patients" (too vague, no resource type direction)
- "Search for E11 diagnoses" (contains ICD-10 code)

---

## Evaluation Gotchas (Lessons Learned)

These are critical lessons from the T2D proof of concept that apply to all phenotypes:

### 1. Synthea Only Codes Conditions in SNOMED
Synthea's FHIR exporter writes Condition resources with SNOMED-CT codes only — NOT ICD-10 or ICD-9. An LLM that generates `Condition?code=http://hl7.org/fhir/sid/icd-10-cm|E11` will get zero results even though E11 is clinically correct. This is a realistic test of whether the LLM knows what code system the server uses, but it means:
- Expected queries should use SNOMED codes for Condition resources
- ICD-based queries are valid alternative answers but will score 0 on execution match
- Consider accepting multiple valid queries in the evaluation (future enhancement)

### 2. Ingredient vs SCD Code Mismatch
HAPI FHIR does NOT automatically resolve RxNorm ingredient codes to SCD codes. If Synthea generates `MedicationRequest` with SCD code `860975` (metformin 500mg ER), a query for ingredient code `6809` (metformin) will return zero results. Expected queries must use the EXACT SCD codes that Synthea generates.

### 3. Value-Quantity Encoding
The `value-quantity` parameter encoding is tricky:
- Format: `[prefix][value]||[unit]` — note the double pipe `||` (empty system)
- Percent must be URL-encoded: `%25` not `%`
- Example: `Observation?code=http://loinc.org|4548-4&value-quantity=ge6.5||%25`
- Not all FHIR servers support `value-quantity` filtering the same way

### 4. `_has` Query Semantics
The `_has` parameter finds resources REFERENCED BY other resources matching criteria:
- `Patient?_has:Condition:patient:code=X` = "find Patients who are referenced by a Condition with code X"
- Multiple `_has` parameters are AND-ed together
- Not all servers support `_has` (fhir-candle has limited support; HAPI and Azure do)
- The `_has` parameter cannot do value-quantity filtering on the nested resource in all servers

### 5. Control Patient Contamination
Control patients may still have Observation resources (normal lab values) that could match broad queries. Ensure:
- Lab-based queries include value thresholds to exclude normal values
- Control modules generate values BELOW the case threshold
- Use the STRICTER control exclusion thresholds from the algorithm (e.g., T2D controls: HbA1c < 6.0%, not < 6.5%)

### 6. Expected Result Count Depends on Data Generation
`expected_result_count` and `expected_resource_ids` must be populated AFTER loading data, not hardcoded:
- Synthea's random distributions mean exact counts vary by seed
- Always run `fhir-eval load synthea -p <phenotype> --update-test-case` or use `/phenotype_test_case validate` after data generation
- Some patients may be too young to have clinical data (Age_Guard filtering)

### 7. Observation Queries Return Multiple Results Per Patient
Unlike Condition (typically one per diagnosis), Observation queries may return MANY results per patient (every HbA1c reading at every visit). This is expected behavior. The evaluation compares resource IDs, so multiple observations per patient count individually.

---

## Evaluation Tiers and Agentic Testing

This framework supports three evaluation tiers. Test cases created by this skill are used in all three:

| Tier | LLM Has Access To | What It Tests |
|------|-------------------|---------------|
| **1. Closed Book** | Just the prompt | Raw FHIR + clinical knowledge |
| **2. Tool-Assisted** | + UMLS MCP + FHIR `/metadata` | Reasoning + tool use |
| **3. Skill-Guided** | + IG profiles (FSH/YAML) + valueset bindings + `/fhir_server_introspection` skill | Following a systematic approach |

For Tier 2/3, see:
- **`/fhir_server_introspection` skill** — teaches the LLM to query server capabilities, check profiles, and verify codes
- **`docs/PLAN-AGENTIC-EVALUATION.md`** — full architecture for agentic evaluation with tool access

### Dual Test Data Sets

For each phenotype, we plan to generate TWO data variants:
- **Generic (FHIR R4)**: Synthea default — SNOMED conditions, LOINC labs, RxNorm SCD meds
- **US Core**: Adds ICD-10-CM codes alongside SNOMED, US Core categories, proper must-support elements

This tests whether LLMs adapt their query strategy based on the server's profile/IG.

### IG Profile Data for Tier 3

Pre-downloaded IG profiles are in `data/ig-profiles/`. Format preference: **FSH > YAML > JSON**.

US Core 8.0.1 profiles (YAML) are already downloaded. Key finding: **US Core 8 removed ICD-9-CM** from the condition code valueset — only SNOMED + ICD-10-CM for new records.

## Running Evaluations

```bash
# Single test case
fhir-eval run -t phekb-type-2-diabetes-dx -p command --command "ollama run qwen2.5:7b" -v

# All T2D test cases
for tc in dx meds labs path4-meds-labs comprehensive; do
  fhir-eval run -t phekb-type-2-diabetes-$tc -p command --command "ollama run qwen2.5:7b"
done

# Results saved to results/ directory as JSON
```

### Known Provider Issues

- **claude-cli (`--print` mode)**: Requires Anthropic API credits, NOT covered by Max subscription
- **Ollama**: The `ollama run` command outputs ANSI spinner chars on stderr that can cause `cp1252 UnicodeDecodeError` on Windows. Use `--nowordwrap` flag to minimize this. The command provider captures stdout which is usually clean.

---

## Code System URI Reference

| System | FHIR URI | Example Query |
|--------|----------|---------------|
| SNOMED CT | `http://snomed.info/sct` | `Condition?code=http://snomed.info/sct\|44054006` |
| ICD-10-CM | `http://hl7.org/fhir/sid/icd-10-cm` | `Condition?code=http://hl7.org/fhir/sid/icd-10-cm\|E11` |
| ICD-9-CM | `http://hl7.org/fhir/sid/icd-9-cm` | `Condition?code=http://hl7.org/fhir/sid/icd-9-cm\|250.00` |
| LOINC | `http://loinc.org` | `Observation?code=http://loinc.org\|4548-4` |
| RxNorm | `http://www.nlm.nih.gov/research/umls/rxnorm` | `MedicationRequest?code=http://www.nlm.nih.gov/research/umls/rxnorm\|6809` |

---

## Example Session

```
User: /phenotype_test_case analyze type-2-diabetes-mellitus

Claude: Analyzing the T2DM phenotype algorithm...

[Reads document_analysis.json, description.txt, algorithm PDF]
[Identifies 5 algorithm paths]
[Verifies codes via UMLS MCP tools]

Analysis complete. The T2DM algorithm has 5 distinct case identification paths:

Path 1: T2DM dx + T2DM meds + T1DM meds (T2DM Rx first)
  - Resources: Condition, MedicationRequest
  - Dx codes: SNOMED 44054006, ICD-10 E11, ICD-9 250.00/250.02
  - T2DM meds: Metformin (RxNorm 6809), Glipizide (4821), ...
  - T1DM meds: Insulin (RxNorm 253182)
  - Temporal: T2DM med order date < T1DM med order date

Path 2: T2DM dx + T2DM meds (no T1DM meds)
  ...

[Continues for all 5 paths]

Recommended test cases:
1. phekb-type-2-diabetes-dx (Condition query, easy)
2. phekb-type-2-diabetes-meds (MedicationRequest query, medium)
3. phekb-type-2-diabetes-labs-hba1c (Observation + value filter, hard)
4. phekb-type-2-diabetes-labs-glucose (Observation + value filter, hard)
5. phekb-type-2-diabetes-path4-meds-no-dx (MedicationRequest, subtle)
```

```
User: /phenotype_test_case create type-2-diabetes-mellitus

Claude: Creating test cases for T2DM based on algorithm analysis...

[Verifies all codes via UMLS]
[Creates 5 test case JSON files]

Created test cases:
- test-cases/phekb/phekb-type-2-diabetes.json (primary dx query)
- test-cases/phekb/phekb-type-2-diabetes-meds.json (medication query)
- test-cases/phekb/phekb-type-2-diabetes-labs-hba1c.json (HbA1c with value filter)
- test-cases/phekb/phekb-type-2-diabetes-labs-glucose.json (glucose with value filter)
- test-cases/phekb/phekb-type-2-diabetes-path4.json (meds without diagnosis)

Next steps:
- Run /synthea create-module type-2-diabetes to create aligned Synthea module
- Run /synthea full type-2-diabetes to generate and load test data
- Run /phenotype_test_case validate type-2-diabetes-mellitus to verify
```

```
User: /phenotype_test_case validate type-2-diabetes-mellitus

Claude: Validating T2DM test cases against FHIR server...

[Checks FHIR server is running]
[Executes each expected query]
[Compares results against expected counts]

Validation Results:
  phekb-type-2-diabetes          Condition query       20/20 results  PASS
  phekb-type-2-diabetes-meds     MedicationRequest     20/20 results  PASS
  phekb-type-2-diabetes-labs     Observation+value     18/20 results  WARN
  phekb-type-2-diabetes-path4    MedicationRequest     3/3 results    PASS

Note: Labs test case returned 18/20 - 2 patients had HbA1c values
generated just below the 6.5% threshold due to Synthea randomization.
Consider tightening the Synthea module value range.

Updated test case files with actual resource IDs.
```
