#!/usr/bin/env bash
# FULL MIMIC-IV sweep: all phenotypes with a full-MIMIC cohort, scored against
# data/mimic-full-gold.json (recompute_mimic_gold.py over the 299,712-patient
# credentialed dataset). Shards phenotypes across every server that holds the
# full load (Patient count == 299712); each shard's phenotypes run sequentially
# against its server -- concurrent READS, no reloads. Results tagged '+mimic'.
#
# Usage: bash scripts/run_mimic_full_sweep.sh [paths] [tiers]
#   paths: default dx,comprehensive (demo-comparable); add labs if desired
#   tiers: default 1,2,3
set -uo pipefail
cd "$(dirname "$0")/.."
if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi
PATHS="${1:-dx,comprehensive}"
TIERS="${2:-1,2,3}"
MODEL="${MIMIC_MODEL:-claude-opus-4.7}"
GOLD="data/mimic-full-gold.json"
mkdir -p logs/mimic-full-sweep
ALL=(
  "https://jaerwinllm.azurewebsites.net"  "https://jaerwinllm2.azurewebsites.net"
  "https://jaerwinllm3.azurewebsites.net" "https://jaerwinllm4.azurewebsites.net"
  "https://jaerwinllm5.azurewebsites.net" "https://jaerwinllm6.azurewebsites.net"
  "https://jaerwinllm7.azurewebsites.net" "https://jaerwinllm8.azurewebsites.net"
  "https://jaerwinllm9.azurewebsites.net" "https://jaerwinllm10.azurewebsites.net"
)
# Only shard onto servers that hold the FULL dataset.
SERVERS=()
for u in "${ALL[@]}"; do
  p=$(curl -sk --max-time 20 "$u/Patient?_summary=count" 2>/dev/null | python -c "import json,sys;print(json.load(sys.stdin).get('total'))" 2>/dev/null)
  if [[ "$p" == "299712" ]]; then SERVERS+=("$u"); else echo "  SKIP $u (Patient=$p, not full-loaded)"; fi
done
N=${#SERVERS[@]}
[[ $N -eq 0 ]] && { echo "no full-loaded servers"; exit 1; }
mapfile -t PHENOS < <(python -c "import json;print('\n'.join(json.load(open('$GOLD')).keys()))" | tr -d "\r")
echo "MIMIC FULL SWEEP: ${#PHENOS[@]} phenotypes x {$PATHS} x naive/broad/expert x T$TIERS, $MODEL, $N servers"
for ((s=0; s<N; s++)); do
  shard=()
  for ((i=s; i<${#PHENOS[@]}; i+=N)); do shard+=("${PHENOS[i]}"); done
  [[ ${#shard[@]} -eq 0 ]] && continue
  (
    python scripts/run_mimic_eval.py --phenotypes "${shard[@]}" \
      --paths "$PATHS" --tiers "$TIERS" --variants naive,broad,expert \
      --provider copilot --model "$MODEL" --fhir-url "${SERVERS[s]}" \
      --gold "$GOLD" --lean-prompt
  ) > "logs/mimic-full-sweep/shard-${s}.log" 2>&1 &
  echo "  shard $s -> ${SERVERS[s]} (${#shard[@]} phenos) PID $!"
done
wait
echo "MIMIC FULL SWEEP: ALL SHARDS DONE"
