# Tier 3 Phenotype Methodology

This document is loaded into the LLM's context as an addendum to the Tier 2 system prompt when running in Tier 3 (skill-guided) mode. It distills the heuristics an experienced clinical informaticist applies when designing a phenotype query.

The Tier 2 prompt teaches you which tools exist. This methodology teaches you which strategy to apply. Recognize the *category* of phenotype, then apply the matching playbook.

---

## STEP 0 — CATEGORIZE BEFORE YOU QUERY (mandatory)

Before any tool call, before any query, do this:

1. Read the request carefully.
2. Run through the 8-question decision tree below.
3. State explicitly in your reasoning: **"This request matches Playbook(s) X [+ Y + Z]."** A request often matches multiple playbooks (e.g., a pediatric cancer is Playbook 1 + 3, a "biologic without Crohn's" request is Playbook 10 + 2).
4. Only then construct queries.

Watch especially for these keywords in the request — they are strong signals for specific playbooks:

| Keyword in request | Likely playbook |
|---|---|
| "without", "MINUS", "do NOT have", "but not", "lacking" | **Playbook 10 (Negation)** — emit two queries on separate lines |
| "≥", "above", "over", "below", numeric thresholds (e.g., "HbA1c ≥ 6.5") | **Playbook 7 (Threshold)** — `value-quantity=ge<value>||<unit>` |
| "men", "women", "male", "female" | **Playbook 4 (Sex-specific)** — chain `patient.gender` |
| "pediatric", "children", "neonatal", "elderly" | **Playbook 3 (Age-restricted)** — chain `patient.birthdate` |
| "all my patients", "complete cohort", "find all" | **Playbook 12 (Cohort = OR)** — multi-resource union |
| "validated cases", "research cohort", "confirmed" | **Playbook 12 (Case = AND)** — `_has` cross-resource |
| "drug-induced", "iatrogenic", "complication of" | **Playbook 5 (Iatrogenic)** — drug exposure is primary signal |
| "treatment response", "responders", "drug efficacy" | **Playbook 2 (PGx)** — MedicationRequest + outcome resource |

Engaging with this step doubles the success rate for "broad" or vague clinical prompts that don't spell out the algorithm. Do not skip it.

---

## How to recognize a phenotype category

Read the clinical request and ask:

1. Is the disease one with **clinical subtypes**? (cancer, dementia, diabetes, multiple sclerosis, epilepsy, heart failure)
2. Is it a **pharmacogenomics / drug response** phenotype? (warfarin, clopidogrel, asthma-ICS response, ACE-inhibitor cough)
3. Is it **age-restricted**? (pediatric: NAS, peanut allergy, SECO, post-event pain; geriatric: dementia, BPH)
4. Is it **sex-specific**? (BPH, prostate cancer for male; ovarian/cervical cancer, endometriosis for female)
5. Is it an **iatrogenic / complication** phenotype? (steroid-induced AVN, drug-induced liver injury, statins-and-MACE)
6. Is it **procedurally defined**? (colonoscopy for CRC, CABG/PCI for CHD, AAA repair, biopsy for cancer staging)
7. Is it **threshold-based**? (T2D via HbA1c, AKI via creatinine ratio, hypertension via BP, FH via LDL)
8. Does it involve **negation / exclusion**? ("biologic without a Crohn's diagnosis", "anticoagulant in patients without VTE", "statin without indication")
9. Is it a **broad provider-level cohort** or a **validated research case**? Cohort = OR of evidence; validated case = AND of strict criteria.

Most phenotypes match more than one category. Combine the playbooks below.

---

## Playbook 1 — Diseases with clinical subtypes

**Examples:** colorectal cancer, lung cancer, dementia, type 2 diabetes, heart failure, multiple sclerosis, epilepsy, sickle cell disease, depression, hypertension subtypes.

**Why they're hard:** a single SNOMED or ICD-10 code typically covers ~30-40% of the cohort. PheKB algorithms enumerate full code families.

**Strategy:**
1. Start with `vsac_search_value_sets("<concept>")`. Quality-measure value sets exist for almost all of these.
2. `vsac_expand_value_set(oid)` to get the full code family.
3. If no VSAC match, use `umls_search` and follow `crosswalk_codes` for each SNOMED parent to ICD-10 children.
4. Build a single Condition query with the comma-separated code list.
5. Sample the server to confirm which codes are actually populated.

**Common mistakes:**
- Querying parent SNOMED only (e.g., `73211009 Diabetes mellitus`) and trusting `:below` modifier — server-dependent.
- Forgetting that ICD-10-CM cancer chapters span entire ranges (C18.0-C18.9 for colon alone).

---

## Playbook 2 — Pharmacogenomics / drug response

**Examples:** Warfarin Dose Response, Clopidogrel Poor Metabolizers, Asthma Response to Inhaled Steroids, ACE-Inhibitor Cough.

**Why they're hard:** the diagnosis isn't the signal — the *medication* is. Outcome resources (INR labs for warfarin, AMI Conditions for clopidogrel) further qualify the cohort.

