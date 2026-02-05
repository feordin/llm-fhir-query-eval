---
name: synthea
description: Generate synthetic FHIR test data from PheKB phenotype definitions using Synthea. Creates custom Synthea modules, runs data generation, and loads results to the FHIR server.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Synthea Test Data Generation Skill

## Usage

```
/synthea <command> [options]
```

## Commands

| Command | Description |
|---------|-------------|
| `create-module <phenotype>` | Create Synthea module from phenotype data |
| `generate <phenotype>` | Run Synthea to generate FHIR data |
| `load <phenotype>` | Load generated data to FHIR server |
| `full <phenotype>` | Create module + generate + load (full pipeline) |
| `status` | Show status of all phenotypes |
| `list` | List available phenotypes with modules |
| `batch <phenotypes...>` | Process multiple phenotypes |

## Command Details

### create-module

Creates a Synthea GMF (Generic Module Framework) module from phenotype data.

**Inputs:**
- `data/phekb-raw/<phenotype>/document_analysis.json` - Extracted codes and criteria
- `data/phekb-raw/<phenotype>/description.txt` - Phenotype description
- `test-cases/phekb/phekb-<phenotype>.json` - Test case with required codes

**Outputs:**
- `synthea/modules/custom/phekb_<phenotype>.json` - Positive case module
- `synthea/modules/custom/phekb_<phenotype>_control.json` - Control module

### generate

Runs Synthea with the custom module to generate synthetic patients.

**Options:**
- `--patients N` - Number of positive cases (default: 20)
- `--controls N` - Number of control cases (default: 20)
- `--seed N` - Random seed for reproducibility

**Outputs:**
- `synthea/output/<phenotype>/positive/fhir/*.json` - Positive patient bundles
- `synthea/output/<phenotype>/control/fhir/*.json` - Control patient bundles

### load

Loads generated FHIR bundles to the fhir-candle server.

**Prerequisites:**
- FHIR server running at `http://localhost:5826/r4`
- Generated data exists in `synthea/output/<phenotype>/`

### full

Runs the complete pipeline: create-module → generate → load

### status

Shows which phenotypes have:
- Document analysis data
- Synthea modules created
- Generated data
- Data loaded to FHIR server

---

## Instructions for Claude

When this skill is invoked, follow these instructions based on the command:

### For `create-module <phenotype>`:

1. **Read the phenotype data:**
   ```
   Read: data/phekb-raw/<phenotype>/document_analysis.json
   Read: test-cases/phekb/phekb-<phenotype>.json (if exists)
   ```

2. **Extract key information:**
   - Diagnosis codes (ICD-9, ICD-10, SNOMED-CT)
   - Lab codes (LOINC) with thresholds from clinical_criteria
   - Medication codes (RxNorm)
   - Age requirements
   - Exclusion criteria

3. **Generate the Synthea module** following GMF format:
   - Use the existing `synthea/modules/custom/phekb_type_2_diabetes.json` as a template
   - Include multiple code systems for each concept (SNOMED + ICD-10 + ICD-9)
   - Set realistic value ranges based on clinical_criteria
   - Create state machine: Initial → Age Guard → Condition Onset → Labs → Medications → Terminal

4. **Generate the control module:**
   - Normal lab values (below diagnostic thresholds)
   - No phenotype-specific diagnosis codes
   - May include unrelated conditions for variety

5. **Write the modules:**
   ```
   Write: synthea/modules/custom/phekb_<phenotype>.json
   Write: synthea/modules/custom/phekb_<phenotype>_control.json
   ```

6. **Validate JSON syntax** by reading back and parsing

### For `generate <phenotype>`:

1. **Check prerequisites:**
   - Synthea source build exists at `C:\repos\synthea` (or `SYNTHEA_HOME` env var)
   - Module exists: `synthea/modules/custom/phekb_<phenotype>.json`

2. **If Synthea not found**, provide install instructions:
   ```bash
   git clone https://github.com/synthetichealth/synthea.git C:/repos/synthea
   ```

3. **IMPORTANT: Environment-specific issues to handle:**

   Claude Code runs in a **bash environment** (git bash), NOT cmd.exe. This causes three issues:

   **Issue 1: `.bat` files don't run natively in bash.**
   - Do NOT call `run_synthea.bat` directly — it won't find `gradlew.bat`.
   - Instead, call `./gradlew` (the Unix wrapper) directly from the Synthea directory.

   **Issue 2: JAVA_HOME / Java not on PATH.**
   - Git bash doesn't inherit Windows system PATH fully. Java may not be found.
   - Before running Synthea, set JAVA_HOME explicitly:
     ```bash
     export JAVA_HOME="/c/Program Files/Eclipse Adoptium/jdk-17.0.18.8-hotspot"
     export PATH="$JAVA_HOME/bin:$PATH"
     ```
   - Or auto-detect: check `/c/Program Files/Eclipse Adoptium/`, `/c/Program Files/Java/`, etc.

   **Issue 3: Backslash paths break Gradle `-Params`.**
   - Gradle's Groovy parser interprets `\` as escape characters.
   - ALWAYS use **forward slashes** in all paths passed to `./gradlew`.
   - Example: `C:/repos/llm-fhir-query-eval/synthea/modules/custom` (NOT `C:\repos\...`)

4. **Run the Python helper script** (recommended):
   ```bash
   python synthea/generate_test_data.py --phenotype <phenotype> --patients 20 --controls 20
   ```
   The script auto-detects whether it's running in bash or cmd.exe and adjusts:
   - In bash: calls `./gradlew run -Params="[...]"` directly with forward-slash paths
   - In cmd.exe: calls `run_synthea.bat` as before
   - Auto-detects JAVA_HOME from common Windows install locations

