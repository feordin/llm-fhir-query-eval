---
description: Build a FHIR cohort query from a plain-English patient-population description
argument-hint: <population description> [--server <FHIR base URL>]
---

Build FHIR cohort queries for: $ARGUMENTS

Use the `fhir-cohort-query` skill workflow. If a `--server` URL is given use
it; else use `$FHIR_BASE_URL`; else ask for the FHIR endpoint before doing
anything else. Deliver the final query set with live `_summary=count` results
and caveats.
