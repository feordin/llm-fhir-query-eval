#!/usr/bin/env bash
# Full decoupled Opus T1 backfill, end to end and unattended.
#
# Decoupled design (fixes the concurrent-reload blocker): T1 is closed-book, so
# generation never touches the FHIR server. We generate EVERYTHING first (no
# reloads, parallel), then score one phenotype at a time with the server reload
# running exclusively -- zero competing LLM subprocesses, so the bundle probes
# never starve. See scripts/run_t1_decoupled.py.
#
# Phases:
#   0. wait for the in-flight +T3confirm agentic rerun to finish (so its reloads
#      don't collide with our closed-book node.exe fan-out).
#   1. generate  Opus T1 PLAIN   (all 108 phenotypes, naive/broad/expert)
#   2. generate  Opus T1 +SKILL  (Anthropic fhir-developer skill prepended)
#   3. score     BOTH specs       (sequential reload, replay-scored -> canonical)
#   4. aggregate the 3-model + opus-full leaderboard
#
# Copilot closed-book is free (wall-clock only). Run from repo root.
set -uo pipefail
cd "$(dirname "$0")/.."
if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi
export FHIR_BUNDLES_DIR="${FHIR_BUNDLES_DIR:-C:\\fhir-bundles-ext}"
FHIR_URL="https://jaerwinllm.azurewebsites.net"
SKILL="vendor/anthropic-fhir-skill/SKILL.md,vendor/anthropic-fhir-skill/references/resource-examples.md"
mkdir -p logs/opus-t1-decoupled
GS=$(date +%s)
say() { echo "[$(date -u +%H:%M:%SZ) +$(( $(date +%s) - GS ))s] $*"; }

# --- Phase 0: wait for the confirmatory agentic rerun to finish -------------
CONFIRM_LOG="logs/opus-t3-confirm.log"
say "PHASE 0: waiting for +T3confirm rerun to finish (max 75 min)..."
CONFIRM_DONE=0
for ((i=0; i<300; i++)); do
  if [[ -f "$CONFIRM_LOG" ]] && grep -q "SUITE SUMMARY" "$CONFIRM_LOG"; then
    say "  +T3confirm finished."; CONFIRM_DONE=1; break
  fi
  sleep 15
done
[[ $CONFIRM_DONE -eq 0 ]] && say "  WARN: confirm rerun not done after 75 min; proceeding anyway."

# --- Phase 1: generate plain ------------------------------------------------
say "PHASE 1: generate Opus T1 PLAIN (all phenotypes)..."
python scripts/run_t1_decoupled.py generate \
  --model claude-opus-4.7 --max-workers 6 --timeout-sec 240 \
  > logs/opus-t1-decoupled/1-generate-plain.log 2>&1
say "  plain generate rc=$?"

# --- Phase 2: generate +skill ----------------------------------------------
say "PHASE 2: generate Opus T1 +fhirskill (all phenotypes)..."
python scripts/run_t1_decoupled.py generate \
  --model claude-opus-4.7 --max-workers 6 --timeout-sec 300 \
  --skill-file "$SKILL" \
  > logs/opus-t1-decoupled/2-generate-skill.log 2>&1
say "  skill generate rc=$?"

# --- Phase 3: score both specs (sequential reload) --------------------------
say "PHASE 3: score BOTH specs (sequential reload, no LLM)..."
python scripts/run_t1_decoupled.py score \
  --model claude-opus-4.7 --both --fhir-url "$FHIR_URL" \
  > logs/opus-t1-decoupled/3-score.log 2>&1
say "  score rc=$?"

# --- Phase 4: aggregate -----------------------------------------------------
say "PHASE 4: aggregate full leaderboard..."
mapfile -t ALL < <(ls -d synthea/output/*/ | xargs -n1 basename)
python scripts/aggregate_sweep.py --since 20260516T000000Z \
  --label opus-t1-backfill-decoupled \
  --exclude-models ollama +T3fix +T3lean +T3rerun +T3confirm \
  --phenotypes "${ALL[@]}" \
  > logs/opus-t1-decoupled/4-aggregate.log 2>&1
say "  aggregate rc=$?"
say "DONE. Report under docs/results/. Logs under logs/opus-t1-decoupled/."
