"""End-to-end upgrade for one phenotype:
  1. patch_path_b.py (if Path B missing)
  2. patch_control_module.py
  3. regenerate_phenotype.py  (existing pipeline -- generate, augment, rebuild, verify)

Usage:
    python scripts/upgrade_phenotype.py asthma
    python scripts/upgrade_phenotype.py asthma --skip-regenerate
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
SCRIPTS = REPO / "scripts"


def _run(label: str, cmd: list[str], ok_rcs=(0,)) -> int:
    print(f"\n--- {label} ---\n$ {' '.join(cmd)}", flush=True)
    t0 = time.time()
    rc = subprocess.run(cmd).returncode
    print(f"--- {label}: rc={rc} ({int(time.time() - t0)}s) ---", flush=True)
    if rc not in ok_rcs:
        return rc
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phenotype")
    ap.add_argument("--skip-regenerate", action="store_true",
                    help="just patch modules; skip Synthea regen + reload")
    ap.add_argument("--path-b-prevalence", type=float, default=0.15)
    args = ap.parse_args()

    t0 = time.time()
    # Path B is opt-in: patch_path_b returns rc=0 if added, rc=2 if shape
    # unrecognised. Both are non-fatal -- log and continue.
    _run("patch_path_b",
         [PY, str(SCRIPTS / "patch_path_b.py"), args.phenotype,
          "--prevalence", str(args.path_b_prevalence)],
         ok_rcs=(0, 2))
    rc = _run("patch_control_module",
              [PY, str(SCRIPTS / "patch_control_module.py"), args.phenotype])
    if rc != 0:
        return rc
    if args.skip_regenerate:
        print(f"\n[{args.phenotype}] modules patched in {int(time.time() - t0)}s "
              f"(--skip-regenerate; not regenerated)")
        return 0
    rc = _run("regenerate_phenotype",
              [PY, str(SCRIPTS / "regenerate_phenotype.py"), args.phenotype])
    print(f"\n[{args.phenotype}] upgrade cycle "
          f"{'PASS' if rc == 0 else 'FAIL'} in {int(time.time() - t0)}s", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
