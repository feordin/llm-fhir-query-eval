---
name: umls
description: "Look up clinical codes, map between code systems (SNOMED, ICD-10, LOINC, RxNorm), search VSAC value sets, and check code subsumption using the NIH UMLS MCP server."
allowed-tools: mcp__nih-umls__search_umls, mcp__nih-umls__get_concept, mcp__nih-umls__get_concept_relations, mcp__nih-umls__get_definitions, mcp__nih-umls__get_source_concept, mcp__nih-umls__crosswalk_codes, mcp__nih-umls__search_value_sets, mcp__nih-umls__get_value_set, mcp__nih-umls__expand_value_set, mcp__nih-umls__validate_code_in_value_set, mcp__nih-umls__lookup_code, mcp__nih-umls__check_code_subsumption, Read, Glob
---

# UMLS Code Lookup Skill

## Usage

```
/umls <command> <term-or-code>
```

## Commands

| Command | Description |
|---------|-------------|
| `lookup <term>` | Find codes for a clinical concept (e.g., "atrial fibrillation") |
| `crosswalk <system> <code>` | Map a code to other code systems |
| `codes-for <term>` | Get all FHIR-relevant codes for a concept (SNOMED, ICD-10, LOINC, RxNorm) |
| `validate <system> <code>` | Check if a code exists and get its display name |
| `valueset <term>` | Search VSAC for curated value sets by name |
| `expand <oid>` | Expand a value set to see all member codes |
| `validate-in-vs <oid> <system> <code>` | Check if a code belongs to a value set |
| `subsumes <system> <code_a> <code_b>` | Check hierarchical code relationships (e.g., SNOMED parent/child) |

## Instructions for Claude

### General Workflow

The UMLS MCP server provides five tools. Use them in this order for best results:

1. **`search_umls`** - Find the UMLS CUI (Concept Unique Identifier) for a term
2. **`get_concept`** - Get details about a CUI (semantic type, atom count)
3. **`get_definitions`** - Get clinical definitions (useful for disambiguation)
4. **`crosswalk_codes`** - Map between code systems via a known code
5. **`get_source_concept`** - Get details about a specific code in a specific system
6. **`search_value_sets`** - Search VSAC for curated value sets (quality measure code lists, CMS groupings)
7. **`expand_value_set`** - Get all codes in a value set (replaces manual crosswalking for known value sets)
8. **`validate_code_in_value_set`** - Check if a code belongs to a standard value set
9. **`lookup_code`** - Look up code details using FHIR-native system URIs (no UMLS abbreviation translation needed)
10. **`check_code_subsumption`** - Check parent/child relationships in hierarchical systems like SNOMED CT

### For `lookup <term>`:

1. **Search UMLS** for the term:
   ```
   search_umls(query="<term>", search_type="exact")
   ```
   If no results, fall back to `search_type="words"` then `"approximate"`.

2. **Identify the correct CUI.** Look for:
   - Semantic type "Disease or Syndrome" for conditions
   - Semantic type "Laboratory Procedure" or "Clinical Attribute" for labs
   - Semantic type "Pharmacologic Substance" for medications
   - Avoid CUIs with semantic type "Finding" unless that's what you need

3. **Get concept details:**
   ```
   get_concept(cui="<CUI>")
   ```

4. **Report** the CUI, preferred name, and semantic type.

### For `crosswalk <system> <code>`:

1. **Call crosswalk_codes** with the source system and code:
   ```
   crosswalk_codes(source="<SYSTEM>", code="<CODE>")
   ```

   Valid source vocabulary abbreviations:
   | Common Name | UMLS Abbreviation |
   |-------------|-------------------|
   | SNOMED CT | `SNOMEDCT_US` |
   | ICD-10-CM | `ICD10CM` |
   | ICD-9-CM | `ICD9CM` |
   | LOINC | `LOINC` |
   | RxNorm | `RXNORM` |
   | CPT | `CPT` |
   | HCPCS | `HCPCS` |
   | ICD-10-PCS | `ICD10PCS` |
   | NDC | `NDC` |

