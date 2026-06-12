#!/usr/bin/env bash
# MIMIC-IV eval sweep: run the full (phenotype x prompt x tier) matrix against
# MIMIC-IV-on-FHIR, which is loaded ONCE per server via $import (out of band).
#
# Key difference from the synthetic sweep: MIMIC is a single STATIC dataset, so
# we pass --no-reload -- there is no per-phenotype wipe/load, hence none of the
# concurrent-reload contention. We just shard the phenotypes' test cases across
# the 10 instances (all holding the same MIMIC data) and read.
#
# PREREQUISITES (do first, see docs/MIMIC-IMPORT-RUNBOOK.md):
#   - standardized MIMIC NDJSON $import-ed into all 10 servers (verify counts)
#   - gold expected_patient_ids recomputed against MIMIC for multi-query cases
#     (scripts/recompute_gold_for_server.py) -- single-query cases need nothing.
#
# Usage:
#   bash scripts/run_mimic_sweep.sh [phenos-file] [tiers]
#     phenos-file: one phenotype per line (default: all 108; absent ones score ~0)
#     tiers: e.g. "1,2,3" (default) or "2,3"
set -uo pipefail
cd "$(dirname "$0")/.."
if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi
PHENO_FILE="${1:-}"
TIERS="${2:-1,2,3}"
MODEL="${MIMIC_MODEL:-copilot:claude-opus-4.7}"
mkdir -p logs/mimic-sweep/shards
if [[ -n "$PHENO_FILE" ]]; then
  mapfile -t PHENOS < "$PHENO_FILE"
else
  mapfile -t PHENOS < <(ls -d synthea/output/*/ | xargs -n1 basename | sort)
fi
SERVERS=(
  "https://jaerwinllm.azurewebsites.net"  "https://jaerwinllm2.azurewebsites.net"
  "https://jaerwinllm3.azurewebsites.net" "https://jaerwinllm4.azurewebsites.net"
  "https://jaerwinllm5.azurewebsites.net" "https://jaerwinllm6.azurewebsites.net"
  "https://jaerwinllm7.azurewebsites.net" "https://jaerwinllm8.azurewebsites.net"
  "https://jaerwinllm9.azurewebsites.net" "https://jaerwinllm10.azurewebsites.net"
)
N=${#SERVERS[@]}
echo "MIMIC SWEEP: ${#PHENOS[@]} phenotypes x tiers=$TIERS x $MODEL across $N servers (--no-reload)"
for ((s=0; s<N; s++)); do
  shard=()
  for ((i=s; i<${#PHENOS[@]}; i+=N)); do shard+=("${PHENOS[i]}"); done
  [[ ${#shard[@]} -eq 0 ]] && continue
  (
    python scripts/run_isolated_suite.py "${shard[@]}" \
      --providers "$MODEL" --tiers "$TIERS" \
      --prompt-variants naive,broad,expert \
      --fhir-url "${SERVERS[s]}" --max-cell-workers 3 \
      --no-reload --label-suffix +mimic
  ) > "logs/mimic-sweep/shards/mimic-shard-${s}.log" 2>&1 &
  echo "  shard $s -> ${SERVERS[s]} (${#shard[@]} phenos) PID $!"
done
wait
echo "MIMIC SWEEP: ALL SHARDS DONE"
