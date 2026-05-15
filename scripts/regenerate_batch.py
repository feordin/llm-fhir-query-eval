# scripts/regenerate_batch.py
"""Run regenerate_phenotype.py over a list of phenotypes (or the full FAIL
list from the 2026-05-14 triage). Per-phenotype fail-fast: a failure logs
and continues to the next phenotype rather than aborting the whole batch.

Per-phenotype output is streamed live to the operator's terminal AND tee'd
to ``results/regen-logs/regen-<phenotype>.log`` for post-hoc triage. Each
phenotype is bounded by a 1-hour wall-clock cap; on timeout the subprocess
is killed and the batch continues.

Usage:
    python scripts/regenerate_batch.py                 # full 37-phenotype FAIL list
    python scripts/regenerate_batch.py stroke ckd      # specific phenotypes
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
REGEN = str(REPO / "scripts" / "regenerate_phenotype.py")
LOGS_DIR = REPO / "results" / "regen-logs"
PER_PHENOTYPE_TIMEOUT = 3600  # 1 hour cap; CHD pilot finished in ~4 min

# 37 FAIL phenotypes from the 2026-05-14 contamination triage
# (bykphfac8.output -- TRIAGE SUMMARY block).
DEFAULT_PHENOTYPES = [
    "atopic-dermatitis", "atrial-fibrillation", "bipolar-disorder",
    "breast-cancer", "carotid-atherosclerosis", "cervical-cancer",
    "ckd", "clopidogrel-poor-metabolizers", "coronary-heart-disease",
    "crohns-disease", "dementia", "depression", "drug-induced-liver-injury",
    "epilepsy", "familial-hypercholesterolemia", "gerd", "heart-failure",
    "hepatitis-c", "hypertension", "hypothyroidism", "lyme-disease",
    "multiple-sclerosis", "nafld", "neonatal-abstinence-syndrome",
    "ovarian-cancer", "peripheral-arterial-disease", "pneumonia",
    "rheumatoid-arthritis", "sepsis", "sickle-cell-disease",
    "steroid-induced-avn", "stroke", "systemic-lupus-erythematosus",
    "type-1-diabetes", "type-2-diabetes", "ulcerative-colitis",
    "venous-thromboembolism",
]


def _run_one(phenotype: str) -> int:
    """Run regenerate_phenotype for one phenotype. Streams output to both the
    operator's terminal and a per-phenotype log file. Bounded by
    PER_PHENOTYPE_TIMEOUT; returns 124 (conventional timeout exit) on hang."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"regen-{phenotype}.log"
    with log_path.open("w", encoding="utf-8") as logf:
        proc = subprocess.Popen(
            [PY, REGEN, phenotype],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                logf.write(line)
            return proc.wait(timeout=PER_PHENOTYPE_TIMEOUT)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            msg = f"\n!! [{phenotype}] TIMEOUT after {PER_PHENOTYPE_TIMEOUT}s -- killed\n"
            sys.stdout.write(msg)
            logf.write(msg)
            return 124


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phenotypes", nargs="*", help="empty = full FAIL list")
    args = ap.parse_args()
    phenos = args.phenotypes or DEFAULT_PHENOTYPES

    results = []
    suite_t0 = time.time()
    for i, p in enumerate(phenos, 1):
        print(f"\n{'#' * 72}\n# [{i}/{len(phenos)}] {p}\n{'#' * 72}", flush=True)
        t0 = time.time()
        rc = _run_one(p)
        results.append((p, rc, int(time.time() - t0)))

    print(f"\n{'#' * 72}\n# BATCH SUMMARY ({int(time.time() - suite_t0)}s)\n{'#' * 72}")
    npass = sum(1 for _, rc, _ in results if rc == 0)
    print(f"{len(results)} phenotypes: {npass} PASS, {len(results) - npass} FAIL\n")
    for p, rc, secs in sorted(results, key=lambda r: (r[1], r[0])):
        print(f"  {p:42} {'PASS' if rc == 0 else 'FAIL'}  ({secs}s)")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
