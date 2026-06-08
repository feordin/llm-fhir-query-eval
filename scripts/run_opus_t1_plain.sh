#!/usr/bin/env bash
# Opus T1 plain closed-book (NO skill, NO tools) on the skill-baseline subset,
# all 3 prompts. Isolates the frontier one-shot baseline -> completes the 3-way:
#   claude-opus-4.7 T1 (plain)  vs  +fhirskill T1 (skill)  vs  claude-opus-4.7 T2 (ours)
# Spec stays 'claude-opus-4.7' (no suffix) -- adds T1 cells alongside the existing T2.
set -uo pipefail
if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi
mkdir -p logs/opus-t1-plain
SUBSET=(type-2-diabetes gerd systemic-lupus-erythematosus osteoporosis
        coronary-heart-disease crohns-disease asthma heart-failure)
S=("https://jaerwinllm.azurewebsites.net" "https://jaerwinllm2.azurewebsites.net"
   "https://jaerwinllm3.azurewebsites.net" "https://jaerwinllm4.azurewebsites.net"
   "https://jaerwinllm5.azurewebsites.net" "https://jaerwinllm6.azurewebsites.net"
   "https://jaerwinllm7.azurewebsites.net" "https://jaerwinllm8.azurewebsites.net")
i=0
for ph in "${SUBSET[@]}"; do
  ( python scripts/run_isolated_suite.py "$ph" --providers copilot:claude-opus-4.7 \
      --tiers 1 --prompt-variants naive,broad,expert \
      --fhir-url "${S[i]}" --max-cell-workers 3
  ) > "logs/opus-t1-plain/${ph}.log" 2>&1 &
  i=$((i+1))
done
wait
echo "OPUS T1 PLAIN COMPLETE"
