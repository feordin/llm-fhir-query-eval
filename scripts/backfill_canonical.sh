#!/usr/bin/env bash
# Surgical backfill of the targeted canonical-case gaps (2026-06-07):
#   - gpt-sepsis-comprehensive: whole case (9 cells) never run, via Copilot.
#   - 8 qwen cells across 6 comprehensive cases, via OpenRouter (lean).
# Each job reloads its phenotype on a dedicated server (reload wipes), then runs
# only the missing tier/variant. non-empty-wins dedup keeps existing good cells.

set -uo pipefail
if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi
mkdir -p logs/backfill

OR="https://openrouter.ai/api/v1"
S=(
 "https://jaerwinllm.azurewebsites.net"
 "https://jaerwinllm2.azurewebsites.net"
 "https://jaerwinllm3.azurewebsites.net"
 "https://jaerwinllm4.azurewebsites.net"
 "https://jaerwinllm5.azurewebsites.net"
 "https://jaerwinllm6.azurewebsites.net"
 "https://jaerwinllm7.azurewebsites.net"
)

# job: pheno|test_case|provider|model|baseurl|lean|tiers|variants
JOBS=(
 "sepsis|phekb-sepsis-comprehensive|copilot|gpt-5.4|||1,2,3|naive,broad,expert"
 "familial-hypercholesterolemia|phekb-familial-hypercholesterolemia-comprehensive|openai-compat|qwen/qwen3.5-9b|$OR|--lean-prompt|2|broad"
 "hepatitis-c|phekb-hepatitis-c-comprehensive|openai-compat|qwen/qwen3.5-9b|$OR|--lean-prompt|2|naive"
 "liver-cancer-staging|phekb-liver-cancer-staging-comprehensive|openai-compat|qwen/qwen3.5-9b|$OR|--lean-prompt|2|broad"
 "ovarian-cancer|phekb-ovarian-cancer-comprehensive|openai-compat|qwen/qwen3.5-9b|$OR|--lean-prompt|2|broad"
 "type-1-diabetes|phekb-type-1-diabetes-comprehensive|openai-compat|qwen/qwen3.5-9b|$OR|--lean-prompt|3|naive"
 "type-2-diabetes|phekb-type-2-diabetes-comprehensive|openai-compat|qwen/qwen3.5-9b|$OR|--lean-prompt|1|naive,broad,expert"
)

i=0
for job in "${JOBS[@]}"; do
  IFS='|' read -r pheno tc prov model baseurl lean tiers vars <<< "$job"
  server="${S[i]}"; log="logs/backfill/${pheno}.log"
  (
    export FHIR_RELOAD_URL="$server"
    echo "[$pheno] reload on $server"
    python scripts/reload_phenotype.py "$pheno"
    bflag=(); [[ -n "$baseurl" ]] && bflag=(--base-url "$baseurl")
    lflag=(); [[ -n "$lean" ]] && lflag=("$lean")
    echo "[$pheno] matrix $prov:$model t=$tiers v=$vars"
    python scripts/run_sanity_matrix.py -t "$tc" --provider "$prov" --model "$model" \
      "${bflag[@]}" "${lflag[@]}" --tiers "$tiers" --prompt-variants "$vars" --fhir-url "$server"
  ) > "$log" 2>&1 &
  i=$((i+1))
done
wait
echo "BACKFILL COMPLETE"
