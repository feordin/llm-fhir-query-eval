# Example FHIR Query Agent Prompts

These examples show the types of natural language prompts the agent handles
and the expected FHIR queries it should produce.

---

## 1. Condition Query (Diagnosis)

**Prompt:**
> Find all patients with a diagnosis of type 2 diabetes mellitus

**Expected workflow:**
1. `umls_search("type 2 diabetes mellitus")` -> SNOMED 44054006, ICD-10 E11
2. `fhir_resource_sample("Condition")` -> sees SNOMED codes in use
3. `fhir_search("Condition?code=http://snomed.info/sct|44054006")` -> confirms results

**Expected query:**
```
Condition?code=http://snomed.info/sct|44054006
```

---

## 2. MedicationRequest Query (Medications)

**Prompt:**
> Find all active prescriptions for metformin

**Expected workflow:**
1. `umls_search("metformin")` -> RxNorm 6809 (ingredient)
2. `fhir_resource_sample("MedicationRequest")` -> sees RxNorm SCD-level codes
3. `fhir_search("MedicationRequest?code=http://www.nlm.nih.gov/research/umls/rxnorm|6809")` -> 0 results (ingredient code not in data)
4. `umls_crosswalk("RXNORM", "6809", "RXNORM")` -> finds SCD codes like 860975
5. `fhir_search("MedicationRequest?code=http://www.nlm.nih.gov/research/umls/rxnorm|860975&status=active")` -> confirms results

**Expected query:**
```
MedicationRequest?code=http://www.nlm.nih.gov/research/umls/rxnorm|860975&status=active
```

Note: The exact RxNorm SCD code depends on what is loaded in the server.
The agent discovers this through sampling and crosswalking.

---

## 3. Observation Query with Value Filter (Labs)

**Prompt:**
> Find all HbA1c lab results greater than 9%

**Expected workflow:**
1. `umls_search("hemoglobin A1c")` -> LOINC 4548-4
2. `fhir_resource_sample("Observation")` -> confirms LOINC codes in use
3. `fhir_search("Observation?code=http://loinc.org|4548-4&value-quantity=gt9")` -> checks results

**Expected query:**
```
Observation?code=http://loinc.org|4548-4&value-quantity=gt9||%25
```

---

## 4. Multi-Resource Query (Comprehensive)

**Prompt:**
> Find patients diagnosed with type 2 diabetes who have an HbA1c above 8% and are on metformin

**Expected queries (one per resource type):**
```
Condition?code=http://snomed.info/sct|44054006
Observation?code=http://loinc.org|4548-4&value-quantity=gt8
MedicationRequest?code=http://www.nlm.nih.gov/research/umls/rxnorm|860975
```

The agent should explain that these queries need to be joined by patient reference
in application logic, or suggest using `_has` chaining if the server supports it.

---

## 5. Cross-Resource `_has` Query

**Prompt:**
> Find patients who have both a diabetes diagnosis and are on insulin

**Expected workflow:**
1. Look up diabetes codes (SNOMED 44054006)
2. Look up insulin codes (RxNorm, check server for specific formulations)
3. Sample both Condition and MedicationRequest resources
4. Attempt a `_has` query if supported

**Expected query (if server supports `_has`):**
```
Patient?_has:Condition:patient:code=http://snomed.info/sct|44054006&_has:MedicationRequest:patient:code=http://www.nlm.nih.gov/research/umls/rxnorm|253182
```

**Fallback (separate queries):**
```
Condition?code=http://snomed.info/sct|44054006
MedicationRequest?code=http://www.nlm.nih.gov/research/umls/rxnorm|253182
```

---

## 6. Encounter Query with Date Range

**Prompt:**
> Find all emergency department visits in the last year

**Expected workflow:**
1. `umls_search("emergency department visit")` -> SNOMED 4525004
2. `fhir_resource_sample("Encounter")` -> check encounter type codes
3. Construct query with date filter

**Expected query:**
```
Encounter?type=http://snomed.info/sct|4525004&date=ge2025-03-15
```

---

## Tips for Best Results

1. **Be specific about what you want**: "Find patients with type 2 diabetes" works better than "diabetes patients"
2. **Mention resource types if you know them**: "Find Observation resources for blood glucose" helps the agent focus
3. **Include filters**: "active prescriptions", "in the last year", "greater than 9%" all translate to FHIR search parameters
4. **The agent will discover the right codes**: You never need to provide clinical codes - that is the agent's job
