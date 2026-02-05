# Test Data Generation Plan

## Overview

This document outlines the strategy for generating synthetic FHIR test data for each phenotype in our test cases. We'll leverage Synthea with custom modules informed by the clinical criteria in our `document_analysis.json` and `description.txt` files.

## Goals

1. Generate FHIR-compliant test data for each phenotype
2. Create both positive cases (matching phenotype) and negative cases (control patients)
3. Ensure generated data uses correct clinical codes (LOINC, SNOMED, ICD-10, RxNorm)
4. Support execution-based evaluation against fhir-candle
5. Automate data generation from phenotype definitions

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Test Data Generation Pipeline                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────────┐     ┌─────────────────┐     ┌────────────────────┐
│ Phenotype Analyzer│     │ Synthea Module  │     │ FHIR Data Loader   │
│                   │     │ Generator       │     │                    │
│ - Read doc_analysis│    │ - Create JSON   │     │ - Load to server   │
│ - Extract criteria│     │   module files  │     │ - Validate data    │
│ - Map to codes    │     │ - Configure     │     │ - Link to tests    │
│                   │     │   demographics  │     │                    │
└───────────────────┘     └─────────────────┘     └────────────────────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────┐     ┌─────────────────┐     ┌────────────────────┐
│ data/phekb-raw/   │     │ synthea/modules/│     │ fhir-candle        │
│ {phenotype}/      │     │ custom/         │     │ localhost:5826/r4  │
│ document_analysis │     │ {phenotype}.json│     │                    │
└───────────────────┘     └─────────────────┘     └────────────────────┘
```

---

## Synthea Module Generation

### Synthea Generic Module Framework (GMF)

Synthea modules are JSON state machines that describe disease progression. Each module contains:

1. **States**: Conditions, observations, medications, procedures
2. **Transitions**: Probability-based or conditional
3. **Attributes**: Patient demographics, variables

### Module Structure

```json
{
  "name": "Type 2 Diabetes Phenotype",
  "remarks": ["Generated from PheKB phenotype definition"],
  "states": {
    "Initial": {
      "type": "Initial",
      "direct_transition": "Age_Guard"
    },
    "Age_Guard": {
      "type": "Guard",
      "allow": {
        "condition_type": "Age",
        "operator": ">=",
        "quantity": 18,
        "unit": "years"
      },
      "direct_transition": "Potential_T2DM"
    },
    "Potential_T2DM": {
      "type": "Simple",
      "distributed_transition": [
        {"distribution": 0.15, "transition": "Onset_T2DM"},
        {"distribution": 0.85, "transition": "Terminal"}
      ]
    },
    "Onset_T2DM": {
      "type": "ConditionOnset",
      "codes": [
        {
          "system": "SNOMED-CT",
          "code": "44054006",
          "display": "Type 2 diabetes mellitus"
        },
        {
          "system": "ICD-10-CM",
          "code": "E11",
          "display": "Type 2 diabetes mellitus"
        }
      ],
      "direct_transition": "HbA1c_Elevated"
    },
    "HbA1c_Elevated": {
      "type": "Observation",
      "category": "laboratory",
      "codes": [
        {
          "system": "LOINC",
          "code": "4548-4",
          "display": "Hemoglobin A1c/Hemoglobin.total in Blood"
        }
      ],
      "unit": "%",
      "range": {"low": 6.5, "high": 10.0},
      "direct_transition": "Prescribe_Metformin"
    },
    "Prescribe_Metformin": {
      "type": "MedicationOrder",
      "codes": [
        {
          "system": "RxNorm",
          "code": "6809",
          "display": "Metformin"
        }
      ],
      "direct_transition": "Terminal"
    },
    "Terminal": {
      "type": "Terminal"
    }
  }
}
```

---

## Automated Module Generation

### Phase 1: Phenotype Analysis

Extract structured data from our phenotype files:

```python
# tools/synthea_generator/phenotype_analyzer.py

