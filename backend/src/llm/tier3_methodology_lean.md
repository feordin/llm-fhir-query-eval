# Tier 3 Phenotype Methodology (lean)

Condensed playbooks for small-context models. The full file is
tier3_methodology.md; this lean version drops worked examples and detailed
prose, keeping just the decision tree + one-line strategy per playbook.

---

## STEP 0 — Categorize before you query (mandatory)

State explicitly: **"This request matches Playbook(s) X [+ Y + Z]."** Then build queries. Keyword cheat-sheet:

| Keyword in request | Playbook |
|---|---|
| "without", "but not", "MINUS", "lacking" | **10 — Negation**: two queries on separate lines |
| "≥", "above", "over", numeric thresholds | **7 — Threshold**: `value-quantity=ge<value>\|\|<unit>` |
| "men/women/male/female" | **4 — Sex**: chain `patient.gender` |
| restricts by **current age** ("currently under 18", "adults over 65") | **3 — Age**: chain `patient.birthdate`. NOT for age words in the disease *name* (neonatal/juvenile/congenital) — the code already encodes that; a birthdate filter over-constrains. |
| "all my patients", "complete cohort" | **12 — Cohort = OR**: multi-resource union |
| "validated cases", "research cohort" | **12 — Case = AND**: `_has` cross-resource |
| "drug-induced", "iatrogenic" | **5 — Iatrogenic**: drug exposure is primary |
| "treatment response", "responders" | **2 — PGx**: MedicationRequest + outcome resource |

Most phenotypes match >1 playbook — combine them.

---

## Playbooks (one line each)

1. **Subtypes** (cancers, NDD, diabetes families). Query the umbrella SNOMED + each subtype code; union with `,` in one `code=` param. Don't pick only one subtype.
2. **PGx / drug response** (warfarin INR, clopidogrel post-AMI). Always two resources: `MedicationRequest` for the drug + `Observation` (or `Condition`) for the outcome.
3. **Age-restricted** — ONLY when the request restricts the patient's *current* age. Add `&patient.birthdate=gt<YYYY-MM-DD>&patient.birthdate=lt<YYYY-MM-DD>` (FHIR has no `age` param; chain through Patient). Do NOT add this for a disease whose *name* contains an age word (neonatal/juvenile/congenital) — the condition code already encodes the age and the filter drops valid patients.
4. **Sex-specific**. Add `&patient.gender=male` or `=female`.
5. **Iatrogenic / complication**. Drug exposure is the PRIMARY signal, not the dx. Query `MedicationRequest?code=<drug>` first; the dx may be absent.
6. **Procedurally defined**. Use `Procedure?code=<CPT-or-SNOMED>`. Cross-walk CPT↔SNOMED via UMLS if only one is in the prompt.
7. **Threshold-based** (HbA1c≥6.5, eGFR<60, T-score≤-2.5). `Observation?code=<loinc>&value-quantity=ge6.5||%25` (URL-encode `%`). Negative thresholds: `=le-2.5||{T_score}`.
8. **Multi-system code lists** (PheKB style: SNOMED + ICD-10 + ICD-9). Emit ONE query with comma-separated `code=` values from all systems. Don't issue a query per system unless they're different resource types.
9. **Acute / temporal**. Add `&onset-date=ge<date>` or `&authored-on=ge<date>`. For "current": no date filter; the latest record wins.
10. **Negation** ("drug X without dx Y"). Emit TWO queries on separate lines: (a) the keep-set (`MedicationRequest?code=X`), (b) the subtract-set (`Condition?code=Y`). The harness will subtract patient sets.
11. **Cross-resource AND**. Use `_has`: `Patient?_has:Condition:patient:code=<dx>&_has:MedicationRequest:patient:code=<drug>` — returns patients with BOTH.
12. **Cohort vs validated case**. "Find all my patients with X" = OR across evidence sources (dx OR meds OR labs OR procedures). "Validated research case" = AND of strict criteria (use `_has` chain).

---

## Universal tactics (apply to every tier-3 query)

- **Sample the server first** via `fhir_resource_sample` when uncertain which code system the data uses. Don't guess.
- **Use `fhir_server_metadata`** to confirm a search param exists before relying on it.
- **For codes you don't know**: `umls_search` → CUI → `umls_crosswalk` to the target system. Don't invent codes.
- **One primary query if possible**; multiple queries are union (line-separated) or subtract (negation Playbook 10).
- **Always include the system URI**: `code=http://snomed.info/sct|44054006`, never bare `code=44054006`.
