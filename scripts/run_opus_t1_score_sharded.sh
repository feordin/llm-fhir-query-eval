#!/usr/bin/env bash
# Parallel score phase for the decoupled Opus T1 backfill: shard the remaining
# phenotypes round-robin across N Azure FHIR servers. Each server runs its shard
# SEQUENTIALLY (reload -> replay-score), but the servers run concurrently. Safe:
# scoring is replay-only (no LLM subprocesses), and concurrent reloads off the
# external bundles dir were verified contention-free.
#
# Reads phenotype list from $1 (one per line). Generation must already be done.
set -uo pipefail
cd "$(dirname "$0")/.."
if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi
export FHIR_BUNDLES_DIR="${FHIR_BUNDLES_DIR:-C:\\fhir-bundles-ext}"
PHENO_FILE="${1:?usage: run_opus_t1_score_sharded.sh <phenos-file>}"
mkdir -p logs/opus-t1-decoupled/shards
mapfile -t PHENOS < "$PHENO_FILE"
SERVERS=(
  "https://jaerwinllm.azurewebsites.net"
  "https://jaerwinllm2.azurewebsites.net"
  "https://jaerwinllm3.azurewebsites.net"
  "https://jaerwinllm4.azurewebsites.net"
  "https://jaerwinllm5.azurewebsites.net"
  "https://jaerwinllm6.azurewebsites.net"
)
N=${#SERVERS[@]}
echo "SHARDED SCORE: ${#PHENOS[@]} phenotypes across $N servers"
for ((s=0; s<N; s++)); do
  shard=()
  for ((i=s; i<${#PHENOS[@]}; i+=N)); do shard+=("${PHENOS[i]}"); done
  [[ ${#shard[@]} -eq 0 ]] && continue
  (
    python scripts/run_t1_decoupled.py score \
      --phenotypes "${shard[@]}" \
      --model claude-opus-4.7 --both \
      --fhir-url "${SERVERS[s]}"
  ) > "logs/opus-t1-decoupled/shards/score-shard-${s}.log" 2>&1 &
  echo "  shard $s -> ${SERVERS[s]} (${#shard[@]} phenos) PID $!"
done
wait
echo "ALL SHARDS DONE"
