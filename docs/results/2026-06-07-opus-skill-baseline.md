# Opus skill baseline: best off-the-shelf vs our methodology (Task #2)

**Date:** 2026-06-07. Subset: 8 phenotypes (easy / trick-Path-C / labs / comprehensive).
- **Off-the-shelf:** `copilot:claude-opus-4.7` **closed-book (T1)** + Anthropic's
  `fhir-developer` skill (SKILL.md + resource-examples, frontmatter stripped),
  NO tools, NO agentic loop.
- **Ours:** `copilot:claude-opus-4.7` **T2** agentic (10 FHIR/UMLS/VSAC tools).

## Comprehensive ("all-patients") cell, mean over naive/broad/expert (n=24 each)

| Phenotype | T1 + skill | T2 (ours) | Δ |
|---|---|---|---|
| type-2-diabetes | 0.969 | 0.972 | ~0 |
| gerd | 0.996 | 1.000 | ~0 |
| osteoporosis | 0.989 | 0.989 | 0 |
| systemic-lupus-erythematosus | 0.966 | 0.996 | −0.03 |
| heart-failure | 0.962 | 1.000 | −0.04 |
| coronary-heart-disease | 0.946 | 1.000 | −0.05 |
| crohns-disease | **0.739** | 1.000 | **−0.26** |
| asthma | **0.460** | 0.950 | **−0.49** |
| **MEAN** | **0.878** | **0.989** | **−0.111** |

## Takeaways (deck)
- A strong off-the-shelf model + Anthropic's FHIR skill, **closed-book**, already
  reaches **0.88** on comprehensive cohorts — and is essentially tied with our
  agentic methodology on **easy** phenotypes (T2D, GERD, osteoporosis ≈ 0.97–0.99).
- It **collapses on the hard cross-indication / trick phenotypes** — crohns 0.74,
  asthma 0.46 — where finding the *whole* cohort needs tools to discover codes,
  crosswalk systems, and sample the server. The entire 0.88→0.99 gap is here.
- **The off-the-shelf option is good enough for the easy 80%; our agentic approach
  is what unlocks the hard cases that real clinical phenotyping is made of.**

## Caveat / possible follow-up
- This isolates "closed-book+skill vs agentic", not "skill vs no-skill". To measure
  the skill's *marginal* lift we'd add an Opus T1 **without** skill on the same
  subset (cheap, Copilot). Not run yet.
