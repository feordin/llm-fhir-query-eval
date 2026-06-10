#!/usr/bin/env bash
# T3 refresh under the 2026-06 "lean for all" + birthdate-guard fixes.
#
# WHAT CHANGED (why this rerun exists):
#   1. Lean is now the DEFAULT methodology for ALL models (run_isolated_suite.py
#      decide_lean) -- frontier models no longer get the full ~16 KB prompt that
#      over-constrained them.
#   2. The Age-restricted playbook (full + lean) now forbids adding a
#      patient.birthdate filter just because a disease NAME contains an age word
#      (neonatal/juvenile/congenital). This fixes the systematic NAS regression.
#
# Reruns Tier 3 for the two FREE GitHub Copilot frontier models across all 108
# phenotypes, naive+broad+expert. Tagged "+T3fix" via --label-suffix so it lands
# as a DISTINCT aggregator column -- the existing canonical T3 data is untouched,
# so we can A/B old-full-T3 vs new-lean-fixed-T3 for the deck and only promote if
# it wins. (Same safe pattern as run_t3_experiment.sh's +T3lean/+T3rerun.)
#
# Copilot has no per-token cost, so this is free; only wall-clock + rate limits.
# 10-server shard fan-out, 2 copilot specs/shard, 1 cell worker = ~20 concurrent
# Copilot CLIs (the envelope run_full_sweep.sh already proved workable).

set -uo pipefail

if [[ -f .env ]]; then
  set -o allexport
  # shellcheck disable=SC1091
  source .env
  set +o allexport
fi

# sonnet-4.6 + gpt-5.4 are FREE Copilot models; opus-4.7 is PREMIUM (counts
# against the Copilot premium-request quota with a multiplier) -- added per the
# 2026-06-09 "include opus" decision after the 5-pheno smoke test confirmed the
# lean+guard gains hold (sonnet 0.88 / gpt 0.81 vs lean target 0.81 / 0.75).
PROVIDERS="copilot:claude-sonnet-4.6 copilot:gpt-5.4 copilot:claude-opus-4.7"
SUFFIX="+T3fix"
SERVERS=(
  "https://jaerwinllm.azurewebsites.net"  "https://jaerwinllm2.azurewebsites.net"
  "https://jaerwinllm3.azurewebsites.net" "https://jaerwinllm4.azurewebsites.net"
  "https://jaerwinllm5.azurewebsites.net" "https://jaerwinllm6.azurewebsites.net"
  "https://jaerwinllm7.azurewebsites.net" "https://jaerwinllm8.azurewebsites.net"
  "https://jaerwinllm9.azurewebsites.net" "https://jaerwinllm10.azurewebsites.net"
)
N_SERVERS=${#SERVERS[@]}

# All 108 phenotypes (73 "new" + 35 "old"), copied from run_full_sweep.sh.
PHENOS=(
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

LOGS_DIR="logs/t3-lean-refresh"
mkdir -p "$LOGS_DIR"
GRAND_START=$(date +%s)

echo "============================================================"
echo "T3 LEAN REFRESH  (suffix=$SUFFIX)"
echo "  phenotypes: ${#PHENOS[@]}  providers: $PROVIDERS  tier: 3"
echo "  shards: $N_SERVERS  logs: $LOGS_DIR"
echo "============================================================"

for ((s=0; s<N_SERVERS; s++)); do
  shard=()
  for ((i=s; i<${#PHENOS[@]}; i+=N_SERVERS)); do
    shard+=("${PHENOS[i]}")
  done
  [[ ${#shard[@]} -eq 0 ]] && continue
  server="${SERVERS[s]}"
  log="$LOGS_DIR/shard-${s}.log"
  echo "[shard $s] $server  <- ${#shard[@]} phenos  log=$log"
  (
    # shellcheck disable=SC2086
    python scripts/run_isolated_suite.py "${shard[@]}" \
      --providers $PROVIDERS \
      --tiers 3 \
      --prompt-variants "naive,broad,expert" \
      --label-suffix "$SUFFIX" \
      --fhir-url "$server" \
      --max-cell-workers 1
  ) > "$log" 2>&1 &
done
wait

echo "------------------------------------------------------------"
echo "T3 LEAN REFRESH complete ($(( $(date +%s) - GRAND_START ))s)"
echo "------------------------------------------------------------"
for ((s=0; s<N_SERVERS; s++)); do
  log="$LOGS_DIR/shard-${s}.log"
  [[ -f "$log" ]] && { echo "--- shard $s ---"; tail -3 "$log"; }
done
