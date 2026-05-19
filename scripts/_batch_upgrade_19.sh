#!/usr/bin/env bash
# Throwaway batch driver for Task 7 of the rigorous-controls-twenty plan.
# Loops the 19 phenotypes serially: upgrade -> commit per phenotype.
# Halts on first failure so the operator can inspect.
set -uo pipefail

PHENOS=(
  hypertension heart_failure coronary_heart_disease atrial_fibrillation stroke
  copd type_1_diabetes type_2_diabetes hypothyroidism hyperthyroidism ckd
  epilepsy migraine dementia depression anxiety bipolar_disorder
  rheumatoid_arthritis crohns_disease gerd
)

set -a
source .env
set +a

START=$(date +%s)
PASS=()
FAIL=()
for p in "${PHENOS[@]}"; do
  echo
  echo "============================================================"
  echo "[$(date +%H:%M:%S)] BEGIN $p ($(( ${#PASS[@]} + ${#FAIL[@]} + 1 ))/${#PHENOS[@]})"
  echo "============================================================"
  T0=$(date +%s)
  if python scripts/upgrade_phenotype.py "$p"; then
    DUR=$(( $(date +%s) - T0 ))
    echo "[$(date +%H:%M:%S)] $p UPGRADE OK (${DUR}s)"
    # Stage everything that could have changed; some may not exist for all phenotypes.
    git add data/minimal-bundles/${p}*.json.gz \
            test-cases/phekb/phekb-${p}*.json \
            synthea/modules/custom/phekb_${p}*.json 2>/dev/null
    if git diff --cached --quiet; then
      echo "[$(date +%H:%M:%S)] $p NO CHANGES STAGED -- skipping commit"
    elif git commit -m "upgrade: ${p} -- mimicker pack in controls

Batch upgrade per rigorous-controls-twenty plan Task 7.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>" > /dev/null; then
      echo "[$(date +%H:%M:%S)] $p COMMIT OK ($(git log --format=%h -1))"
    else
      echo "[$(date +%H:%M:%S)] $p COMMIT FAILED"
      FAIL+=("$p (commit)")
      continue
    fi
    PASS+=("$p")
  else
    DUR=$(( $(date +%s) - T0 ))
    echo "[$(date +%H:%M:%S)] $p UPGRADE FAILED (${DUR}s) -- HALTING BATCH"
    FAIL+=("$p")
    break
  fi
done

TOTAL=$(( $(date +%s) - START ))
echo
echo "============================================================"
echo "BATCH SUMMARY (${TOTAL}s = $((TOTAL/60))m)"
echo "============================================================"
echo "PASS (${#PASS[@]}): ${PASS[*]:-none}"
echo "FAIL (${#FAIL[@]}): ${FAIL[*]:-none}"
[[ ${#FAIL[@]} -eq 0 ]] && exit 0 || exit 1
