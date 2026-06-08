#!/usr/bin/env bash
# T3 investigation (task #5): why did full-methodology T3 collapse on a few
# frontier cells, and would lean help? On the 5 worst-regressed phenotypes, run
# sonnet + gpt at T3 two ways, tagged as distinct specs (no main-report corruption):
#   +T3rerun : FULL methodology, fresh run  -> variance test (does the collapse repeat?)
#   +T3lean  : LEAN methodology              -> "lean for all?" test
# Compare both vs the original full-T3 numbers already in the report.
set -uo pipefail
if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi
mkdir -p logs/t3-exp
PHENOS=(glaucoma tuberculosis neonatal-abstinence-syndrome iron-deficiency-anemia febrile-neutropenia-pediatric)
PROVIDERS="copilot:claude-sonnet-4.6 copilot:gpt-5.4"
S=("https://jaerwinllm.azurewebsites.net" "https://jaerwinllm2.azurewebsites.net"
   "https://jaerwinllm3.azurewebsites.net" "https://jaerwinllm4.azurewebsites.net"
   "https://jaerwinllm5.azurewebsites.net")

run_phase() {
  local label="$1" suffix="$2" extra="$3"
  echo "=== PHASE $label ==="
  local i=0
  for ph in "${PHENOS[@]}"; do
    ( python scripts/run_isolated_suite.py "$ph" --providers $PROVIDERS \
        --tiers 3 --prompt-variants naive,broad,expert \
        --label-suffix "$suffix" $extra \
        --fhir-url "${S[i]}" --max-cell-workers 3
    ) > "logs/t3-exp/${label}-${ph}.log" 2>&1 &
    i=$((i+1))
  done
  wait
  echo "PHASE $label done"
}

run_phase "rerun" "+T3rerun" ""
run_phase "lean"  "+T3lean"  "--lean-prompt"
echo "T3 EXPERIMENT COMPLETE"