from dataclasses import dataclass
from typing import List, Dict, Optional
import json

@dataclass
class PhenotypeCriteria:
    """Extracted criteria from phenotype definition."""
    phenotype_id: str
    name: str

    # Inclusion criteria
    age_range: Optional[tuple[int, int]] = None
    required_conditions: List[Dict] = None  # ICD codes
    required_observations: List[Dict] = None  # LOINC codes + thresholds
    required_medications: List[Dict] = None  # RxNorm codes

    # Exclusion criteria
    excluded_conditions: List[Dict] = None
    excluded_medications: List[Dict] = None

    # Temporal requirements
    temporal_logic: Optional[str] = None  # e.g., "med before diagnosis"

class PhenotypeAnalyzer:
    """Analyze phenotype documents and extract module criteria."""

    def analyze(self, phenotype_id: str) -> PhenotypeCriteria:
        """
        Load document_analysis.json and description.txt,
        extract criteria for Synthea module generation.
        """
        doc_analysis = self._load_document_analysis(phenotype_id)
        description = self._load_description(phenotype_id)

        return PhenotypeCriteria(
            phenotype_id=phenotype_id,
            name=doc_analysis.get("phenotype_id", phenotype_id),
            required_conditions=self._extract_conditions(doc_analysis),
            required_observations=self._extract_observations(doc_analysis),
            required_medications=self._extract_medications(doc_analysis),
            excluded_conditions=self._extract_exclusions(doc_analysis),
            age_range=self._extract_age_range(doc_analysis),
            temporal_logic=self._extract_temporal(doc_analysis)
        )

    def _extract_conditions(self, doc: Dict) -> List[Dict]:
        """Extract ICD/SNOMED condition codes."""
        conditions = []
        for code in doc.get("extracted_codes", []):
            if code["system"] in ["ICD-9-CM", "ICD-10-CM", "SNOMED-CT"]:
                conditions.append({
                    "system": self._map_system_uri(code["system"]),
                    "code": code["code"],
                    "display": code["display"],
                    "context": code.get("context", "")
                })
        return conditions

    def _extract_observations(self, doc: Dict) -> List[Dict]:
        """Extract LOINC observation codes with thresholds."""
        observations = []
        for code in doc.get("extracted_codes", []):
            if code["system"] == "LOINC":
                obs = {
                    "system": "http://loinc.org",
                    "code": code["code"],
                    "display": code["display"]
                }
                # Try to extract thresholds from clinical_criteria
                threshold = self._find_threshold(doc, code["display"])
                if threshold:
                    obs["threshold"] = threshold
                observations.append(obs)
        return observations

    def _find_threshold(self, doc: Dict, display: str) -> Optional[Dict]:
        """Find numeric threshold from clinical criteria."""
        for criteria in doc.get("clinical_criteria", []):
            # Match patterns like "HbA1c >= 6.5%"
            if display.lower() in criteria.lower():
                # Extract numeric values
                import re
                match = re.search(r'([><=]+)\s*([\d.]+)', criteria)
                if match:
                    return {
                        "operator": match.group(1),
                        "value": float(match.group(2))
                    }
        return None
```

### Phase 2: Module Template Generation

```python
# tools/synthea_generator/module_generator.py