**Strategy:**
1. The primary resource type is `MedicationRequest`. Expect RxNorm ingredient codes (or SCD).
2. Secondary signal is in `Observation` (lab response) or `Condition` (clinical outcome).
3. Use `Patient?_has:MedicationRequest:patient:code=...&_has:Observation:patient:code=...` for AND semantics.
4. Or emit two queries (med + outcome) and let the runner intersect.

**Common mistakes:**
- Querying Condition for "patients on warfarin" — they don't necessarily have an atrial-fibrillation dx.
- Using SCD codes when ingredient codes catch all formulations.

---

## Playbook 3 — Age-restricted (pediatric, geriatric)

**Examples (pediatric):** Neonatal Abstinence Syndrome (<28 days), Peanut Allergy (school-age), SECO (5-17), Post-event Pain (6-21), ADHD, autism.
**Examples (geriatric):** dementia (≥50), osteoporosis, BPH (≥40 male).

**Why they're hard:** FHIR has no `Patient.age` parameter. You must compute via `patient.birthdate`.

**Strategy:**
1. Compute the birthdate range from the age cutoff and current date.
2. Chain on the Condition / MedicationRequest / Observation: `?code=...&patient.birthdate=ge2010-01-01` (born 2010 or later = ≤16 today, etc.).
3. For neonatal phenotypes, use `patient.birthdate=gt2024-08-01` (within last few months).
4. Confirm via `fhir_resource_sample` — check that the returned patients' actual ages match.

**Common mistakes:**
- Filtering Patient resources separately and trying to intersect — easier to chain.
- Forgetting that PheKB age cutoffs are at *encounter* time, not current date — close enough for cohort identification.

---

## Playbook 4 — Sex-specific

**Examples:** prostate cancer, BPH, DRE, PCa biopsy (male only); ovarian, cervical, breast cancer, endometriosis (female only).

**Strategy:**
1. Add `&patient.gender=male` or `&patient.gender=female` to the Condition / MedicationRequest / Procedure query.
2. Don't rely on the dx code being sex-restrictive (some servers code "male breast cancer" with the same code).

---

## Playbook 5 — Iatrogenic / complications

**Examples:** steroid-induced AVN, drug-induced liver injury (DILI), statins-and-MACE, ACE-inhibitor cough, peanut anaphylaxis after epinephrine, febrile neutropenia post-chemotherapy.

**Why they're hard:** the cohort is defined by **drug-then-outcome**, not by a static dx. Many patients never get the iatrogenic dx coded — the medication is the *exposure*, not the cohort.

**Strategy:**
1. Primary resource: `MedicationRequest` for the culprit drug (the exposure).
2. Secondary resource: `Condition` (the complication/outcome) OR `Observation` (lab evidence of toxicity, e.g., ALT ≥5×ULN).
3. For "drug exposed without complication" (Path C — controls): `MedicationRequest` query MINUS `Condition` query.
4. For "drug exposed with complication" (cases): `Patient?_has:MedicationRequest:patient:code=...&_has:Condition:patient:code=...`.

**Common mistakes:**
- Looking for the iatrogenic Condition first — it's often missing or under-coded.
- Forgetting temporal logic: the drug should precede the outcome (FHIR has limited temporal support; verify client-side or accept the imprecision).

---

## Playbook 6 — Procedurally defined

**Examples:** CRC (colonoscopy + biopsy), CHD (CABG/PCI/stent), AAA (repair procedures), BPH (TURP), prostate cancer (biopsy), bone scan utilization, DRE, cardiac stress test.

**Why they're hard:** the procedure is the inclusion criterion. CPT codes often outperform SNOMED for recall on US healthcare data.

**Strategy:**
1. Primary resource: `Procedure?code=...`.
2. Use CPT codes (e.g., 45378 colonoscopy, 33533 CABG, 92928 stent) for US data.
3. Augment with SNOMED procedure codes for international or non-billing-coded data.
4. For cohort identification: Procedure alone is often sufficient.
5. For case validation: combine with a related Condition (e.g., colonoscopy + colon cancer dx).

---

## Playbook 7 — Threshold-based

**Examples:** T2D (HbA1c ≥6.5%), AKI (creatinine ≥1.5x baseline), DILI (ALT ≥5×ULN), FH (LDL ≥190), osteoporosis (T-score ≤-2.5), HTN (SBP >140).

**Strategy:**
1. Resource is `Observation`.
2. Use `value-quantity` with prefix: `ge`, `gt`, `le`, `lt`, `eq`.
3. Encode units carefully:
   - Percent: `%` URL-encoded as `%25` (e.g., `value-quantity=ge6.5||%25`)
   - mg/dL: `value-quantity=ge190||mg/dL`
   - mm[Hg] (BP): `value-quantity=gt140||mm[Hg]`
4. For ratio-based thresholds (1.5x baseline, 5x ULN), there is no native FHIR support. Either:
   - Fetch all values and compute ratios client-side (preferred for accuracy)
   - Use an absolute threshold approximation if the population baseline is known

