#!/usr/bin/env bash
set -uo pipefail
TEMPLATE="https://raw.githubusercontent.com/Microsoft/fhir-server/main/samples/templates/default-azuredeploy-docker.json"
START=$(date +%s)

for i in 2 3 4 5 6 7 8 9 10; do
  name="jaerwinllm$i"
  (
    t0=$(date +%s)
    echo "[$(date +%H:%M:%S)] START $name"
    # Resource groups already exist from prior attempt -- skip group create
    if az deployment group create -g "$name" \
        --template-uri "$TEMPLATE" \
        --parameters serviceName="$name" \
                     solutionType=FhirServerSqlServer \
                     sqlSchemaAutomaticUpdatesEnabled=auto \
                     sqlDatabaseComputeTier=Hyperscale \
                     appServicePlanSku=P2V3 \
                     numberOfInstances=3 \
        -o none 2>&1; then
      echo "[$(date +%H:%M:%S)] OK   $name  ($(( $(date +%s) - t0 ))s)"
    else
      echo "[$(date +%H:%M:%S)] FAIL $name -- deployment ($(( $(date +%s) - t0 ))s)"
    fi
  ) > "logs/provisioning/$name.log" 2>&1 &
done
wait
echo "============================================================"
echo "ALL PARALLEL JOBS FINISHED ($(( $(date +%s) - START ))s)"
echo "============================================================"
for i in 2 3 4 5 6 7 8 9 10; do
  tail -1 "logs/provisioning/jaerwinllm$i.log"
done
