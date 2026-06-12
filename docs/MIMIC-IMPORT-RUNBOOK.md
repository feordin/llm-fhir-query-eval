# MIMIC-IV → 10 FHIR instances via `$import` — runbook

Goal: load the **full** standardized MIMIC-IV-on-FHIR into all 10 Microsoft FHIR
instances (`jaerwinllm`, `jaerwinllm2..10`, App Service) once via `$import`, then
run the eval sweep with `scripts/run_mimic_sweep.sh` (`--no-reload`, no per-phenotype
contention).

**Approach: prove it on ONE instance first, then fan out to the other 9.**

## VALIDATED recipe (proved end-to-end on `jaerwinllm4`, 2026-06-12)

Three things that matter, learned the hard way:
1. **Use `IncrementalLoad`, not `InitialLoad`.** Set `Import__InitialImportMode=false`.
   `InitialLoad`/`InitialImportMode=true` locks the server **read-only** (HTTP 423 on
   everything, including queries and `$bulk-delete`) — useless for an eval that must
   query. `IncrementalLoad` upserts and keeps the server queryable. (`mimic_import.py`
   defaults to `InitialLoad` — pass IncrementalLoad for this use, see Step 4.)
2. **Grant BOTH the system-assigned AND the user-assigned managed identity** the
   `Storage Blob Data Contributor` role on `jaerwinimport`. The FHIR server picks one;
   granting both removes the guesswork. (Per server: RG = server name, user MI =
   `<server>-uami`, storage = `jaerwinimport` in RG `jaerwinllm`.)
3. **RESTART the FHIR app AFTER granting the RBAC.** This was the crux: the blob read
   returned 403 ("Failed to get properties of blob") for 15+ min after the grant — the
   server caches its blob-auth. A restart cleared it instantly and the import succeeded
   (623 Locations loaded + queryable). So: grant role → wait a few min → restart → import.

Quick smoke test that proves an instance is ready (reuses the already-staged synthetic
`fhirllmtestresources/Location.ndjson`):
```
POST {fhir}/$import  mode=IncrementalLoad  input=[{type:Location, url:.../Location.ndjson}]
-> expect output [{type:Location, count:623}], then GET /Location?_summary=count == 623
```

---

## Step 2a — Standardize the full MIMIC data

```bash
# point at the full MIMIC-IV-on-FHIR `fhir/` dir (credentialed download), not the demo
python scripts/standardize_mimic_fhir.py \
  --input-dir /path/to/mimic-iv-on-fhir/fhir \
  --output-dir data/mimic-standardized
# validation gate: re-dotted ICD sample-validated via UMLS >=95%; LOINC coverage % printed
```

Only these resource types are needed (skip Chartevents 534 MB, Datetime/Micro/Specimen):
**Patient, Encounter, Condition(+ED), Procedure, Observation(Labevents+ED),
MedicationRequest**, + foundation (Organization, Location, Practitioner, PractitionerRole).

## Step 2b — Stage in blob

Reuse the existing import storage account (`jaerwinimport`) or a MIMIC-specific
container. NDJSON, one resource per line.

```bash
az storage blob upload-batch \
  --account-name jaerwinimport \
  --destination "fhir-mimic" \
  --source data/mimic-standardized \
  --pattern "*.ndjson" \
  --auth-mode login
```

---

## Step 3 — Configure `$import` on ONE instance (`jaerwinllm`)

These are App Service app settings on the Microsoft FHIR OSS server. Config keys use
`__` (double underscore) as the section separator on Linux App Service. **Confirm the
exact key names against your deployment** (they were set once for the earlier synthetic
`$import`, so some may already exist).

```bash
RG=<resource-group>
APP=jaerwinllm
STORAGE=jaerwinimport

# 3a. Enable Import + initial-load mode + point at the blob store
az webapp config appsettings set -g $RG -n $APP --settings \
  FhirServer__Operations__Import__Enabled=true \
  FhirServer__Operations__Import__InitialImportMode=true \
  FhirServer__Operations__IntegrationDataStore__StorageAccountUri="https://${STORAGE}.blob.core.windows.net"

# 3b. TaskHosting — $import runs as a hosted background task; raise the concurrency
#     so multiple input files import in parallel (default is small, ~2). >=6 per your note.
az webapp config appsettings set -g $RG -n $APP --settings \
  TaskHosting__Enabled=true \
  TaskHosting__MaxRunningTaskCount=6
```