**Common mistakes:**
- Forgetting units — `ge6.5` without unit returns matches in any unit.
- Using `=6.5` (exact match) when you mean `ge6.5`.
- Negative thresholds (osteoporosis T-score ≤-2.5): `value-quantity=le-2.5||SD`.

---

## Playbook 8 — Multi-system code lists from PheKB algorithms

**Examples:** DILI, NAS, T2D, CKD, atrial fibrillation, heart failure, AAA — anywhere PheKB lists a comprehensive code table spanning ICD-9 + ICD-10 + SNOMED.

**Why they matter:** the PheKB algorithm explicitly enumerates the multi-system code list. Real EHR data may use any of those codings on the same patient.

**Strategy:**
1. Read the PheKB-listed codes (the test case's `metadata.required_codes` if present, or the doc analysis).
2. Build a single Condition query with codes from all systems combined: `Condition?code=http://snomed.info/sct|<code1>,http://hl7.org/fhir/sid/icd-10-cm|<code2>,http://hl7.org/fhir/sid/icd-9-cm|<code3>`.
3. Sample the server to see which codings are most prevalent — the augmented Synthea data has all three; real EHRs vary.

---

## Playbook 9 — Acute / temporal cohorts

**Examples:** sepsis (acute presentation), AKI (within 7-day baseline), pneumonia (CAP vs HAP), influenza (seasonal).

**Strategy:**
1. Use `_lastUpdated=gt<date>` for "recent" filters.
2. For temporal ordering between resources (drug then outcome), accept that FHIR support is limited — fetch and order client-side.
3. Encounter-class filters (`encounter.class=IMP` for inpatient, `EMER` for ED) help disambiguate hospital-acquired vs community.

---

## Playbook 10 — Negation / exclusion

**Examples:** "biologic without Crohn's diagnosis", "statin without atherosclerotic disease indication", "anticoagulant in patient without VTE history".

**Why they're hard:** FHIR has no `NOT EXISTS` operator. The agent must emit two queries and the runner subtracts.

**Strategy:**
1. Identify the inclusion set (e.g., all biologic prescriptions).
2. Identify the exclusion set (e.g., all Crohn's diagnoses).
3. Emit both queries on separate lines.
4. Annotate the cohort definition mentally: "patients in set A but not in set B".

The runner subtracts. Do NOT emit a single query and hope to filter post-hoc — it's not what the evaluator scores.

---

## Playbook 11 — Cross-resource AND cohorts

**Examples:** T2D dx + metformin Rx, RA dx + biologic, CHD dx + stent procedure.

**Strategy:**
1. If both criteria are required (AND): use `Patient?_has:Condition:patient:code=...&_has:MedicationRequest:patient:code=...`.
2. If either is sufficient (OR): emit two queries and union via the runner.
3. Read the cohort definition carefully — "patients with T2D *or* on metformin" is OR (broad cohort), "patients with T2D *and* on metformin" is AND (validated case).

---

## Playbook 12 — Cohort vs validated case

The single most important question to answer before constructing the query:

> **Is this a broad cohort identification (provider-level use case) or a validated research case (strict trial criteria)?**

- **Cohort (OR):** Provider asks "find all my diabetes patients". They want the union of evidence — dx OR meds OR labs.
- **Case (AND):** Researcher asks "validated T2D cases". They want intersection — dx AND positive lab AND treatment.

PheKB phenotype algorithms are usually **case** definitions. Quality-measure value sets are usually **cohort** definitions. Real-world clinical workflows are usually **cohort** queries with the implicit understanding that validation happens later.

When in doubt, ask: would you rather over-include or under-include? Answer that to choose AND vs OR.

---

## A worked example: Type 2 Diabetes (provider cohort)

A provider says: "Find my type 2 diabetes patients."

Apply the categorization:
- Disease with subtypes? Yes (Playbook 1) — multiple SNOMED variants, ICD-10 family E11.x.
- Threshold-based? Yes if HbA1c is included (Playbook 7).
- Provider-level cohort? Yes (Playbook 12 — OR semantics).

Workflow:
1. `vsac_search_value_sets("type 2 diabetes")` → find OID 2.16.840.1.113883.3.464.1003.103.12.1001.
2. `vsac_expand_value_set(oid)` → 50+ codes across SNOMED + ICD-10 + ICD-9.
3. `fhir_server_metadata` → confirms US Core profiles loaded (so we expect multi-coded Conditions).
4. `fhir_resource_sample("Condition")` → confirms server has both SNOMED 44054006 and ICD-10 E11.9 on the same Conditions.
5. Emit three queries (provider cohort = OR):
   - Condition by full T2D code list (SNOMED + ICD-10 + ICD-9)
   - MedicationRequest for oral hypoglycemics (RxNorm metformin, sulfonylureas, etc.)
   - Observation for HbA1c with `value-quantity=ge6.5||%25`
6. Runner unions the patient sets → returns the full provider-level cohort.

A naïve agent would emit one Condition query with one SNOMED code and miss 60-70% of the cohort. The methodology turns that into 3 queries and full recall.
