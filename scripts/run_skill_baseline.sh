#!/usr/bin/env bash
# Thread A baseline (task #2): best off-the-shelf Opus, closed-book + Anthropic
# fhir-developer skill, vs our best in-house Opus agentic stack. On a representative
# subset spanning easy / trick-Path-C / labs / comprehensive / procedure / negation.
#
#   Run A: copilot:claude-opus-4.7  T1 closed-book + skill  -> spec '+fhirskill'
#   Run B: copilot:claude-opus-4.7  T2 agentic + tools (no skill)
#
# Why T2 (not T3): frontier models PEAK at T2 (sonnet 0.917>0.896, gpt 0.913>=0.906);
# T3's methodology only helps the small qwen. So T2 is the fair "best in-house"
# comparator for an Opus ceiling-vs-ceiling matchup.
#
# Both via Copilot (no OpenRouter cost). Skill = SKILL.md + resource-examples.md.
# Aggregate afterward with --since covering today; the '+fhirskill' suffix makes
# Run A a distinct column from any plain Opus T3.
#
# Prereq: gh auth (Copilot), FHIR servers healthy. Run AFTER the backfill frees
# the servers (this reloads phenotypes).

set -uo pipefail
if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi
mkdir -p logs/skill-baseline

MODEL="copilot:claude-opus-4.7"
SKILL="vendor/anthropic-fhir-skill/SKILL.md,vendor/anthropic-fhir-skill/references/resource-examples.md"
SUBSET=(
  type-2-diabetes gerd systemic-lupus-erythematosus osteoporosis
  coronary-heart-disease crohns-disease asthma heart-failure
)
S=(
 "https://jaerwinllm.azurewebsites.net"  "https://jaerwinllm2.azurewebsites.net"
 "https://jaerwinllm3.azurewebsites.net" "https://jaerwinllm4.azurewebsites.net"
 "https://jaerwinllm5.azurewebsites.net" "https://jaerwinllm6.azurewebsites.net"
 "https://jaerwinllm7.azurewebsites.net" "https://jaerwinllm8.azurewebsites.net"
)

run_phase() {
  local label="$1" tiers="$2" extra="$3"
  echo "=== PHASE $label (tiers $tiers) ==="
  local i=0
  for ph in "${SUBSET[@]}"; do
    local server="${S[i]}" log="logs/skill-baseline/${label}-${ph}.log"
    (
      python scripts/run_isolated_suite.py "$ph" \
        --providers "$MODEL" --tiers "$tiers" \
        --prompt-variants naive,broad,expert \
        --fhir-url "$server" --max-cell-workers 3 $extra
    ) > "$log" 2>&1 &
    i=$((i+1))
  done
  wait
  echo "PHASE $label complete"
}

# Run A: T1 + skill ; Run B: T2 agentic (no skill)
run_phase "A-T1-skill" "1" "--skill-file $SKILL"
run_phase "B-T2"       "2" ""
echo "SKILL BASELINE COMPLETE"
