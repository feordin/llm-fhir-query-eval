#!/usr/bin/env bash
# Opus T2 backfill to full 108-phenotype / 388-tc coverage (agentic, tier 2).
#
# Unlike T1, T2 is AGENTIC -- the model queries the live isolated server during
# generation, so it cannot use the decoupled closed-book trick. It must go through
# run_isolated_suite (reload -> agentic cells) per phenotype. To keep reloads from
# starving under many concurrent Copilot node.exe cells (the original blocker), we
# use a LOW shard count (3 servers) rather than the 6 used for the closed-book score.
# Within a shard, reload never overlaps its own cells (sequential per phenotype);
# only cross-shard overlap remains, kept modest by 3-way + the path-probe+retry in
# reload_phenotype.py.
#
# New canonical claude-opus-4.7 tier-2 cells supersede the old 48-tc subset via the
# aggregator's latest-non-empty dedup. Running all 108 (incl. the 48) makes the
# full-388 T2 internally consistent (uniform lean-agentic prompt). PREMIUM quota.
set -uo pipefail
cd "$(dirname "$0")/.."
if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi
export FHIR_BUNDLES_DIR="${FHIR_BUNDLES_DIR:-C:\\fhir-bundles-ext}"
mkdir -p logs/opus-t2-backfill/shards
mapfile -t PHENOS < <(ls -d synthea/output/*/ | xargs -n1 basename | sort)
SERVERS=(
  "https://jaerwinllm.azurewebsites.net"
  "https://jaerwinllm2.azurewebsites.net"
  "https://jaerwinllm3.azurewebsites.net"
)
N=${#SERVERS[@]}
echo "OPUS T2 BACKFILL: ${#PHENOS[@]} phenotypes x T2 across $N servers (premium quota)"
for ((s=0; s<N; s++)); do
  shard=()
  for ((i=s; i<${#PHENOS[@]}; i+=N)); do shard+=("${PHENOS[i]}"); done
  [[ ${#shard[@]} -eq 0 ]] && continue
  (
    python scripts/run_isolated_suite.py "${shard[@]}" \
      --providers copilot:claude-opus-4.7 --tiers 2 \
      --prompt-variants naive,broad,expert \
      --fhir-url "${SERVERS[s]}" --max-cell-workers 3
  ) > "logs/opus-t2-backfill/shards/t2-shard-${s}.log" 2>&1 &
  echo "  shard $s -> ${SERVERS[s]} (${#shard[@]} phenos) PID $!"
done
wait
echo "OPUS T2 BACKFILL: ALL SHARDS DONE"