5. **Or run Synthea directly via gradlew** (if script has issues):
   ```bash
   export JAVA_HOME="/c/Program Files/Eclipse Adoptium/jdk-17.0.18.8-hotspot"
   export PATH="$JAVA_HOME/bin:$PATH"

   cd C:/repos/synthea && ./gradlew run -Params="['-p','20','-m','phekb_<phenotype>','-d','C:/repos/llm-fhir-query-eval/synthea/modules/custom','--exporter.fhir.export','true','--exporter.fhir.use_us_core_ig','true','--exporter.baseDirectory','C:/repos/llm-fhir-query-eval/synthea/output/<phenotype>/positive','-s','42']"
   ```
   Then repeat with `phekb_<phenotype>_control` module and `control` output subdirectory.

6. **Report results:** Count generated files and summarize

### For `load <phenotype>`:

1. **Check FHIR server is running:**
   ```bash
   curl -s http://localhost:5826/r4/metadata | head -5
   ```

2. **Load positive cases:**
   ```bash
   for f in synthea/output/<phenotype>/positive/fhir/*.json; do
     curl -X POST http://localhost:5826/r4 \
       -H "Content-Type: application/fhir+json" \
       -d @"$f"
   done
   ```

3. **Load control cases:**
   ```bash
   for f in synthea/output/<phenotype>/control/fhir/*.json; do
     curl -X POST http://localhost:5826/r4 \
       -H "Content-Type: application/fhir+json" \
       -d @"$f"
   done
   ```

4. **Verify loaded data** by querying the server

5. **Update test case** with expected resource IDs (optional)

### For `full <phenotype>`:

Execute in sequence:
1. `create-module <phenotype>`
2. `generate <phenotype>`
3. `load <phenotype>`

Report overall success/failure.

### For `status`:

1. **List all phenotypes** from `data/phekb-raw/*/`

2. **For each, check:**
   - Has `document_analysis.json`?
   - Has module in `synthea/modules/custom/`?
   - Has generated data in `synthea/output/`?
   - Count positive/control patients

3. **Display summary table:**
   ```
   Phenotype            | Analysis | Module | Data (pos/ctrl) | Loaded
   ---------------------|----------|--------|-----------------|--------
   type-2-diabetes      | ✓        | ✓      | 20/20           | ✓
   asthma               | ✓        | ✗      | -               | -
   heart-failure        | ✓        | ✗      | -               | -
   ```

### For `list`:

List phenotypes that have Synthea modules ready:
```bash
ls synthea/modules/custom/phekb_*.json | grep -v _control
```

### For `batch <phenotypes...>`:

1. Parse the phenotype list (comma or space separated)
2. For each phenotype, run `full <phenotype>`
3. Track successes and failures
4. Report summary at end

---

## Synthea Module Template

When creating modules, use this structure:

```json
{
  "name": "PheKB <Phenotype Name>",
  "remarks": [
    "Auto-generated from PheKB phenotype: <phenotype-id>",
    "Clinical criteria: ...",
    "..."
  ],
  "states": {
    "Initial": {
      "type": "Initial",
      "direct_transition": "Age_Guard"
    },
    "Age_Guard": {
      "type": "Guard",
      "allow": { "condition_type": "Age", "operator": ">=", "quantity": 18, "unit": "years" },
      "direct_transition": "..."
    },
    "Condition_Onset": {
      "type": "ConditionOnset",
      "codes": [
        { "system": "SNOMED-CT", "code": "...", "display": "..." },
        { "system": "ICD-10-CM", "code": "...", "display": "..." }
      ],
      "direct_transition": "..."
    },
    "Lab_Observation": {
      "type": "Observation",
      "category": "laboratory",
      "codes": [{ "system": "LOINC", "code": "...", "display": "..." }],
      "unit": "...",
      "range": { "low": ..., "high": ... },
      "direct_transition": "..."
    },
    "Medication_Order": {
      "type": "MedicationOrder",
      "codes": [{ "system": "RxNorm", "code": "...", "display": "..." }],
      "direct_transition": "..."
    },
    "Terminal": {
      "type": "Terminal"
    }
  },
  "gmf_version": 2
}
```

---

## Code System URIs

| System | Synthea Name | FHIR URI |
|--------|--------------|----------|
| SNOMED CT | `SNOMED-CT` | `http://snomed.info/sct` |
| ICD-10-CM | `ICD-10-CM` | `http://hl7.org/fhir/sid/icd-10-cm` |
| ICD-9-CM | `ICD-9-CM` | `http://hl7.org/fhir/sid/icd-9-cm` |
| LOINC | `LOINC` | `http://loinc.org` |
| RxNorm | `RxNorm` | `http://www.nlm.nih.gov/research/umls/rxnorm` |

---

## Example Session

```
User: /synthea create-module asthma

Claude: I'll create a Synthea module for the asthma phenotype.

[Reads document_analysis.json and test case]
[Extracts codes: ICD-9 493.x, SNOMED 195967001, LOINC for spirometry, RxNorm for albuterol]
[Creates module with age guard, condition onset, observations, medications]
[Writes phekb_asthma.json and phekb_asthma_control.json]

Created Synthea modules for asthma:
- synthea/modules/custom/phekb_asthma.json (positive cases)
- synthea/modules/custom/phekb_asthma_control.json (controls)

To generate test data: /synthea generate asthma
```

```
User: /synthea full heart-failure

Claude: Running full pipeline for heart-failure phenotype...

Step 1/3: Creating module...
[Creates module]

Step 2/3: Generating data...
[Runs Synthea - 20 positive, 20 control patients]

Step 3/3: Loading to FHIR server...
[Loads 40 patient bundles]

Complete! Generated and loaded 40 patients for heart-failure phenotype.
- 20 positive cases (should match phenotype query)
- 20 controls (should NOT match)
```
