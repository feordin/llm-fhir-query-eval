# fhir-phenotyping — Shareable Claude Code Plugin

**Date:** 2026-06-05
**Status:** Approved design, pending implementation plan
**Task:** #4 (dev-days goals)

## Goal

Package everything we built into a **genuinely usable, installable Claude Code
plugin** that helps anyone do clinical phenotyping — turn a plain-English cohort
definition into correct, multi-coding FHIR cohort queries — and that doubles as
the **finale of the dev-days presentation** ("here is the gap the sweep exposed;
here is the plugin that closes it").

Audience: practitioners (outward-facing, must work for a stranger) + showcase.

## Vehicle decision

A **plugin** distributed via a Claude Code **plugin marketplace** (modeled on
`anthropics/healthcare`). Rationale: only a plugin can bundle **skills + an MCP
server + slash commands** in one `/plugin install`. A subagent is too narrow
(single persona, can't ship the MCP); a loose skill-set can't carry the UMLS
server. Confirmed schema from `anthropics/healthcare`: a single `plugin.json` may
declare both `mcpServers{}` and `skills[]`.

## Distribution & install

New public GitHub repo `<owner>/fhir-phenotyping`, structured as a marketplace:

```
/plugin marketplace add <owner>/fhir-phenotyping
/plugin install fhir-phenotyping@fhir-phenotyping
```

`<owner>` = the user's GitHub account (TBD at publish time).

## Repository / plugin layout

```
fhir-phenotyping/                          # repo root = marketplace
  .claude-plugin/marketplace.json          # lists one plugin: fhir-phenotyping
  README.md                                # install + quickstart + showcase script
  fhir-phenotyping/                        # the plugin
    .claude-plugin/plugin.json             # name, version, mcpServers{}, skills[], commands
    skills/
      fhir-phenotyping/
        SKILL.md                           # methodology + 108 index + UMLS workflow
        references/
          phenotypes/<name>.md             # 108 generated files
          query-patterns.md                # comprehensive union, negation/_has,
                                           #   lab thresholds, multi-coding strategy
          umls-lookup.md                   # search_umls -> CUI -> get_source_atoms_for_cui
      fhir-server-introspection/
        SKILL.md                           # adapted from existing skill
    commands/
      phenotype.md                         # /phenotype <name>
      cohort.md                            # /cohort "<plain english>"
```

### marketplace.json (shape)

```json
{
  "name": "fhir-phenotyping",
  "owner": { "name": "<owner>" },
  "metadata": { "version": "1.0.0",
    "description": "Clinical phenotyping toolkit: plain-English cohort definitions to correct multi-coding FHIR queries, with 108 PheKB phenotype references and live UMLS code lookup." },
  "plugins": [
    { "name": "fhir-phenotyping", "source": "./fhir-phenotyping",
      "category": "healthcare",
      "tags": ["fhir","phenotyping","phekb","umls","cohort","hl7"] }
  ]
}
```

### plugin.json (shape) — bundles skills + MCP + commands

```json
{
  "name": "fhir-phenotyping",
  "version": "1.0.0",
  "description": "...",
  "author": { "name": "<owner>" },
  "skills": ["./skills/fhir-phenotyping", "./skills/fhir-server-introspection"],
  "mcpServers": {
    "nih-umls": {
      "command": "uvx",
      "args": ["nih-umls-mcp"],
      "env": { "UMLS_API_KEY": "${UMLS_API_KEY}" }
    }
  }
}
```

## nih-umls MCP bundling (RESOLVED)

`nih-umls-mcp` is **published on PyPI** (v0.4.0, 2026-04-30). The plugin therefore
declares the MCP with `command: "uvx", args: ["nih-umls-mcp"]` — **zero manual
install** for users (uvx fetches it on first run). Falls back to
`python -m nih_umls_mcp.server` for users who prefer pip.

- `UMLS_API_KEY` is referenced from the user's environment as `${UMLS_API_KEY}`.
  **Never bake a key into the published plugin.**
- Offline behavior: the 108 baked references carry verified codes, so the skill is
  fully functional with **no key**. A key only unlocks live lookup for *novel*
  (non-PheKB) phenotypes.

### Security action (separate from the plugin)

The working repo's `.mcp.json:7` contains a **real UMLS_API_KEY committed to git**
(`acb7c7ec-...`). Before publishing anything: (1) ensure the plugin uses
`${UMLS_API_KEY}`, (2) rotate that UMLS key since it is in this repo's history.
This is a pre-publish gate, tracked as its own step in the implementation plan.

## Per-phenotype reference generation (core build effort)

A generator `scripts/build_phenotype_references.py` emits all 108
`references/phenotypes/<name>.md` from existing source-of-truth — no hand-authoring:

| Source | Contributes |
|---|---|
| `test-cases/phekb/phekb-<name>-*.json` | Gold FHIR queries per variant (dx/meds/labs/procedures/comprehensive/trick), expected codes, negation flags |
| `data/code_augmentations.json` | SNOMED-keyed crosswalk to ICD-10/ICD-9/CPT/RxNorm |
| Mimicker packs + memory notes | Path-C %, cross-indication notes, mimicker terms, sex/age guards |

Each generated `<name>.md` contains:
1. **Overview** — what the phenotype is, which paths apply (A/B/C/D), any patient filters (sex/age).
2. **Code sets** — per system (SNOMED, ICD-10-CM, ICD-9-CM, RxNorm, LOINC, CPT).
3. **Query paths** — A (dx+meds), B (dx-only), C (meds-only, the trick), D (labs-only), with the FHIR query for each.
4. **Comprehensive union query** — the headline multi-resource query.
5. **Tricky hints** — cross-indication mimickers, negation/two-query subtraction, lab thresholds.
6. **Worked examples** — copy-pasteable FHIR search URLs.

SKILL.md's index table is generated alongside (name -> one-liner -> reference path)
so Claude loads only the relevant phenotype reference on demand (progressive
disclosure; ~zero startup bloat).

Regeneration is idempotent and re-runs whenever phenotypes/test-cases change, so
the plugin stays in lockstep with the eval truth.

## SKILL.md (the methodology)

Distilled from the `phenotype_workflow` skill for a *practitioner* (not our Synthea
pipeline):

1. Decompose a clinical cohort request into paths (dx / meds / labs / procedures).
2. Resolve codes: if the nih-umls MCP is present and keyed, use the verified
   pattern `search_umls("<term>","exact") -> CUI -> get_source_atoms_for_cui`;
   otherwise use the baked phenotype reference.
3. Build a **multi-coding** query (query in any system finds the same cohort).
4. Handle the **comprehensive union** (Condition ∪ MedicationRequest ∪ Observation
   ∪ Procedure) and **trick cases** (meds-without-dx, abnormal-labs-without-dx,
   negation via two-query subtraction).
5. Point at a real server: defer to the `fhir-server-introspection` skill.

## Slash commands (v1)

- `/phenotype <name>` — print a phenotype's code sets + ready-to-run FHIR queries
  (reads the generated reference). The fast "give me the codes" path.
- `/cohort "<plain-english cohort>"` — the **showcase centerpiece**: generate the
  multi-coding FHIR query for an arbitrary description, applying the methodology
  (and live UMLS lookup if keyed).

## fhir-server-introspection skill

Adapted from the existing `.claude/skills/fhir_server_introspection/SKILL.md` so a
practitioner can introspect their own server's capability statement, profiles, and
valueset bindings. Carried as a second skill in the same plugin.

## Out of scope (v1)

- **Synthea / synthetic data generation** — eval-only, stays out of the
  practitioner plugin (confirmed).
- The eval harness, sweep launchers, scoring/aggregation — internal, not shipped.
- Non-PheKB phenotype reference files — only the 108 we have verified data for.

## Showcase demo (dev-days finale)

Live sequence:
1. `/plugin install fhir-phenotyping@fhir-phenotyping`
2. Ask in plain English: *"find patients with type 2 diabetes who are on metformin
   but have no diabetes diagnosis"* (a Path-C trick case).
3. The skill emits the correct multi-coding query that catches the
   meds-without-dx cohort — the exact case a bare model under-queries (shown by
   the sweep's trick-variant numbers).
4. Contrast with the same prompt and no plugin → under-query. Close on: *the
   measured gap, and the installable thing that closes it.*

## Phasing

- **v1 (target for dev days):** marketplace + plugin.json + generated 108
  references + SKILL.md + fhir-server-introspection skill + MCP declaration +
  `/phenotype` + `/cohort` + README/quickstart.
- **v1.1 (post-dev-days):** richer `/cohort` validation, optional eval-on-demand,
  additional non-PheKB phenotypes.

## Open items to confirm during planning

1. `<owner>` / final repo name for the public marketplace.
2. Whether to also publish the marketplace listing anywhere central (vs share the
   repo URL directly).
3. Exact wording/format of the generated reference template (lock the template
   before generating all 108).
