#!/usr/bin/env bash
# Expert-prompt rerun: the 193 expert prompts were rewritten to remove embedded
# FHIR query strings (commit 4f95180c). Only the EXPERT variant changed, so only
# expert cells are stale. Rerun the 91 affected phenotypes, expert-only, across
# the 3 frontier copilot models. Qwen is intentionally NOT rerun (kept as-is).
#
# Phase 1: 91 phenos x {gpt-5.4, opus-4.7, sonnet-4.6} x tiers 1,2,3 x expert
# Phase 2: 91 phenos x opus+fhirskill x tier 1 x expert (refresh skill baseline)
#
# All specs share each per-phenotype wipe/load (one reload per phenotype/server).
# Concurrency per phase 1 shard: 3 specs * --max-cell-workers 1; 10 shards = ~30
# concurrent Copilot CLIs (the proven full-sweep ceiling).
set -uo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi

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
N_SERVERS=${#SERVERS[@]}

mapfile -t PHENOS < <(tr -d '\r' < data/expert_rerun_phenos.txt | grep -v '^$')
SKILL="vendor/anthropic-fhir-skill/SKILL.md,vendor/anthropic-fhir-skill/references/resource-examples.md"

run_phase() {
  local label="$1" logs_dir="$2" providers="$3" tiers="$4" extra="$5"
  shift 5
  local phenos=("$@")
  mkdir -p "$logs_dir"
  local start; start=$(date +%s)
  echo "============================================================"
  echo "PHASE: $label"
  echo "  phenotypes: ${#phenos[@]}  providers: $providers  tiers: $tiers  variant: expert"
  echo "  shards: $N_SERVERS  logs: $logs_dir  extra: $extra"
  echo "============================================================"
  for ((s=0; s<N_SERVERS; s++)); do
    shard=()
    for ((i=s; i<${#phenos[@]}; i+=N_SERVERS)); do shard+=("${phenos[i]}"); done
    if [[ ${#shard[@]} -eq 0 ]]; then continue; fi
    local server="${SERVERS[s]}" log="$logs_dir/shard-${s}.log"
    echo "[shard $s] $server  <- ${#shard[@]} phenos  log=$log"
    (
      # shellcheck disable=SC2086
      python scripts/run_isolated_suite.py "${shard[@]}" \
        --providers $providers \
        --tiers "$tiers" \
        --prompt-variants "expert" \
        --fhir-url "$server" \
        --max-cell-workers 1 \
        $extra
    ) > "$log" 2>&1 &
  done
  wait
  echo "PHASE $label complete ($(( $(date +%s) - start ))s)"
  for ((s=0; s<N_SERVERS; s++)); do
    log="$logs_dir/shard-${s}.log"; [[ -f "$log" ]] && { echo "--- shard $s ---"; tail -2 "$log"; }
  done
}

GRAND_START=$(date +%s)

run_phase "1 (91 x 3 frontier models x T1+T2+T3 x expert)" \
  "logs/expert-rerun/phase1" \
  "copilot:gpt-5.4 copilot:claude-opus-4.7 copilot:claude-sonnet-4.6" \
  "1,2,3" "" \
  "${PHENOS[@]}"

run_phase "2 (91 x opus+fhirskill x T1 x expert)" \
  "logs/expert-rerun/phase2" \
  "copilot:claude-opus-4.7" \
  "1" "--skill-file $SKILL" \
  "${PHENOS[@]}"

echo "============================================================"
echo "EXPERT RERUN GRAND TOTAL: $(( $(date +%s) - GRAND_START ))s"
echo "============================================================"
