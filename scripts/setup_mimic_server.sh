#!/usr/bin/env bash
# Configure ONE Microsoft FHIR App Service for $import and load the MIMIC demo.
# Validated recipe (docs/MIMIC-IMPORT-RUNBOOK.md): grant both MIs the blob role ->
# set app settings (IncrementalLoad, TaskHosting=6) -> wait propagation -> RESTART
# (clears cached blob-auth) -> wipe + import + verify (with one restart+retry).
#
# az runs natively here (git bash); the FHIR half is scripts/mimic_load.py.
# Usage: bash scripts/setup_mimic_server.sh <server>   e.g. jaerwinllm5
set -uo pipefail
cd "$(dirname "$0")/.."
if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi
SRV="${1:?usage: setup_mimic_server.sh <server>}"
# Azure infra — set these in .env (see .env.example), not hard-coded:
SUB="${FHIR_SUBSCRIPTION:?set FHIR_SUBSCRIPTION (Azure subscription id)}"
STORAGE="${FHIR_IMPORT_STORAGE:?set FHIR_IMPORT_STORAGE (storage account name)}"
STORAGE_RG="${FHIR_IMPORT_STORAGE_RG:?set FHIR_IMPORT_STORAGE_RG (storage account resource group)}"
STORAGE_ID="/subscriptions/${SUB}/resourceGroups/${STORAGE_RG}/providers/Microsoft.Storage/storageAccounts/${STORAGE}"
ROLE=ba92f5b4-2d11-453d-a403-e96b0029c9fe   # Storage Blob Data Contributor (well-known Azure role id)
URL="https://${SRV}.azurewebsites.net"
PROP_WAIT="${PROP_WAIT:-180}"

az account set --subscription $SUB

# az with retry (PIM Contributor propagates inconsistently across ARM replicas)
azr() { local i; for i in 1 2 3 4 5; do az "$@" && return 0; echo "  (retry az $1 $2)"; sleep 20; done; return 1; }

echo "=== setup $SRV ==="
SYS=$(azr webapp identity show -g "$SRV" -n "$SRV" --query principalId -o tsv)
USR=$(azr identity show -g "$SRV" -n "${SRV}-uami" --query principalId -o tsv)
echo "  system MI=$SYS  user MI=$USR"
for P in "$SYS" "$USR"; do
  GUID=$(python -c "import uuid;print(uuid.uuid4())")
  if az rest --method put \
      --url "https://management.azure.com${STORAGE_ID}/providers/Microsoft.Authorization/roleAssignments/${GUID}?api-version=2022-04-01" \
      --body "{\"properties\":{\"roleDefinitionId\":\"/subscriptions/${SUB}/providers/Microsoft.Authorization/roleDefinitions/${ROLE}\",\"principalId\":\"${P}\",\"principalType\":\"ServicePrincipal\"}}" >/dev/null 2>&1; then
    echo "  granted blob role to $P"
  else echo "  blob role for $P (already exists or transient)"; fi
done

azr webapp config appsettings set -g "$SRV" -n "$SRV" --settings \
  FhirServer__Operations__Import__Enabled=true \
  FhirServer__Operations__Import__InitialImportMode=false \
  "FhirServer__Operations__IntegrationDataStore__StorageAccountUri=https://${STORAGE}.blob.core.windows.net" \
  TaskHosting__Enabled=true TaskHosting__MaxRunningTaskCount=6 -o none
echo "  settings set; waiting ${PROP_WAIT}s for RBAC propagation..."
sleep "$PROP_WAIT"
azr webapp restart -g "$SRV" -n "$SRV"
echo "  restarted; waiting for health..."
for i in $(seq 1 24); do
  code=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 15 "$URL/metadata" 2>/dev/null)
  [[ "$code" == "200" ]] && break; sleep 10
done

# wipe + import + verify; on failure restart once and retry (blob-auth cache)
if ! python scripts/mimic_load.py --server "$SRV"; then
  echo "  load failed; restart + retry"
  azr webapp restart -g "$SRV" -n "$SRV"
  sleep 90
  python scripts/mimic_load.py --server "$SRV"
fi
echo "=== $SRV done ==="
