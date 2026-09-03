# fhir-cohort-agent

**Plain English in → research-grade FHIR cohort queries out.**

A Claude Code plugin that turns a patient-population description ("find all
my type 2 diabetics", "women over 65 with osteoporosis but no
bisphosphonate") into FHIR search queries whose **returned patient set**
actually matches the described cohort — validated by live execution, not
vibes.

Distilled from a 108-phenotype execution-based benchmark (expert PheKB
algorithms, patient-set precision/recall/F1 scoring) plus real-data
validation on MIMIC-IV-on-FHIR (299,712 patients). The headline findings the
plugin encodes:

- **Closed-book LLMs are poor cohort finders** — F1 ≈ 0.6 on synthetic data
  and ≈ 0.1 on real EHR data, because they guess codes from memory.
- **Tools are the dominant lever** (+0.23–0.30 F1 synthetic, +0.6 real):
  sampling the live server and looking codes up in UMLS/VSAC recovers what
  recall misses.
- **With tools, plain English ≈ expert prompting** — the workflow erases
  the prompt-sophistication gap.

## What's inside

| Component | Purpose |
|---|---|
| `skills/fhir-cohort-query/` | The discovery-loop workflow: categorize → find codes (UMLS/VSAC) → sample the server → count-validate → emit queries |
| `skills/.../references/methodology.md` | 12-playbook phenotyping decision tree (negation, thresholds, subtype enumeration, sex/age guards, `_has` AND-cohorts…), with benchmark-derived fixes baked in |
| `agents/cohort-builder.md` | A delegatable agent that runs the whole loop and returns queries + live counts |
| `commands/cohort.md` | `/fhir-cohort-agent:cohort <description>` slash command |
| `scripts/fhir_introspect.py` | Stdlib-only helper: capability summary, code-system census, `_summary=count` probe |
| `.mcp.json` | NIH UMLS MCP server wiring (UMLS + VSAC terminology services) |

## Requirements

1. **A FHIR R4 server** to query. Set `FHIR_BASE_URL` (or pass
   `--server` / mention it in your request). Optional `FHIR_BEARER_TOKEN`
   for authenticated servers.
2. **A free UMLS API key** (https://uts.nlm.nih.gov/uts/signup-login) in
   `UMLS_API_KEY`, plus the `nih-umls` MCP server package
   (`pip install nih-umls-mcp` or your local equivalent). Without it the
   workflow still runs but loses code lookup/crosswalk/value-set expansion.

## Usage

```
/fhir-cohort-agent:cohort patients on warfarin with an INR above 3 --server https://fhir.example.com/r4
```

or just ask in chat: *"Find every patient with CKD stage 3 or worse on my
FHIR server"* — the skill triggers on cohort-finding requests.

Output: one or more FHIR query URLs (union queries line-separated; negation
as KEEP/SUBTRACT pairs), each with its live `_summary=count`, plus caveats
(paths the server can't express, codes that couldn't be verified).

## The core rule

> **Never answer from memory.** Real EHR data is single-code-system,
> granularly coded, and full of surprises (NDC behind
> `medicationReference`, ICD-9 in old records, no `code:below` hierarchy).
> The agent's first action is always discovery — sample the server, look up
> the codes — because that's what measurably works.

## Provenance

Built from the `llm-fhir-query-eval` benchmark project. Method and numbers:
see the project's results docs and paper draft (`docs/paper/manuscript.md`).

## License

MIT