## Step 3c — RBAC: let the FHIR service's managed identity read the blob

The FHIR service authenticates to the storage account via its **user-assigned managed
identity**. Grant it Storage Blob Data access on the storage account (Contributor covers
import-read + export-write; Reader is enough for import-only).

```bash
# principal (object) id of the FHIR service's user-assigned managed identity
MI_PRINCIPAL=$(az identity show -g <mi-rg> -n <managed-identity-name> --query principalId -o tsv)
STORAGE_ID=$(az storage account show -g $RG -n $STORAGE --query id -o tsv)

az role assignment create \
  --assignee "$MI_PRINCIPAL" \
  --role "Storage Blob Data Contributor" \
  --scope "$STORAGE_ID"
```

> If the FHIR app uses a **system-assigned** identity instead, get its principal with
> `az webapp identity show -g $RG -n $APP --query principalId -o tsv`. The user noted a
> **user-assigned** MI, so use `az identity show`. Confirm which `IntegrationDataStore`
> auth mode the server expects (managed-identity vs connection string); managed identity
> is the modern default.

Restart the app so settings + role take effect: `az webapp restart -g $RG -n $APP`.

---

## Step 3d — Empty the instance, then `$import`, then verify (on `jaerwinllm`)

```bash
# ensure empty (reuses our $bulk-delete wiper)
FHIR_RELOAD_URL=https://jaerwinllm.azurewebsites.net \
  python scripts/reload_phenotype.py --wipe-only anything   # wipe-only ignores the phenotype

# POST $import — body = Parameters{ inputFormat, mode=InitialLoad, input[]={type,url} }
# load order: foundation -> Patient -> Encounter -> clinical (Condition/Procedure/Observation/MedicationRequest)
# (scripted invocation: scripts/mimic_import.py — TODO build once one-server config is confirmed)
```

**Verify before trusting it:** live dx counts must match the offline counter
(`scripts/mimic_phenotype_counts.py`) — e.g. for the demo HTN=55, CHD=33, T2D=32; for
full MIMIC the numbers scale up. Spot-check a few:

```bash
curl -sk "https://jaerwinllm.azurewebsites.net/Condition?code=http://hl7.org/fhir/sid/icd-10-cm|I10&_summary=count"
```

If counts are right on `jaerwinllm`, the config is correct.

---

## Step 3e — Fan out to the other 9

Repeat 3a-3d for `jaerwinllm2..10` (loop the `az` commands over the app names; same
storage account + same blob container, so RBAC is per-storage-account but each app's MI
needs the role — grant to each app's MI, or use one shared user-assigned MI across all 10).

---

## Step 4 — Run the sweep

After all 10 are loaded + verified:

1. **Recompute gold patient sets for multi-query cases** against loaded MIMIC
   (single-query cases need nothing — `ExecutionEvaluator` runs gold + model live).
   `scripts/recompute_gold_for_server.py` (TODO — reuses `reload_phenotype._expected_patient_set`)
   writes MIMIC `expected_patient_ids` so comprehensive/negation cells score correctly.
2. `bash scripts/run_mimic_sweep.sh [phenos-file] [tiers]` — shards all phenotypes across
   the 10 servers, `--no-reload`, results tagged `+mimic` (distinct from synthetic).
3. Aggregate and compare synthetic-vs-real.

## Coverage caveat (report it)
MIMIC procedures are **ICD-10-PCS** and meds are **NDC** — our procedure (CPT/SNOMED)
and med (RxNorm) gold codes don't overlap, so those paths score ~0 unless crosswalked.
The **dx (ICD)** path is the reliable signal; labs (LOINC) over-capture in the sick ICU
population. Frame MIMIC as the **diagnosis-cohort** real-data check, and note med/procedure
crosswalks as future work.