class SyntheaModuleGenerator:
    """Generate Synthea modules from phenotype criteria."""

    def generate(self, criteria: PhenotypeCriteria) -> Dict:
        """Generate complete Synthea module JSON."""

        states = {
            "Initial": {
                "type": "Initial",
                "direct_transition": "Demographics_Check"
            }
        }

        current_state = "Demographics_Check"

        # Add age guard if specified
        if criteria.age_range:
            states["Demographics_Check"] = self._create_age_guard(
                criteria.age_range,
                next_state="Condition_Onset"
            )
        else:
            states["Demographics_Check"] = {
                "type": "Simple",
                "direct_transition": "Condition_Onset"
            }

        # Add condition onset states
        if criteria.required_conditions:
            for i, condition in enumerate(criteria.required_conditions):
                state_name = f"Condition_{i}"
                next_state = f"Condition_{i+1}" if i < len(criteria.required_conditions)-1 else "Observations"
                states[state_name] = self._create_condition_state(
                    condition, next_state
                )

        # Add observation states
        if criteria.required_observations:
            for i, obs in enumerate(criteria.required_observations):
                state_name = f"Observation_{i}"
                next_state = f"Observation_{i+1}" if i < len(criteria.required_observations)-1 else "Medications"
                states[state_name] = self._create_observation_state(
                    obs, next_state
                )

        # Add medication states
        if criteria.required_medications:
            for i, med in enumerate(criteria.required_medications):
                state_name = f"Medication_{i}"
                next_state = f"Medication_{i+1}" if i < len(criteria.required_medications)-1 else "Terminal"
                states[state_name] = self._create_medication_state(
                    med, next_state
                )

        states["Terminal"] = {"type": "Terminal"}

        return {
            "name": f"{criteria.name} Phenotype",
            "remarks": [
                f"Auto-generated from PheKB phenotype: {criteria.phenotype_id}",
                "For testing FHIR query generation"
            ],
            "states": states
        }

    def _create_condition_state(self, condition: Dict, next_state: str) -> Dict:
        return {
            "type": "ConditionOnset",
            "codes": [{
                "system": condition["system"],
                "code": condition["code"],
                "display": condition["display"]
            }],
            "direct_transition": next_state
        }

    def _create_observation_state(self, obs: Dict, next_state: str) -> Dict:
        state = {
            "type": "Observation",
            "category": "laboratory",
            "codes": [{
                "system": obs["system"],
                "code": obs["code"],
                "display": obs["display"]
            }],
            "direct_transition": next_state
        }

        # Add value range based on threshold
        if "threshold" in obs:
            threshold = obs["threshold"]
            if ">=" in threshold["operator"]:
                state["range"] = {
                    "low": threshold["value"],
                    "high": threshold["value"] * 1.5
                }
            elif "<=" in threshold["operator"]:
                state["range"] = {
                    "low": threshold["value"] * 0.5,
                    "high": threshold["value"]
                }

        return state

    def _create_medication_state(self, med: Dict, next_state: str) -> Dict:
        return {
            "type": "MedicationOrder",
            "codes": [{
                "system": med["system"],
                "code": med["code"],
                "display": med["display"]
            }],
            "direct_transition": next_state
        }
```

### Phase 3: Control Patient Generation

Generate patients who do NOT match the phenotype:

```python
# tools/synthea_generator/control_generator.py

class ControlModuleGenerator:
    """Generate Synthea modules for control (non-matching) patients."""

    def generate(self, criteria: PhenotypeCriteria) -> Dict:
        """
        Generate module for control patients who:
        1. Have SOME related conditions but not all criteria
        2. Have conditions from exclusion list
        3. Are outside age range
        """

        # Strategy: Create patients with partial criteria
        return {
            "name": f"{criteria.name} Control",
            "remarks": ["Control patients for phenotype testing"],
            "states": {
                "Initial": {
                    "type": "Initial",
                    "distributed_transition": [
                        {"distribution": 0.33, "transition": "Age_Excluded"},
                        {"distribution": 0.33, "transition": "Has_Exclusion"},
                        {"distribution": 0.34, "transition": "Partial_Criteria"}
                    ]
                },
                "Age_Excluded": self._create_age_excluded(criteria),
                "Has_Exclusion": self._create_exclusion_state(criteria),
                "Partial_Criteria": self._create_partial_state(criteria),
                "Terminal": {"type": "Terminal"}
            }
        }
```

---

## Data Generation Pipeline

### Step 1: Generate Modules for All Phenotypes

```bash
# CLI command
fhir-eval synthea generate-modules --all

