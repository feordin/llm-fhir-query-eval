#!/usr/bin/env bash
# Full 108-phenotype sweep across qwen + sonnet + gpt-5.4.
#
# Phase 1: 73 NEW phenotypes (just got mimicker packs this session) x
#   {openai-compat:qwen/qwen3.5-9b, copilot:claude-sonnet-4.6, copilot:gpt-5.4}
#   x tiers 1,2,3 x naive,broad,expert.
# Phase 2: 35 OLD phenotypes x qwen ONLY x tier 1 (closed-book gap; the
#   May-31 sweep ran T2+T3 for qwen on these but not T1).
#
# All 3 specs share each per-phenotype load so we only wipe-and-load each
# phenotype ONCE per server. Phase 1 runs all 10 servers in parallel.
#
# Concurrency: 10 shards * 3 specs * --max-cell-workers 1 = 30 concurrent
# cells, of which ~10 are openrouter conns (safe vs ~20 ceiling) and ~20
# are Copilot CLIs (more than the prior 8-CLI ceiling, but spread across
# 10 shard subprocesses).
#
# Auto-lean fires for qwen ONLY (qwen3.5-9b in SMALL_MODEL_PATTERNS).
# Copilot frontier models stay on the full agentic + methodology prompt.

set -uo pipefail

if [[ -f .env ]]; then
  set -o allexport
  # shellcheck disable=SC1091
  source .env
  set +o allexport
fi

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

# 73 NEW phenotypes (every phenotype that got a mimicker pack this session)
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

# 35 OLD phenotypes (rigorous-21 + Tier A 14) -- already have qwen lean T2+T3
# and full sonnet/gpt T1+T2+T3 from May 27/29/31. Only qwen T1 is missing.
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
  local providers="$3"
  local tiers="$4"
  shift 4
  local phenos=("$@")
  mkdir -p "$logs_dir"

  local start=$(date +%s)
  echo "============================================================"
  echo "PHASE: $label"
  echo "  phenotypes: ${#phenos[@]}  providers: $providers  tiers: $tiers"
  echo "  shards: $N_SERVERS  logs: $logs_dir"
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
      # shellcheck disable=SC2086
      python scripts/run_isolated_suite.py "${shard[@]}" \
        --providers $providers \
        --base-url "$BASE_URL" \
        --tiers "$tiers" \
        --prompt-variants "naive,broad,expert" \
        --fhir-url "$server" \
        --max-cell-workers 1 \
        2>&1
    ) > "$log" 2>&1 &
  done
  wait
  echo "------------------------------------------------------------"
  echo "PHASE $label complete ($(( $(date +%s) - start ))s)"
  echo "------------------------------------------------------------"
  for ((s=0; s<N_SERVERS; s++)); do
    log="$logs_dir/shard-${s}.log"
    [[ -f "$log" ]] && { echo "--- shard $s ---"; tail -3 "$log"; }
  done
}

GRAND_START=$(date +%s)

# Phase 1: 73 NEW phenotypes x all 3 specs x T1+T2+T3
run_phase "Phase 1 (73 new x 3 models x T1+T2+T3)" \
  "logs/full-sweep/phase1" \
  "openai-compat:qwen/qwen3.5-9b copilot:claude-sonnet-4.6 copilot:gpt-5.4" \
  "1,2,3" \
  "${PHENOS_NEW[@]}"

# Phase 2: 35 OLD phenotypes x qwen ONLY x T1 (closes qwen T1 gap)
run_phase "Phase 2 (35 old x qwen x T1)" \
  "logs/full-sweep/phase2" \
  "openai-compat:qwen/qwen3.5-9b" \
  "1" \
  "${PHENOS_OLD[@]}"

echo "============================================================"
echo "GRAND TOTAL: $(( $(date +%s) - GRAND_START ))s"
echo "============================================================"
