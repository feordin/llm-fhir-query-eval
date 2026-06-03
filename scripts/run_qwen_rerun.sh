#!/usr/bin/env bash
# Rerun qwen lean on:
#   Phase A: 73 NEW phenotypes x T1+T2+T3 x naive/broad/expert
#            (replaces 707 cells that hit OpenRouter "Key limit exceeded"
#             during the June 2-3 full sweep, plus 630 cascade backend
#             errors).
#   Phase B: 35 OLD phenotypes x T2+T3 x naive/broad/expert
#            (re-fills the cells that the June 2-3 Phase-2 T1-only run
#             clobbered in the prior aggregator; the new aggregator's
#             non-empty-wins dedup makes this rerun additive even if it
#             only partially succeeds).
#
# 10-server fan-out, single openai-compat:qwen/qwen3.5-9b spec.
# Auto-lean fires (qwen3.5-9b is in SMALL_MODEL_PATTERNS).
# --max-cell-workers 2 -> ~20 concurrent OpenRouter conns.
#
# Prereqs (BEFORE running this):
#   - OpenRouter key has spending budget. Last run hit a $20 ceiling and
#     produced ~55% empty cells. Verify with:
#       curl -H "Authorization: Bearer $OPENAI_COMPAT_API_KEY" \
#            https://openrouter.ai/api/v1/auth/key | jq '.data | {usage, limit, limit_remaining}'

set -uo pipefail

if [[ -f .env ]]; then
  set -o allexport
  # shellcheck disable=SC1091
  source .env
  set +o allexport
fi

PROVIDER_SPEC="openai-compat:qwen/qwen3.5-9b"
BASE_URL="https://openrouter.ai/api/v1"
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

PHENOS_NEW=(
  abdominal-aortic-aneurysm ace-inhibitor-cough adhd alcohol-use-disorder
  appendicitis asthma-response-inhaled-steroids autism autoimmune-disease
  bladder-cancer bone-scan-utilization bph breast-cancer ca-mrsa
  cardiac-conduction-qrs cardiorespiratory-fitness carotid-atherosclerosis
  cataracts cervical-cancer chronic-rhinosinusitis clopidogrel-poor-metabolizers
  clostridium-difficile colorectal-cancer cystic-fibrosis
  developmental-language-disorder diabetic-retinopathy digital-rectal-exam
  diverticulitis down-syndrome drug-induced-liver-injury endometriosis
  esophageal-cancer familial-hypercholesterolemia febrile-neutropenia-pediatric
  functional-seizures glaucoma glioblastoma hearing-loss hepatitis-c
  herpes-zoster hiv influenza intellectual-disability leukemia liver-cancer
  liver-cancer-staging lung-cancer lyme-disease lymphoma melanoma
  multimodal-analgesia multiple-myeloma nafld neonatal-abstinence-syndrome
  ovarian-cancer pancreatic-cancer peanut-allergy peripheral-arterial-disease
  polycystic-kidney-disease post-event-pain prostate-cancer renal-cancer
  resistant-hypertension sepsis severe-childhood-obesity sickle-cell-disease
  sleep-apnea statins-and-mace steroid-induced-avn stomach-cancer thyroid-cancer
  tuberculosis urinary-incontinence warfarin-dose-response
)

PHENOS_OLD=(
  anxiety asthma atrial-fibrillation bipolar-disorder ckd copd
  coronary-heart-disease crohns-disease dementia depression epilepsy gerd
  heart-failure hypertension hyperthyroidism hypothyroidism migraine
  rheumatoid-arthritis stroke type-1-diabetes type-2-diabetes
  acute-kidney-injury atopic-dermatitis fibromyalgia gout
  iron-deficiency-anemia multiple-sclerosis osteoporosis parkinsons-disease
  pneumonia psoriasis schizophrenia systemic-lupus-erythematosus
  ulcerative-colitis venous-thromboembolism
)

run_phase() {
  local label="$1"
  local logs_dir="$2"
  local tiers="$3"
  shift 3
  local phenos=("$@")
  mkdir -p "$logs_dir"

  local start=$(date +%s)
  echo "============================================================"
  echo "PHASE: $label"
  echo "  phenotypes: ${#phenos[@]}  tiers: $tiers"
  echo "============================================================"

  for ((s=0; s<N_SERVERS; s++)); do
    shard=()
    for ((i=s; i<${#phenos[@]}; i+=N_SERVERS)); do
      shard+=("${phenos[i]}")
    done
    if [[ ${#shard[@]} -eq 0 ]]; then continue; fi
    server="${SERVERS[s]}"
    log="$logs_dir/shard-${s}.log"
    echo "[shard $s] $server  <- ${#shard[@]} phenos  log=$log"
    (
      python scripts/run_isolated_suite.py "${shard[@]}" \
        --providers "$PROVIDER_SPEC" \
        --base-url "$BASE_URL" \
        --tiers "$tiers" \
        --prompt-variants "naive,broad,expert" \
        --fhir-url "$server" \
        --max-cell-workers 2 \
        2>&1
    ) > "$log" 2>&1 &
  done
  wait
  echo "PHASE $label complete ($(( $(date +%s) - start ))s)"
}

GRAND_START=$(date +%s)
run_phase "A (73 new x qwen x T1+T2+T3)" "logs/qwen-rerun/phaseA" "1,2,3" "${PHENOS_NEW[@]}"
run_phase "B (35 old x qwen x T2+T3)"   "logs/qwen-rerun/phaseB" "2,3"   "${PHENOS_OLD[@]}"
echo "GRAND TOTAL: $(( $(date +%s) - GRAND_START ))s"