# Or for specific phenotype
fhir-eval synthea generate-modules --phenotype asthma
```

### Step 2: Run Synthea with Custom Modules

```bash
# Run Synthea with phenotype-specific module
java -jar synthea-with-dependencies.jar \
  -p 50 \                              # 50 patients
  -m phenotype_t2dm \                  # Module name
  --exporter.fhir.export=true \        # Export as FHIR
  --exporter.fhir.bulk_data=false \
  --exporter.baseDirectory=output/t2dm/
```

### Step 3: Load Data to FHIR Server

```python
# tools/data_loader.py

class FHIRDataLoader:
    """Load Synthea output to FHIR server."""

    def __init__(self, base_url: str = "http://localhost:5826/r4"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def load_bundle(self, bundle_path: Path):
        """Load a FHIR Bundle to the server."""
        with open(bundle_path) as f:
            bundle = json.load(f)

        response = await self.client.post(
            self.base_url,
            json=bundle,
            headers={"Content-Type": "application/fhir+json"}
        )
        return response.json()

    async def load_all_patients(self, output_dir: Path):
        """Load all patient bundles from Synthea output."""
        for bundle_file in output_dir.glob("*.json"):
            await self.load_bundle(bundle_file)
```

### Step 4: Link Test Data to Test Cases

```python
# Update test case with generated data references

def link_test_data(test_case: TestCase, patients: List[str], expected_matches: List[str]):
    """Link generated test data to test case."""
    test_case.test_data = TestData(
        resources=patients,
        expected_result_count=len(expected_matches),
        expected_resource_ids=expected_matches
    )
    return test_case
```

---

## Code System Mapping

### ICD-9 to ICD-10 Mapping

Many PheKB phenotypes use ICD-9 codes. We need mapping to ICD-10:

```python
# tools/code_mapper.py

class CodeMapper:
    """Map between code systems."""

    # Common diabetes codes
    ICD9_TO_ICD10 = {
        "250.00": "E11.9",   # T2DM without complications
        "250.01": "E10.9",   # T1DM without complications
        "493.00": "J45.20",  # Mild intermittent asthma
        "493.90": "J45.909", # Asthma, unspecified
        "401.9": "I10",      # Essential hypertension
    }

    def map_icd9_to_icd10(self, icd9_code: str) -> Optional[str]:
        """Map ICD-9 to ICD-10-CM code."""
        # Use GEMs (General Equivalence Mappings) or lookup table
        return self.ICD9_TO_ICD10.get(icd9_code)

    def expand_icd_code(self, code: str) -> List[str]:
        """Expand truncated code to all children."""
        # e.g., "250" -> ["250.00", "250.01", "250.02", ...]
        pass
```

### Code System URIs

| System | URI | Example |
|--------|-----|---------|
| ICD-9-CM | `http://hl7.org/fhir/sid/icd-9-cm` | 250.00 |
| ICD-10-CM | `http://hl7.org/fhir/sid/icd-10-cm` | E11.9 |
| SNOMED CT | `http://snomed.info/sct` | 44054006 |
| LOINC | `http://loinc.org` | 4548-4 |
| RxNorm | `http://www.nlm.nih.gov/research/umls/rxnorm` | 6809 |

---

## Test Data Requirements by Phenotype

### Example: Type 2 Diabetes

From `document_analysis.json`:

```json
{
  "clinical_criteria": [
    "Random glucose > 200 mg/dl (for T2DM cases)",
    "Fasting glucose >= 125 mg/dl (for T2DM cases)",
    "Hemoglobin A1c >= 6.5% (for T2DM cases)",
    "At least 2 physician-entered T2DM diagnoses required",
    "T2DM medication prescribed before T1DM medication"
  ]
}
```

**Required Test Patients:**

| Type | Count | Characteristics |
|------|-------|-----------------|
| Positive (match) | 10 | All criteria met, HbA1c 7-10%, on metformin |
| Partial match | 5 | HbA1c elevated but no diagnosis code |
| Exclusion | 5 | Has T1DM diagnosis (excluded) |
| Control | 10 | Normal labs, no diabetes codes |

### Example: Asthma

From `document_analysis.json`:

```json
{
  "clinical_criteria": [
    "Age >= 4 years",
    "Multiple asthma diagnoses from separate visits",
    "Asthma medication prescribed",
    "No cystic fibrosis, COPD, or organ transplant"
  ]
}
```

**Required Test Patients:**

| Type | Count | Characteristics |
|------|-------|-----------------|
| Positive (match) | 10 | Age 10-50, multiple J45 codes, albuterol Rx |
| Age excluded | 5 | Age 2-3, has asthma codes |
| Condition excluded | 5 | Has COPD or CF codes |
| Control | 10 | No respiratory diagnoses |

---

## Directory Structure

```
synthea/
├── modules/
│   └── custom/
│       ├── phekb_type_2_diabetes.json
│       ├── phekb_type_2_diabetes_control.json
│       ├── phekb_asthma.json
│       ├── phekb_asthma_control.json
│       └── ... (one per phenotype)
├── output/
│   ├── type-2-diabetes/
│   │   └── fhir/*.json
│   ├── asthma/
│   │   └── fhir/*.json
│   └── ...
└── config/
    └── synthea.properties

test-data/
├── type-2-diabetes/
│   ├── positive/
│   │   └── bundle.json
│   ├── control/
│   │   └── bundle.json
│   └── manifest.json
├── asthma/
│   └── ...
└── ...
```

---

## CLI Commands

```bash
# Generate Synthea module from phenotype
fhir-eval synthea generate-module asthma

# Generate all modules
fhir-eval synthea generate-modules --all

# Generate test data with Synthea
fhir-eval synthea generate-data asthma --patients 30

# Load test data to FHIR server
fhir-eval data load --phenotype asthma

# Load all test data
fhir-eval data load --all

# Verify test data matches expected counts
fhir-eval data verify asthma

# Link test data to test cases
fhir-eval data link-tests
```

---

## Alternative Approaches

### Option A: Pure Synthea (Recommended)

**Pros:**
- Well-established, widely used
- Generates realistic longitudinal data
- Built-in FHIR export
- Community modules available

**Cons:**
- Java-based, adds dependency
- Module creation has learning curve
- May generate more data than needed

### Option B: Direct FHIR Bundle Generation

**Pros:**
- Simpler, no external dependencies
- Full control over exact resources
- Faster for small datasets

**Cons:**
- Less realistic data
- No longitudinal history
- More manual work per phenotype

### Option C: Hybrid Approach

Use Synthea base population, then:
1. Filter patients to phenotype criteria
2. Augment with specific test cases
3. Create targeted edge cases manually

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Phenotype analyzer implementation
- [ ] Module generator skeleton
- [ ] CLI commands for module generation

### Phase 2: Synthea Integration (Week 2)
- [ ] Synthea Docker setup
- [ ] Module validation
- [ ] Batch generation scripts

### Phase 3: Data Loading (Week 3)
- [ ] FHIR loader implementation
- [ ] Test case linking
- [ ] Data verification

### Phase 4: Full Pipeline (Week 4)
- [ ] End-to-end automation
- [ ] All phenotypes generated
- [ ] Integration tests

---

## Sources

- [Synthea Documentation](https://synthetichealth.github.io/synthea/)
- [Synthea GitHub](https://github.com/synthetichealth/synthea)
- [Generic Module Framework Wiki](https://github.com/synthetichealth/synthea/wiki/Generic-Module-Framework)
- [FHIR for Research - Synthea Overview](https://mitre.github.io/fhir-for-research/modules/synthea-overview)
- [Synthea Module Builder](https://synthetichealth.github.io/module-builder/)
