"""Per-phenotype regeneration cycle: produces fresh Synthea data sized to the
phenotype's test cases, refreshes expected_patient_ids, rebuilds the minimal
bundle, and verifies the resulting setup loads cleanly.

Cycle:
  1. compute_target()      -- read test cases, derive raw patient count
  2. synthea generate      -- python synthea/generate_test_data.py ...
  3. augment_fhir_codes    -- python scripts/augment_fhir_codes.py --phenotype <pheno>
  4. build_minimal_bundles -- python scripts/build_minimal_bundles.py <pheno>
  5. reload_phenotype      -- python scripts/reload_phenotype.py <pheno>
                              (wipe + load; the loaded server is what the next step queries)
  6. rederive              -- python scripts/rederive_expected_patients.py <pheno>
  7. final verify          -- python scripts/reload_phenotype.py <pheno> --no-wipe
                              (re-runs verify; should now PASS)

Usage:
    python scripts/regenerate_phenotype.py coronary-heart-disease
    python scripts/regenerate_phenotype.py heart-failure --dry-run-counts

`--skip-generate` skips stages 2-3 only (no Synthea, no augmentation). Stages
4-7 still run, so the FHIR server IS still wiped and reloaded from the existing
synthea/output -- this flag is for "re-derive on current data," not "do nothing
to the server."

Note: augment_fhir_codes.py supports --phenotype filtering (verified via --help),
so this script passes --phenotype rather than running a whole-tree augmentation.

DO NOT run two instances concurrently for different phenotypes -- the server
wipe in stage 5 is destructive across the entire FHIR server.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from reload_phenotype import _test_cases_for  # noqa: E402

PY = sys.executable
SCRIPTS = REPO / "scripts"
TEST_CASES = REPO / "test-cases" / "phekb"
SYNTHEA_GEN = REPO / "synthea" / "generate_test_data.py"

YIELD_FLOOR = 0.15
RAW_FLOOR = 200
RAW_CAP = 3000


def compute_target(phenotype: str) -> tuple[int, int, int]:
    """Return (max_expected_pids, raw_patients, controls)."""
    expected_max = 0
    for f in _test_cases_for(phenotype):
        tc = json.loads(f.read_text(encoding="utf-8"))
        pids = tc.get("test_data", {}).get("expected_patient_ids") or []
        expected_max = max(expected_max, len(pids))
    raw = max(RAW_FLOOR, min(RAW_CAP, math.ceil(expected_max / YIELD_FLOOR)))
    controls = max(30, raw // 5)
    return expected_max, raw, controls


def _run(label: str, cmd: list[str], timeout: int | None = None) -> int:
    """Run a stage subprocess with optional wall-clock timeout. Returns its
    exit code, or 124 (conventional timeout exit) if the timeout fires."""
    print(f"\n--- {label} ---", flush=True)
    print(f"$ {' '.join(cmd)}", flush=True)
    t0 = time.time()
    try:
        rc = subprocess.run(cmd, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print(f"--- {label}: TIMEOUT after {timeout}s ---", flush=True)
        return 124
    print(f"--- {label}: rc={rc} ({int(time.time() - t0)}s) ---", flush=True)
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phenotype")
    ap.add_argument("--dry-run-counts", action="store_true",
                    help="print computed patient count and exit")
    ap.add_argument("--skip-generate", action="store_true",
                    help="skip Synthea generation (re-derive only on existing data)")
    args = ap.parse_args()

    expected_max, raw, controls = compute_target(args.phenotype)
    print(f"[{args.phenotype}] expected_max={expected_max} -> "
          f"generate {raw} positive + {controls} control patients", flush=True)
    if expected_max == 0:
        print(f"WARNING: no test cases with expected_patient_ids found for "
              f"'{args.phenotype}'; using RAW_FLOOR={RAW_FLOOR}. "
              f"Check the phenotype name matches a synthea/output dir.", flush=True)
    if args.dry_run_counts:
        return 0

    t0 = time.time()
    if not args.skip_generate:
        # Synthea can run for an hour+ at 3000 patients; bound it at 2 hours
        # to recover from the rare JVM hang (see batch 21 memory note).
        rc = _run("synthea generate",
                  [PY, str(SYNTHEA_GEN), "--phenotype", args.phenotype,
                   "--patients", str(raw), "--controls", str(controls)],
                  timeout=7200)
        if rc != 0:
            return rc
        rc = _run("augment_fhir_codes",
                  [PY, str(SCRIPTS / "augment_fhir_codes.py"),
                   "--phenotype", args.phenotype])
        if rc != 0:
            return rc

    rc = _run("build_minimal_bundles",
              [PY, str(SCRIPTS / "build_minimal_bundles.py"), args.phenotype])
    if rc != 0:
        return rc
    rc = _run("reload (wipe + load)",
              [PY, str(SCRIPTS / "reload_phenotype.py"), args.phenotype])
    # reload returns 1 if verify fails; that's expected here -- we haven't
    # re-derived yet. Fail only on hard error (rc not in {0, 1}).
    if rc not in (0, 1):
        return rc
    rc = _run("rederive expected_patient_ids",
              [PY, str(SCRIPTS / "rederive_expected_patients.py"), args.phenotype])
    if rc != 0:
        return rc
    rc = _run("final verify (no wipe)",
              [PY, str(SCRIPTS / "reload_phenotype.py"), args.phenotype, "--no-wipe"])
    print(f"\n[{args.phenotype}] regeneration cycle "
          f"{'PASS' if rc == 0 else 'FAIL'} in {int(time.time() - t0)}s", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