2. **Filter by target** if needed:
   ```
   crosswalk_codes(source="SNOMEDCT_US", code="49436004", target_source="ICD10CM")
   ```

3. **Important crosswalk behavior:**
   - Crosswalk only finds codes sharing the **same UMLS concept (CUI)**
   - ICD-10 often splits concepts into subtypes (e.g., atrial fibrillation → paroxysmal, persistent, unspecified) that live under **different CUIs**
   - If a crosswalk returns empty, the target system may classify the concept differently
   - In that case, search UMLS for the term again and look for system-specific matches

4. **If crosswalk returns empty**, try the reverse approach:
   - Search UMLS for the clinical term
   - Look through results for entries from the target code system
   - Or try crosswalking from ICD-9 (broader codes) to the target

### For `codes-for <term>`:

This is the most common use case — getting all FHIR-relevant codes for a clinical concept.

1. **Search UMLS** with exact match first, then words:
   ```
   search_umls(query="<term>", search_type="exact")
   ```

2. **Pick the primary CUI** (usually "Disease or Syndrome" for conditions).

3. **Get codes from multiple systems.** For each relevant code system, try crosswalking from a known code. The most reliable approach:

   a. First, find a SNOMED code (usually the most connected):
      ```
      get_source_concept(source="SNOMEDCT_US", id="<SNOMED_CODE>")
      ```

   b. Then crosswalk to each target system:
      ```
      crosswalk_codes(source="SNOMEDCT_US", code="<CODE>", target_source="ICD10CM")
      crosswalk_codes(source="SNOMEDCT_US", code="<CODE>", target_source="ICD9CM")
      crosswalk_codes(source="SNOMEDCT_US", code="<CODE>", target_source="RXNORM")
      ```

   c. If crosswalks return empty, search UMLS directly with target system filter.

   3b. **Alternative: Use VSAC value sets** for comprehensive code lists.

   For well-known clinical concepts, VSAC value sets provide pre-curated, authoritative code lists:
   ```
   search_value_sets(title="<term>")
   expand_value_set(oid="<oid from search>")
   ```

   This is especially useful for:
   - Quality measure code lists (CMS, HEDIS, NCQA)
   - Conditions with many ICD-10 subtypes (e.g., diabetes E11.0-E11.9)
   - Getting ALL valid codes including ones that crosswalk might miss

4. **Present results as a table:**

   ```
   | System | Code | Display | FHIR URI |
   |--------|------|---------|----------|
   | SNOMED CT | 49436004 | Atrial fibrillation | http://snomed.info/sct |
   | ICD-10-CM | I48.91 | Unspecified atrial fibrillation | http://hl7.org/fhir/sid/icd-10-cm |
   | ICD-9-CM | 427.31 | Atrial fibrillation | http://hl7.org/fhir/sid/icd-9-cm |
   ```

5. **Include FHIR query examples:**
   ```
   Condition?code=http://snomed.info/sct|49436004
   Condition?code=http://hl7.org/fhir/sid/icd-10-cm|I48.91
   ```

### For `validate <system> <code>`:

1. **Get the source concept:**
   ```
   get_source_concept(source="<SYSTEM>", id="<CODE>")
   ```

2. **Report** whether the code exists, its display name, and whether it's obsolete.

### For `valueset <term>`:

1. **Search VSAC** for value sets matching the term:
   ```
   search_value_sets(title="<term>")
   ```

2. **Present results** as a table:
   | OID | Title | Publisher | Status |

3. **Suggest next steps**: Use `/umls expand <oid>` to see all codes in a value set.

**When to use value sets vs crosswalk:**
- Use **value sets** when you need a comprehensive grouping of codes for a clinical concept (e.g., "all diabetes codes" for quality reporting)
- Use **crosswalk** when you need exact concept-level equivalence between two specific codes
- Value sets may include codes from multiple UMLS concepts (e.g., a "Diabetes" value set includes Type 1, Type 2, gestational, etc.)

### For `expand <oid>`:

