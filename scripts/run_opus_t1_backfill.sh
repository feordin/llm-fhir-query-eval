#!/usr/bin/env bash
# Opus T1 backfill (2026-06-10): extend the frontier closed-book comparison from
# the 8-phenotype skill-baseline subset to ALL 108 phenotypes, so the 3-way
#   Opus T1 plain  vs  Opus T1 + Anthropic skill (+fhirskill)  vs  Opus T3 (ours)
# is computed over the same full test-case set (T3 is already full-108).
#
# Two passes over the 100 phenotypes NOT in the original subset (non-empty-wins
# dedup keeps the existing 8). T1 is closed-book (single completion, no agentic
# loop) -- cheap; the per-phenotype reload is the only real cost.
#   Phase A: copilot:claude-opus-4.7  T1 plain  (no skill)        -> spec 'claude-opus-4.7'
#   Phase B: copilot:claude-opus-4.7  T1 + skill (--skill-file)   -> spec '+fhirskill'
# T2 is intentionally NOT backfilled (the requested comparison is T1/skill/T3).
#
# Copilot = free (wall-clock only). 10-server fan-out.

set -uo pipefail
if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi
mkdir -p logs/opus-t1-backfill

MODEL="copilot:claude-opus-4.7"
SKILL="vendor/anthropic-fhir-skill/SKILL.md,vendor/anthropic-fhir-skill/references/resource-examples.md"
mapfile -t PHENOS < scripts/.opus_backfill_phenos.txt
# Full 10-server fan-out. ROOT CAUSE of the earlier reload failures: the bundles
# live INSIDE the repo (C:\repos\...), which is watched by the VS Code file
# watcher / git / Windows Search indexer. Under dense concurrent access (a fast
# closed-book T1 sweep fires reloads back-to-back, unlike the slow agentic T3
# sweep that spaced them out), that watcher contention makes the directory
# listing intermittently empty -> "no minimal bundles". It is NOT antivirus.
# FIX: read bundles from a copy OUTSIDE the repo via FHIR_BUNDLES_DIR. Verified
# 2026-06-11: 10 concurrent reloads on the external dir = 0 failures, vs 73/83
# failures on the in-repo dir.
# Single-shard (1 server). Under SUSTAINED suite load, concurrent reloads
# intermittently see an empty bundles dir at BOTH the in-repo and an external
# path (so it's not purely the repo watcher) -- something escalates as hundreds
# of files are touched over minutes. 5-/10-shard one-shot tests pass but the
# sustained sweep fails. Single-shard has zero such failures; slow (~5-6h for
# 99 x 2 passes) but fully reliable and unattended. FHIR_BUNDLES_DIR still points
# outside the repo as cheap insurance.
export FHIR_BUNDLES_DIR="${FHIR_BUNDLES_DIR:-C:\\fhir-bundles-ext}"
SERVERS=(
  "https://jaerwinllm.azurewebsites.net"
)
N=${#SERVERS[@]}
GRAND_START=$(date +%s)
echo "OPUS T1 BACKFILL: ${#PHENOS[@]} phenotypes x {plain, +skill} x T1 over $N servers"

run_phase() {
  local label="$1" extra="$2"
  echo "=== PHASE $label  $(date -u +%H:%M:%SZ) ==="
  for ((s=0; s<N; s++)); do
    shard=()
    for ((i=s; i<${#PHENOS[@]}; i+=N)); do shard+=("${PHENOS[i]}"); done
    [[ ${#shard[@]} -eq 0 ]] && continue
    (
      # shellcheck disable=SC2086
      python scripts/run_isolated_suite.py "${shard[@]}" \
        --providers "$MODEL" --tiers 1 \
        --prompt-variants naive,broad,expert \
        --fhir-url "${SERVERS[s]}" --max-cell-workers 1 $extra
    ) > "logs/opus-t1-backfill/${label}-shard-${s}.log" 2>&1 &
  done
  wait
  echo "PHASE $label complete ($(( $(date +%s) - GRAND_START ))s elapsed)"
}

run_phase "A-plain" ""
run_phase "B-skill" "--skill-file $SKILL"
echo "OPUS T1 BACKFILL COMPLETE ($(( $(date +%s) - GRAND_START ))s)"
