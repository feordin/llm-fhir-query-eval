# Journal selection and format requirements (researched 2026-09-02)

## Recommendation: JAMIA — Research and Applications

Best audience fit by a wide margin: JAMIA published PheKB, SMART on FHIR,
MIMIC-IV-on-FHIR, and Synthea — four of this paper's foundational citations.
Execution-based FHIR/phenotyping evaluation is squarely in scope, and our
draft was already structured to JAMIA's required sections.

| Requirement | JAMIA spec | Our status |
|---|---|---|
| Main text | ≤ 4,000 words | 2,709 + additions — OK |
| Abstract | ≤ 250 words, structured: Objective / Materials and Methods / Results / Discussion / Conclusion | trimmed from 391 → ~250, Discussion heading added |
| Body sections | abstract headings + Background and Significance | restructured |
| Tables | ≤ 4 | merged 6 → 4 (tier table → prose; deck-map dropped) |
| Figures | ≤ 6 | 7 slots → 6 (Fig 6 becomes two panels) |
| References | unlimited; numbered, Medline abbrev., ≤3 authors then et al. | 14 refs, 12 PubMed-verified |
| Title page | title, corresponding author, affiliations/degrees, ≤5 keywords (MeSH), word count | in submission file (placeholders for affiliation details) |
| Statements | Data availability (required), funding, competing interests, CRediT author contributions, AI/LLM-use disclosure (cover letter + Methods/Acknowledgements) | drafted |
| Preprint policy | preprints allowed before submission | medRxiv possible |

Source: [JAMIA General Instructions (OUP)](https://academic.oup.com/jamia/pages/General_Instructions)

## Alternatives (in fallback order)

1. **JAMIA Open** — same house/format, higher acceptance, fully OA (APC).
   Near-zero reformatting cost if JAMIA declines with transfer offer.
2. **Journal of Biomedical Informatics** (Elsevier) — methodology framing fits
   (benchmark + evaluation method). Structured abstract ≤300 (Objective/
   Methods/Results/Conclusion); body Introduction/Related Work/Methods/
   Results/Discussion/Conclusion ≤6,000 words. Expects healthcare-professional
   involvement in evaluation. [Guide for authors](https://www.sciencedirect.com/journal/journal-of-biomedical-informatics/publish/guide-for-authors)
3. **npj Digital Medicine** — higher impact, broader audience; lighter format
   (unstructured abstract, no hard body limit for Articles, ≤60 refs) but a
   much more selective bar; the "tools democratize cohort ID" story would
   need a stronger clinical-impact frame. [Submission guidelines](https://www.nature.com/npjdigitalmed/for-authors-and-referees/submission-guidelines)
4. **JMIR Medical Informatics** — friendly to eval/benchmark papers;
   structured abstract ≤450 words; OA with APC. [Instructions for authors](https://medinform.jmir.org/author-information/instructions-for-authors)

## Submission checklist (JAMIA)

- [ ] Finalize author list, affiliations, degrees, corresponding-author contact
- [ ] Produce the 6 figures (slots specified in the submission file)
- [ ] Cover letter (must include AI-use disclosure)
- [ ] Competing-interests declarations (note Microsoft employment vs. evaluated
      Copilot/Azure infrastructure — must be declared)
- [ ] CRediT roles per author
- [ ] Consider medRxiv preprint (allowed by JAMIA policy)
- [ ] Convert `jamia-submission.md` → DOCX (pandoc) for the OUP portal