1. **Expand the value set:**
   ```
   expand_value_set(oid="<oid>", count=100)
   ```

2. **Present results** grouped by code system:
   ```
   Value Set: <title> (<oid>)
   Total codes: <count>

   SNOMED CT:
   | Code | Display |
   |------|---------|
   | ...  | ...     |

   ICD-10-CM:
   | Code | Display |
   |------|---------|
   | ...  | ...     |
   ```

3. **For large value sets** (100+ codes), note that pagination is available:
   ```
   expand_value_set(oid="<oid>", count=100, offset=100)
   ```

4. **Include FHIR query examples** showing how to use the codes.

### For `validate-in-vs <oid> <system> <code>`:

1. **Validate the code:**
   ```
   validate_code_in_value_set(oid="<oid>", code="<code>", system="<system>")
   ```
   System uses FHIR URIs (e.g., `http://snomed.info/sct`, `http://hl7.org/fhir/sid/icd-10-cm`).

2. **Report** whether the code is a member and its display name.

### For `subsumes <system> <code_a> <code_b>`:

1. **Check subsumption:**
   ```
   check_code_subsumption(system="<system>", code_a="<code_a>", code_b="<code_b>")
   ```
   System uses FHIR URIs (e.g., `http://snomed.info/sct`).

2. **Interpret the result:**
   - `subsumes` — code_a is an ancestor of code_b (code_a is broader)
   - `subsumed-by` — code_a is a descendant of code_b (code_a is narrower)
   - `equivalent` — both codes represent the same concept
   - `not-subsumed` — no hierarchical relationship

3. **Explain in clinical context:** For example, "SNOMED 73211009 (Diabetes mellitus) subsumes 44054006 (Type 2 diabetes mellitus), meaning a query for the broader code would also match the narrower one if the server supports `:below` modifier."

4. **Note:** Subsumption checking is primarily useful for hierarchical code systems like SNOMED CT. It is not applicable to flat code systems like ICD-10-CM or LOINC.

---

## FHIR Code System URI Reference

| System | UMLS Abbreviation | FHIR URI | Synthea Name |
|--------|-------------------|----------|--------------|
| SNOMED CT | `SNOMEDCT_US` | `http://snomed.info/sct` | `SNOMED-CT` |
| ICD-10-CM | `ICD10CM` | `http://hl7.org/fhir/sid/icd-10-cm` | `ICD-10-CM` |
| ICD-9-CM | `ICD9CM` | `http://hl7.org/fhir/sid/icd-9-cm` | `ICD-9-CM` |
| LOINC | `LOINC` | `http://loinc.org` | `LOINC` |
| RxNorm | `RXNORM` | `http://www.nlm.nih.gov/research/umls/rxnorm` | `RxNorm` |
| CPT | `CPT` | `http://www.ama-assn.org/go/cpt` | `CPT` |
| NDC | `NDC` | `http://hl7.org/fhir/sid/ndc` | - |

---

## Tips and Gotchas

### Crosswalk Gaps

The UMLS crosswalk maps codes that share the **same CUI**. This means:
- **SNOMED → ICD-9** usually works well (both have broad concepts)
- **SNOMED → ICD-10** often returns empty because ICD-10 splits conditions into specificity levels (laterality, severity, type) that are separate CUIs
- **ICD-10 → SNOMED** works better in reverse for specific ICD-10 codes

**Workaround for empty crosswalks:** Search UMLS for the term with `search_type="words"`, then look at which CUIs have atoms from your target system.

### Obsolete Codes

SNOMED regularly retires codes. The crosswalk may return obsolete codes (marked `"obsolete": true`). Always check this field and prefer active codes.

### Multiple Codes per Concept

Many conditions have multiple valid codes in the same system (e.g., ICD-10 has `I48.0` paroxysmal, `I48.1` persistent, `I48.2` chronic, `I48.91` unspecified for atrial fibrillation). For FHIR queries that should catch all variants, consider using multiple codes or the unspecified/general code.

### VSAC Value Sets vs UMLS Crosswalk

