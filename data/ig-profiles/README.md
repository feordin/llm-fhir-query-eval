# Implementation Guide Profile Data

Pre-downloaded IG profiles for use in LLM evaluation (Tier 3: Skill-Guided).

## Available IGs

### US Core 6.1.0
- **Source format**: JSON (from `HL7/US-Core` GitHub repo, tag `6.1.0`)
- **FSH conversion**: Available in `us-core-6.1.0/fsh/` (generated via `goFSH`)
- **Status**: Widely deployed, still in use by many systems

### US Core 8.0.1
- **Source format**: YAML (from `HL7/US-Core` GitHub repo, branch `8.0.1`)
- **FSH conversion**: Not available (goFSH doesn't handle YAML source well; YAML is readable enough)
- **Status**: Current version

## Key Differences Between Versions

### Condition.code ValueSet

| Version | SNOMED CT | ICD-10-CM | ICD-9-CM |
|---------|:-:|:-:|:-:|
| US Core 6.1.0 | Yes | Yes | **Yes** |
| US Core 8.0.1 | Yes | Yes | **Removed** |

This is critical for evaluation: an LLM querying a US Core 8 server should NOT use ICD-9 codes.

### Binding Changes

| Element | US Core 6.1.0 | US Core 8.0.1 |
|---------|--------------|--------------|
| Condition.code | extensible (us-core-condition-code) | preferred + "current" additional binding (us-core-condition-code-current, excludes ICD-9) |
| MedicationRequest.medication[x] | extensible (VSAC OID 2.16.840.1.113762.1.4.1010.4) | Same |
| Observation.code (labs) | extensible (us-core-laboratory-test-codes = LOINC) | Same |

## Format Preference for LLM Context

**FSH > YAML > JSON**

- FSH: ~76 lines for the Condition profile (see `us-core-6.1.0/fsh/`)
- YAML: ~180 lines for the same profile (see `us-core-8.0.1/`)
- JSON: ~12,000+ characters for the same profile

For LLM context windows, FSH uses ~5-10x fewer tokens than JSON.

## How to Download More IGs

```bash
# 1. Check the IG's GitHub repo for source format
gh api repos/HL7/<ig-name>/git/trees/<tag>?recursive=1 --jq '.tree[].path' | grep -E "\.fsh$|\.yml$"

# 2. Download profiles and valuesets (prefer FSH/YAML)
# 3. If only JSON available, convert with goFSH:
npx gofsh <json-directory> -o <output>/fsh/ --no-alias
```
