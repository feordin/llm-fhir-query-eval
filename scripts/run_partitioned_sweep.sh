#!/usr/bin/env bash
# Multi-server partition driver: shard a list of phenotypes across N FHIR
# servers and launch run_isolated_suite.py in parallel per shard. Wall-clock
# becomes max(per-shard) instead of sum(all).
#
# Usage: bash scripts/run_partitioned_sweep.sh
# Tunables: edit MODEL, PROVIDER, TIERS, PROMPT_VARIANTS, SERVERS, PHENOS.
set -uo pipefail

# Load OPENAI_COMPAT_API_KEY (and friends) from .env so child Python procs
# inherit them. Without this, the OpenRouter call returns 401 and every cell
# fails silently with f1=None.
if [[ -f .env ]]; then
  set -o allexport
  # shellcheck disable=SC1091
  source .env
  set +o allexport
fi

# --- Sweep config ---
PROVIDER="openai-compat"
MODEL="qwen/qwen3.5-9b"
BASE_URL="https://openrouter.ai/api/v1"
TIERS="2,3"
PROMPT_VARIANTS="naive,broad,expert"
EXTRA_FLAGS="--lean-prompt --max-cell-workers 2"
# 10 shards * 2 cell-workers = ~20 concurrent OpenRouter conns. At 6 cell-workers
# (default) the gateway returned 289 "Connection error" + 56 timeouts across one
# run -- this lower ceiling keeps us inside its connection budget.

# --- 10 FHIR servers ---
SERVERS=(
  "https://jaerwinllm.azurewebsites.net"
  "https://jaerwinllm2.azurewebsites.net"
  "https://jaerwinllm3.azurewebsites.net"
  "https://jaerwinllm4.azurewebsites.net"
  "https://jaerwinllm5.azurewebsites.net"
  "https://jaerwinllm6.azurewebsites.net"
  "https://jaerwinllm7.azurewebsites.net"
  "https://jaerwinllm8.azurewebsites.net"
  "https://jaerwinllm9.azurewebsites.net"
  "https://jaerwinllm10.azurewebsites.net"
)

# --- 35 phenotypes (21 rigorous + 14 Tier A) ---
PHENOS=(
  # Rigorous-21
  anxiety asthma atrial-fibrillation bipolar-disorder ckd copd
  coronary-heart-disease crohns-disease dementia depression epilepsy gerd
  heart-failure hypertension hyperthyroidism hypothyroidism migraine
  rheumatoid-arthritis stroke type-1-diabetes type-2-diabetes
  # Tier A 14
  acute-kidney-injury atopic-dermatitis fibromyalgia gout
  iron-deficiency-anemia multiple-sclerosis osteoporosis parkinsons-disease
  pneumonia psoriasis schizophrenia systemic-lupus-erythematosus
  ulcerative-colitis venous-thromboembolism
)

N_SERVERS=${#SERVERS[@]}
LOGS_DIR="logs/qwen-partitioned-sweep"
mkdir -p "$LOGS_DIR"
echo "Sharding ${#PHENOS[@]} phenotypes across $N_SERVERS servers"

START=$(date +%s)
for ((s=0; s<N_SERVERS; s++)); do
  shard=()
  for ((i=s; i<${#PHENOS[@]}; i+=N_SERVERS)); do
    shard+=("${PHENOS[i]}")
  done
  if [[ ${#shard[@]} -eq 0 ]]; then continue; fi
  server="${SERVERS[s]}"
  log="$LOGS_DIR/shard-${s}.log"
  echo "[shard $s] $server  <- ${shard[*]}  log=$log"
  (
    python scripts/run_isolated_suite.py "${shard[@]}" \
      --providers "${PROVIDER}:${MODEL}" \
      --base-url "$BASE_URL" \
      --tiers "$TIERS" \
      --prompt-variants "$PROMPT_VARIANTS" \
      --fhir-url "$server" \
      $EXTRA_FLAGS \
      2>&1
  ) > "$log" 2>&1 &
done

wait
echo "============================================================"
echo "ALL SHARDS FINISHED ($(( $(date +%s) - START ))s)"
echo "============================================================"
for ((s=0; s<N_SERVERS; s++)); do
  log="$LOGS_DIR/shard-${s}.log"
  if [[ -f "$log" ]]; then
    echo "--- shard $s ---"
    tail -3 "$log"
  fi
done
