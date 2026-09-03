# Phenotyping Methodology — playbook decision tree

Benchmark-validated (108 PheKB phenotypes + MIMIC-IV): this lean form
outperformed a 3× longer version for strong models, and lifted a small
open-weight model +0.23 F1. Apply STEP 0 first, always.

## STEP 0 — Categorize before you query (mandatory)

State explicitly: **"This request matches Playbook(s) X [+ Y + Z]."** Then
build queries. Keyword cheat-sheet:

| Keyword in request | Playbook |
|---|---|
| "without", "but not", "MINUS", "lacking" | **10 — Negation**: two queries, subtract sets |
| "≥", "above", "over", numeric thresholds | **7 — Threshold**: `value-quantity=ge<value>\|\|<unit>` |
| "men/women/male/female" | **4 — Sex**: chain `patient.gender` |
| restricts by **current age** ("currently under 18", "adults over 65") | **3 — Age**: chain `patient.birthdate`. NOT for age words in the disease *name* (neonatal/juvenile/congenital) — the code already encodes that; a birthdate filter over-constrains. |
| "all my patients", "complete cohort" | **12 — Cohort = OR**: multi-resource union |
| "validated cases", "research cohort" | **12 — Case = AND**: `_has` cross-resource |
| "drug-induced", "iatrogenic" | **5 — Iatrogenic**: drug exposure is primary |
| "treatment response", "responders" | **2 — PGx**: MedicationRequest + outcome resource |

Most phenotypes match >1 playbook — combine them.

## Playbooks

1. **Subtypes** (cancers, neurodevelopmental, diabetes families). Query the
   umbrella code **AND every subtype code**, comma-joined in one `code=`
   param. **Enumerate the full long tail — never "pick the canonical
   code"**: on heterogeneous phenotypes, narrowing from 32 enumerated
   concepts to 7 cut recall from 1.00 to 0.39 in our benchmark.
2. **PGx / drug response** (warfarin INR, clopidogrel post-AMI). Always two
   resources: `MedicationRequest` for the drug + `Observation` (or
   `Condition`) for the outcome.
3. **Age-restricted** — ONLY when the request restricts the patient's
   *current* age. Add `&patient.birthdate=gt<YYYY-MM-DD>&patient.birthdate=lt<YYYY-MM-DD>`
   (FHIR has no `age` search param; chain through Patient). Do NOT add this
   for a disease whose *name* contains an age word — the condition code
   already encodes the age, and the filter drops valid patients.
4. **Sex-specific**. Add `&patient.gender=male` or `=female`.
5. **Iatrogenic / complication**. Drug exposure is the PRIMARY signal, not
   the dx. Query `MedicationRequest?code=<drug>` first; the dx may be absent.
6. **Procedurally defined**. Use `Procedure?code=<CPT-or-SNOMED-or-ICD10PCS>`.
   Crosswalk between systems via UMLS if only one is known; sample the
   server to see which system its Procedure resources carry.
7. **Threshold-based** (HbA1c≥6.5, eGFR<60, T-score≤-2.5).
   `Observation?code=<loinc>&value-quantity=ge6.5||%25` (URL-encode `%`).
   Negative thresholds work: `=le-2.5`.
8. **Multi-system code lists** (PheKB style: SNOMED + ICD-10 + ICD-9). Emit
   ONE query with comma-separated `code=` values from all systems present on
   the server. Don't issue one query per system unless the resource types
   differ.
9. **Acute / temporal**. Add `&onset-date=ge<date>` or `&authored-on=ge<date>`.
   For "current": no date filter; the latest record wins.
10. **Negation** ("drug X without dx Y"). Emit TWO queries on separate
    lines: (a) KEEP set (`MedicationRequest?code=X`), (b) SUBTRACT set
    (`Condition?code=Y`). Patient sets are subtracted client-side — FHIR has
    no native NOT-EXISTS.
11. **Cross-resource AND**. Use `_has`:
    `Patient?_has:Condition:patient:code=<dx>&_has:MedicationRequest:patient:code=<drug>`.
12. **Cohort vs validated case**. "Find all my patients with X" = OR across
    evidence sources (dx OR meds OR labs OR procedures — union). "Validated
    research case" = AND of strict criteria (`_has` chain).

## Universal tactics

- **Sample the server first** when uncertain which code system the data
  uses. Don't guess — real EHR data is usually single-system and granular.
- **Expand the tail iteratively, count-guided.** One sampling pass shows
  only the *head* of a large cohort's code distribution (full-scale
  benchmark: recall 0.70 for 1k–10k-patient cohorts but 0.28 above 10k from
  one-shot enumeration). Loop: query → `_summary=count` → compare against a
  clinical plausibility estimate → if low, sample more rows / expand the
  value set / probe sibling subcodes with counts → re-query. Stop when the
  count stabilizes at a plausible magnitude.
- **Confirm search params exist** via `/metadata` before relying on them
  (`_has`, `:below`, chained params vary by server).
- **For codes you don't know**: UMLS search → CUI → source atoms in the
  target system. Never invent codes.
- **One primary query if possible**; multiple queries are union
  (line-separated) or subtract (Playbook 10).
- **Always include the system URI**: `code=http://snomed.info/sct|44054006`,
  never bare `code=44054006`.

## Real-EHR lessons (MIMIC-IV validation)

- Real data may carry **no SNOMED at all** (ICD-9/ICD-10 only). Closed-book
  SNOMED queries score ~0 there; discovery is mandatory.
- Codes are **fully granular** (E11.9, E11.42, …); without server-side
  hierarchy (`:below`), a category query matches nothing — enumerate the
  granular codes actually present.
- Old records mean **ICD-9 alongside ICD-10**; query both.
- Meds are often **NDC behind `medicationReference`**, not inline RxNorm —
  check before writing medication queries.
- **Code-aware hints can mislead**: an "expert" prompt assuming SNOMED
  underperformed a plain clinical description on real data. Trust the
  server sample over the prompt's vocabulary assumptions.
