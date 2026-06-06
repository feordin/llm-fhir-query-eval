#!/usr/bin/env bash
# Targeted fill of qwen empty cells left by the original sweep's 403 key-limit
# casualties (501 cells) + a handful of 402/timeout/other (76 cells). ALL 577
# empties are infra errors, NOT genuine qwen failures (verified 2026-06-05).
#
#   Pass 1: full 108 phenotypes x T1 only  -> fills 495 cheap closed-book cells.
#   Pass 2: the 45 phenotypes that have >=1 T2/T3 empty x T2+T3 -> fills 82
#           agentic cells (the cost driver).
#
# 10-server fan-out, single openai-compat:qwen/qwen3.5-9b spec, auto-lean.
# non-empty-wins dedup in aggregate_sweep.py makes every rerun additive: good
# cells are preserved, only empties get refilled.
#
# Budget at launch (2026-06-05): account balance ~$19.74, key headroom ~$50.
# Est. spend ~$10 (T1 ~free, ~348 agentic T2/T3 cells @ ~$0.007). Safe.
#
# Phase selection: RUN_PHASE_1=0 / RUN_PHASE_2=0 to skip either.

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

# All 108 phenotypes (NEW 73 + OLD 35).
PHENOS_ALL=(
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
  anxiety asthma atrial-fibrillation bipolar-disorder ckd copd
  coronary-heart-disease crohns-disease dementia depression epilepsy gerd
  heart-failure hypertension hyperthyroidism hypothyroidism migraine
  rheumatoid-arthritis stroke type-1-diabetes type-2-diabetes
  acute-kidney-injury atopic-dermatitis fibromyalgia gout
  iron-deficiency-anemia multiple-sclerosis osteoporosis parkinsons-disease
  pneumonia psoriasis schizophrenia systemic-lupus-erythematosus
  ulcerative-colitis venous-thromboembolism
)

# The 45 phenotypes with >=1 T2/T3 empty cell (derived 2026-06-05).
PHENOS_T23=(
  adhd asthma-response-inhaled-steroids atopic-dermatitis breast-cancer ca-mrsa
  cardiorespiratory-fitness cataracts colorectal-cancer coronary-heart-disease
  crohns-disease developmental-language-disorder drug-induced-liver-injury
  epilepsy familial-hypercholesterolemia febrile-neutropenia-pediatric gerd
  hearing-loss heart-failure hepatitis-c herpes-zoster hiv hypothyroidism
  intellectual-disability leukemia liver-cancer liver-cancer-staging migraine
  multiple-sclerosis nafld ovarian-cancer pancreatic-cancer
  peripheral-arterial-disease pneumonia prostate-cancer psoriasis
  resistant-hypertension rheumatoid-arthritis severe-childhood-obesity
  sickle-cell-disease statins-and-mace steroid-induced-avn type-1-diabetes
  ulcerative-colitis urinary-incontinence venous-thromboembolism
)

run_phase() {
  local label="$1" logs_dir="$2" tiers="$3"; shift 3
  local phenos=("$@")
  mkdir -p "$logs_dir"
  local start; start=$(date +%s)
  echo "============================================================"
  echo "PHASE: $label   phenotypes: ${#phenos[@]}  tiers: $tiers"
  echo "============================================================"
  for ((s=0; s<N_SERVERS; s++)); do
    shard=()
    for ((i=s; i<${#phenos[@]}; i+=N_SERVERS)); do shard+=("${phenos[i]}"); done
    [[ ${#shard[@]} -eq 0 ]] && continue
    local server="${SERVERS[s]}" log="$logs_dir/shard-${s}.log"
    echo "[shard $s] $server  <- ${#shard[@]} phenos  log=$log"
    (
      python scripts/run_isolated_suite.py "${shard[@]}" \
        --providers "$PROVIDER_SPEC" \
        --base-url "$BASE_URL" \
        --tiers "$tiers" \
        --prompt-variants "naive,broad,expert" \
        --fhir-url "$server" \
        --max-cell-workers 2
    ) > "$log" 2>&1 &
  done
  wait
  echo "PHASE $label complete ($(( $(date +%s) - start ))s)"
}

GRAND_START=$(date +%s)
RUN_PHASE_1="${RUN_PHASE_1:-1}"
RUN_PHASE_2="${RUN_PHASE_2:-1}"
if [[ "$RUN_PHASE_1" == "1" ]]; then
  run_phase "1 (108 x qwen x T1 fill)" "logs/qwen-fill/phase1" "1" "${PHENOS_ALL[@]}"
fi
if [[ "$RUN_PHASE_2" == "1" ]]; then
  run_phase "2 (45 x qwen x T2+T3 fill)" "logs/qwen-fill/phase2" "2,3" "${PHENOS_T23[@]}"
fi
echo "GRAND TOTAL: $(( $(date +%s) - GRAND_START ))s"
