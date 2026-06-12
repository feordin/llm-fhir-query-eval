#!/usr/bin/env bash
# MIMIC demo sweep: all phenotypes with a MIMIC cohort, scored against the
# recomputed MIMIC gold (data/mimic-gold.json). The demo is loaded on ONE server
# (jaerwinllm4), so we shard the phenotypes across N parallel run_mimic_eval.py
# processes all hitting that static server -- concurrent READS, no reloads, no
# contention. Opus, dx + comprehensive paths, naive/broad/expert x T1/T2/T3,
# lean methodology (matches the synthetic canonical). Results tagged '+mimic'.
set -uo pipefail
cd "$(dirname "$0")/.."
if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi
MODEL="${MIMIC_MODEL:-claude-opus-4.7}"
mkdir -p logs/mimic-demo-sweep
# All 10 servers, each loaded with the same static MIMIC demo. One shard per
# server: shard's phenotypes run sequentially against its server (no reloads).
ALL=(
  "https://jaerwinllm.azurewebsites.net"  "https://jaerwinllm2.azurewebsites.net"
  "https://jaerwinllm3.azurewebsites.net" "https://jaerwinllm4.azurewebsites.net"
  "https://jaerwinllm5.azurewebsites.net" "https://jaerwinllm6.azurewebsites.net"
  "https://jaerwinllm7.azurewebsites.net" "https://jaerwinllm8.azurewebsites.net"
  "https://jaerwinllm9.azurewebsites.net" "https://jaerwinllm10.azurewebsites.net"
)
# Only use servers actually loaded with the MIMIC demo (Patient count == 100).
SERVERS=()
for u in "${ALL[@]}"; do
  p=$(curl -sk --max-time 20 "$u/Patient?_summary=count" 2>/dev/null | python -c "import json,sys;print(json.load(sys.stdin).get('total'))" 2>/dev/null)
  if [[ "$p" == "100" ]]; then SERVERS+=("$u"); else echo "  SKIP $u (Patient=$p, not loaded)"; fi
done
N=${#SERVERS[@]}
[[ $N -eq 0 ]] && { echo "no loaded servers"; exit 1; }
mapfile -t PHENOS < <(python -c "import json;print('\n'.join(json.load(open('data/mimic-gold.json')).keys()))" | tr -d "\r")
echo "MIMIC DEMO SWEEP: ${#PHENOS[@]} phenotypes x {dx,comprehensive} x naive/broad/expert x T1/T2/T3, $MODEL, $N servers"
for ((s=0; s<N; s++)); do
  shard=()
  for ((i=s; i<${#PHENOS[@]}; i+=N)); do shard+=("${PHENOS[i]}"); done
  [[ ${#shard[@]} -eq 0 ]] && continue
  (
    python scripts/run_mimic_eval.py --phenotypes "${shard[@]}" \
      --paths dx,comprehensive --tiers 1,2,3 --variants naive,broad,expert \
      --provider copilot --model "$MODEL" --fhir-url "${SERVERS[s]}" --lean-prompt
  ) > "logs/mimic-demo-sweep/shard-${s}.log" 2>&1 &
  echo "  shard $s -> ${SERVERS[s]} (${#shard[@]} phenos) PID $!"
done
wait
echo "MIMIC DEMO SWEEP: ALL SHARDS DONE"
