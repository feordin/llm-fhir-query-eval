#!/usr/bin/env bash
# Tier A batch upgrade: 14 phenotypes with mimicker packs added in commit
# 25a066c8 but not yet patched + regenerated. Same shape as the prior
# _batch_upgrade_19.sh; per-phenotype commit; halts on first failure.
set -uo pipefail

PHENOS=(
  schizophrenia acute-kidney-injury systemic-lupus-erythematosus
  ulcerative-colitis parkinsons-disease multiple-sclerosis
  iron-deficiency-anemia osteoporosis fibromyalgia gout
  venous-thromboembolism pneumonia atopic-dermatitis psoriasis
)

set -a
source .env
set +a

START=$(date +%s)
PASS=()
FAIL=()
for p in "${PHENOS[@]}"; do
  snake=$(echo "$p" | tr - _)
  echo
  echo "============================================================"
  echo "[$(date +%H:%M:%S)] BEGIN $p ($(( ${#PASS[@]} + ${#FAIL[@]} + 1 ))/${#PHENOS[@]})"
  echo "============================================================"
  T0=$(date +%s)
  if python scripts/upgrade_phenotype.py "$p"; then
    DUR=$(( $(date +%s) - T0 ))
    echo "[$(date +%H:%M:%S)] $p UPGRADE OK (${DUR}s)"
    # Stage with BOTH naming conventions; some patterns expand to nothing
    # which would poison a single git-add call -- run them separately so
    # one unmatched pattern doesn't drop the others.
    git add "data/minimal-bundles/${p}-"*.json.gz 2>/dev/null
    git add "test-cases/phekb/phekb-${p}"*.json 2>/dev/null
    git add "synthea/modules/custom/phekb_${snake}_control.json" 2>/dev/null
    git add "synthea/modules/custom/phekb_${snake}.json" 2>/dev/null
    if git diff --cached --quiet; then
      echo "[$(date +%H:%M:%S)] $p NO CHANGES STAGED -- skipping commit"
    elif git commit -m "upgrade: ${p} -- mimicker pack in controls (Tier A)

Batch upgrade per rigorous-controls-twenty plan, Tier A extension
(14 phenotypes that had curated differentials in the audit script).

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
