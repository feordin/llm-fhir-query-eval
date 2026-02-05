# Synthea Test Data Generation

This directory contains custom Synthea modules for generating synthetic FHIR test data based on PheKB phenotypes.

## Directory Structure

```
synthea/
├── modules/
│   └── custom/
│       ├── phekb_type_2_diabetes.json       # T2DM positive cases
│       └── phekb_type_2_diabetes_control.json # T2DM negative controls
├── output/                                   # Generated FHIR bundles
├── config/                                   # Synthea configuration
└── README.md
```

## Prerequisites

1. **Java 11+** - Synthea requires Java
2. **Synthea JAR** - Download from [GitHub releases](https://github.com/synthetichealth/synthea/releases)

## Quick Start

### 1. Download Synthea

```bash
# Download latest Synthea release
curl -L -o synthea-with-dependencies.jar \
  https://github.com/synthetichealth/synthea/releases/latest/download/synthea-with-dependencies.jar
```

### 2. Generate T2DM Positive Cases

```bash
java -jar synthea-with-dependencies.jar \
  -p 20 \
  -m phekb_type_2_diabetes \
  -d modules/custom \
  --exporter.fhir.export=true \
  --exporter.fhir.use_us_core_ig=true \
  --exporter.baseDirectory=output/type-2-diabetes/positive
```

### 3. Generate Control Patients (Non-Diabetic)

```bash
java -jar synthea-with-dependencies.jar \
  -p 20 \
  -m phekb_type_2_diabetes_control \
  -d modules/custom \
  --exporter.fhir.export=true \
  --exporter.fhir.use_us_core_ig=true \
  --exporter.baseDirectory=output/type-2-diabetes/control
```

## Module Design

### Type 2 Diabetes Module (`phekb_type_2_diabetes.json`)

Based on PheKB phenotype definition with clinical criteria:

**Diagnosis Codes:**
- SNOMED-CT: 44054006 (Type 2 diabetes mellitus)
- ICD-10-CM: E11, E11.9 (Type 2 diabetes mellitus)
- ICD-9-CM: 250.00 (Diabetes mellitus without complication, type II)

**Laboratory Values:**
- HbA1c: 6.5-10.0% (LOINC 4548-4)
- Fasting glucose: 126-250 mg/dL (LOINC 1558-6)
- Random glucose: 200-350 mg/dL (LOINC 2339-0)

**Medications:**
- Metformin (RxNorm 6809) - first-line
- Glipizide (RxNorm 4821) - sulfonylurea
- Sitagliptin (RxNorm 593411) - DPP-4 inhibitor

### Control Module (`phekb_type_2_diabetes_control.json`)

Generates patients who should NOT match T2DM criteria:

**Laboratory Values (Normal):**
- HbA1c: 4.5-5.6% (below prediabetes threshold)
- Fasting glucose: 70-99 mg/dL (normal)
- Random glucose: 80-139 mg/dL (normal)

**No diabetes-related:**
- No diabetes diagnosis codes
- No diabetes medications

**May have other conditions:**
- Hypertension (30%)
- Hyperlipidemia (25%)
- No conditions (45%)

## Loading to FHIR Server

After generating data, load to fhir-candle:

```bash
# Start FHIR server
docker-compose up -d fhir-candle

# Load bundles (example using curl)
for f in output/type-2-diabetes/positive/fhir/*.json; do
  curl -X POST http://localhost:5826/r4 \
    -H "Content-Type: application/fhir+json" \
    -d @"$f"
done

for f in output/type-2-diabetes/control/fhir/*.json; do
  curl -X POST http://localhost:5826/r4 \
    -H "Content-Type: application/fhir+json" \
    -d @"$f"
done
```

## Expected Test Results

For the test case `phekb-type-2-diabetes.json`:

**Query:** `Condition?code=http://snomed.info/sct|44054006`

**Expected:**
- Should return: All patients from `positive/` directory
- Should NOT return: Any patients from `control/` directory

## Synthea Command Reference

| Option | Description |
|--------|-------------|
| `-p N` | Generate N patients |
| `-m MODULE` | Run specific module only |
| `-d PATH` | Custom modules directory |
| `--exporter.fhir.export=true` | Enable FHIR R4 export |
| `--exporter.fhir.use_us_core_ig=true` | Use US Core profiles |
| `--exporter.baseDirectory=PATH` | Output directory |
| `-s SEED` | Random seed for reproducibility |

## Validation

To validate generated data matches phenotype criteria:

```bash
# Check for diabetes diagnoses in positive cases
grep -l "44054006" output/type-2-diabetes/positive/fhir/*.json | wc -l

# Verify no diabetes in control cases
grep -l "44054006" output/type-2-diabetes/control/fhir/*.json | wc -l
# Should be 0
```

## Adding New Phenotype Modules

1. Copy template from existing module
2. Update codes from `data/phekb-raw/{phenotype}/document_analysis.json`
3. Adjust clinical criteria thresholds
4. Create both positive and control modules
5. Test generation and validate output

## Resources

- [Synthea Wiki](https://github.com/synthetichealth/synthea/wiki)
- [Generic Module Framework](https://github.com/synthetichealth/synthea/wiki/Generic-Module-Framework)
- [Module Builder](https://synthetichealth.github.io/module-builder/)
- [PheKB](https://phekb.org/)