These are complementary approaches for finding codes:

| Approach | Best For | How It Works |
|----------|----------|-------------|
| **UMLS Crosswalk** | Exact concept equivalence | Finds codes sharing the same CUI (concept-level mapping) |
| **VSAC Value Sets** | Comprehensive clinical groupings | Curated collections maintained by organizations (NCQA, CMS) |

Key differences:
- A **crosswalk** for "Type 2 diabetes" finds the exact equivalent codes in other systems
- A **value set** for "Diabetes" may include Type 1, Type 2, gestational, and other subtypes
- Value sets are authoritative for quality reporting and are regularly updated
- Crosswalk may miss codes that are semantically related but have different CUIs

**Recommendation:** Use VSAC value sets when available for the clinical concept. Fall back to crosswalk for niche concepts not covered by standard value sets.

---

## Example Sessions

```
User: /umls lookup type 2 diabetes

Claude: Searching UMLS for "type 2 diabetes"...

Found: C0011860 - Diabetes Mellitus, Type 2 (Disease or Syndrome)

Key codes:
| System | Code | Display |
|--------|------|---------|
| SNOMED CT | 44054006 | Type 2 diabetes mellitus |
| ICD-10-CM | E11 | Type 2 diabetes mellitus |
| ICD-9-CM | 250.00 | Diabetes mellitus type II |

FHIR query: Condition?code=http://snomed.info/sct|44054006
```

```
User: /umls crosswalk SNOMEDCT_US 195967001

Claude: Crosswalking SNOMED CT code 195967001...

Source: 195967001 - Asthma (SNOMED CT)

Mapped codes:
| System | Code | Display |
|--------|------|---------|
| ICD-9-CM | 493.90 | Asthma, unspecified |
| ... | ... | ... |
```

```
User: /umls codes-for hemoglobin A1c

Claude: Finding all codes for "hemoglobin A1c"...

| System | Code | Display | FHIR URI |
|--------|------|---------|----------|
| LOINC | 4548-4 | Hemoglobin A1c/Hemoglobin.total in Blood | http://loinc.org |
| LOINC | 4549-2 | Hemoglobin A1c/Hemoglobin.total in Blood by Electrophoresis | http://loinc.org |

FHIR query: Observation?code=http://loinc.org|4548-4
```

```
User: /umls valueset diabetes

Claude: Searching VSAC for "diabetes" value sets...

Found 15 value sets. Top results:
| OID | Title | Publisher |
|-----|-------|-----------|
| 2.16.840.1.113883.3.464.1003.103.12.1001 | Diabetes | NCQA |
| 2.16.840.1.113883.3.464.1003.103.12.1020 | Type 1 Diabetes | NCQA |
| ... | ... | ... |

Use `/umls expand <oid>` to see all codes in a value set.
```

```
User: /umls expand 2.16.840.1.113883.3.464.1003.103.12.1001

Claude: Expanding value set "Diabetes" (2.16.840.1.113883.3.464.1003.103.12.1001)...

Total codes: 47

SNOMED CT (http://snomed.info/sct):
| Code | Display |
|------|---------|
| 44054006 | Type 2 diabetes mellitus |
| 46635009 | Type 1 diabetes mellitus |
| ... | ... |

ICD-10-CM (http://hl7.org/fhir/sid/icd-10-cm):
| Code | Display |
|------|---------|
| E11 | Type 2 diabetes mellitus |
| E11.9 | Type 2 diabetes mellitus without complications |
| E10 | Type 1 diabetes mellitus |
| ... | ... |
```

```
User: /umls subsumes http://snomed.info/sct 73211009 44054006

Claude: Checking subsumption in SNOMED CT...

Result: **subsumes**

73211009 (Diabetes mellitus) is an ancestor of 44054006 (Type 2 diabetes mellitus).

This means:
- A FHIR query using code 73211009 with the `:below` modifier would match patients coded with 44054006
- Use the broader code (73211009) if you want ALL diabetes types
- Use the narrower code (44054006) if you want only Type 2
```
