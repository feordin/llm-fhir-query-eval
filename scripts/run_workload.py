"""Long-running multi-phenotype evaluation runner.

Reads `docs/eval-workloads.json` to determine which phenotypes belong to a
machine, then iterates through them running the full 3×3 matrix per test case.
Writes incremental results so a crash or interruption doesn't lose work, and
skips phenotypes that already have a result file (resume mode by default).

Designed for hours of continuous unattended operation — catches all per-test
exceptions, logs them, keeps going.

Usage:
    # On the fast workstation:
    python scripts/run_workload.py --machine main_pc --model qwen3:8b \\
        --fhir-url https://localhost:8443

    # On the Snapdragon:
    python scripts/run_workload.py --machine snapdragon --model qwen3:8b \\
        --fhir-url https://<cloud-fhir-host>

    # Force re-run all (ignore existing results):
    python scripts/run_workload.py --machine main_pc --model qwen3:8b --force

    # Single phenotype (ad-hoc / debugging):
    python scripts/run_workload.py --machine main_pc --model qwen3:8b \\
        --only phekb-crohns-disease

    # Adjust per-cell timeout (default 300s):
    python scripts/run_workload.py --machine main_pc --model qwen3:8b \\
        --cell-timeout-sec 240
"""
from __future__ import annotations
import argparse
import json
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORKLOAD_PATH = REPO / "docs" / "eval-workloads.json"
RESULTS_DIR = REPO / "results"
PROGRESS_LOG = RESULTS_DIR / "workload-progress.jsonl"
ERROR_LOG = RESULTS_DIR / "workload-errors.log"

MATRIX_SCRIPT = REPO / "scripts" / "run_sanity_matrix.py"


def load_workload(machine: str) -> list[str]:
    if not WORKLOAD_PATH.exists():
        sys.exit(f"Workload file not found: {WORKLOAD_PATH}\nRun: python scripts/build_eval_workload.py")
    with WORKLOAD_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    if machine not in data["workloads"]:
        sys.exit(f"Unknown machine '{machine}'. Valid: {list(data['workloads'].keys())}")
    return data["workloads"][machine]["phenotypes"]


def has_existing_result(phenotype: str, model: str) -> Path | None:
    """Look for an existing matrix result for this phenotype + model.

    Pattern: results/sanity-matrix-<phen-test-case-id>-<model>-<ts>.json
    Since each phenotype has multiple test cases (-dx, -meds, etc.), we check
    if at least one test case has a result. The runner produces one matrix
    file per test case ID it processes.
    """
    if not RESULTS_DIR.exists():
        return None
    pattern = f"sanity-matrix-phekb-{phenotype}-*-{model.replace(':', '-')}-*.json"
    matches = list(RESULTS_DIR.glob(pattern))
    return matches[0] if matches else None


def get_test_cases_for_phenotype(phenotype: str) -> list[str]:
    """Return all test case IDs for a phenotype (matching Synthea slug)."""
    tc_dir = REPO / "test-cases" / "phekb"
    test_cases = []
    for f in sorted(tc_dir.glob(f"phekb-{phenotype}-*.json")):
        test_cases.append(f.stem)
    # Also catch the bare `phekb-<phenotype>.json` if it exists
    bare = tc_dir / f"phekb-{phenotype}.json"
    if bare.exists():
        test_cases.append(bare.stem)
    return test_cases


def log_progress(event: dict) -> None:
    """Append a line to the progress log."""
    RESULTS_DIR.mkdir(exist_ok=True)
    event["ts"] = datetime.utcnow().isoformat() + "Z"
    with PROGRESS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def log_error(test_case: str, err: str) -> None:
    """Append a structured error line."""
    RESULTS_DIR.mkdir(exist_ok=True)
    with ERROR_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.utcnow().isoformat()}Z] {test_case}: {err}\n")


def run_test_case_matrix(test_case_id: str, model: str, fhir_url: str,
                         cell_timeout_sec: int) -> dict:
    """Invoke the sanity matrix script as a subprocess; returns summary dict."""
    cmd = [
        sys.executable, str(MATRIX_SCRIPT),
        "--test-case", test_case_id,
        "--model", model,
        "--fhir-url", fhir_url,
        "--cell-timeout-sec", str(cell_timeout_sec),
    ]
    t0 = time.time()
    # Per-test-case overall timeout: 9 cells × cell_timeout + 30s slack
    overall = 9 * cell_timeout_sec + 30
    try:
        completed = subprocess.run(cmd, timeout=overall, capture_output=True, text=True)
        return {
            "ok": completed.returncode == 0,
            "elapsed_sec": round(time.time() - t0, 1),
            "returncode": completed.returncode,
            "stderr_tail": completed.stderr[-2000:] if completed.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "elapsed_sec": overall,
            "error": f"matrix timeout after {overall}s",
        }
    except Exception as e:
        return {
            "ok": False,
            "elapsed_sec": round(time.time() - t0, 1),
            "error": str(e)[:300],
        }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--machine", required=True, choices=["main_pc", "snapdragon"])
    p.add_argument("--model", default="qwen3:8b")
    p.add_argument("--fhir-url", default="https://localhost:8443")
    p.add_argument("--cell-timeout-sec", type=int, default=300)
    p.add_argument("--force", action="store_true",
                   help="Re-run even if a result file already exists")
    p.add_argument("--only", default=None,
                   help="Run only this phenotype (and its test cases)")
    p.add_argument("--max-phenotypes", type=int, default=None,
                   help="Stop after N phenotypes (debugging)")
    args = p.parse_args()

    phenotypes = load_workload(args.machine)
    if args.only:
        phenotypes = [args.only] if args.only in phenotypes else [args.only]
        if not phenotypes:
            sys.exit(f"Phenotype {args.only} not in workload for {args.machine}")

    print(f"=== run_workload | machine={args.machine} | host={socket.gethostname()} | model={args.model} ===")
    print(f"FHIR: {args.fhir_url}")
    print(f"Phenotypes assigned: {len(phenotypes)}")
    print(f"Per-cell timeout: {args.cell_timeout_sec}s | Resume mode: {'OFF (--force)' if args.force else 'ON'}")
    print()

    log_progress({
        "event": "session_start",
        "machine": args.machine,
        "host": socket.gethostname(),
        "model": args.model,
        "fhir_url": args.fhir_url,
        "phenotype_count": len(phenotypes),
    })

    overall_t0 = time.time()
    counts = {"phenotypes_done": 0, "phenotypes_skipped": 0,
              "test_cases_run": 0, "test_cases_failed": 0}

    for i, phen in enumerate(phenotypes, 1):
        if args.max_phenotypes and counts["phenotypes_done"] >= args.max_phenotypes:
            break
        print(f"\n[{i}/{len(phenotypes)}] {phen}")
        test_cases = get_test_cases_for_phenotype(phen)
        if not test_cases:
            print(f"  no test cases found, skipping")
            log_progress({"event": "phenotype_no_tests", "phenotype": phen})
            continue
        print(f"  {len(test_cases)} test case(s)")

        phenotype_t0 = time.time()
        for tc_id in test_cases:
            existing = has_existing_result(tc_id, args.model)
            if existing and not args.force:
                print(f"  skip (existing result): {tc_id}")
                counts["phenotypes_skipped"] += 1
                continue
            print(f"  running matrix: {tc_id}")
            try:
                summary = run_test_case_matrix(
                    tc_id, args.model, args.fhir_url, args.cell_timeout_sec)
                if summary.get("ok"):
                    counts["test_cases_run"] += 1
                    print(f"    OK ({summary['elapsed_sec']}s)")
                else:
                    counts["test_cases_failed"] += 1
                    err = summary.get("error", f"returncode {summary.get('returncode')}")
                    print(f"    FAILED: {err}")
                    log_error(tc_id, err)
                log_progress({
                    "event": "test_case_done",
                    "phenotype": phen,
                    "test_case": tc_id,
                    "summary": summary,
                })
            except KeyboardInterrupt:
                print("\n[interrupted by user]")
                log_progress({"event": "interrupted", "phenotype": phen, "test_case": tc_id})
                return 130
            except Exception as e:
                counts["test_cases_failed"] += 1
                err = f"unexpected: {e}"
                print(f"    EXCEPTION: {err}")
                log_error(tc_id, err)
                log_progress({"event": "test_case_exception", "test_case": tc_id, "error": err})

        counts["phenotypes_done"] += 1
        phen_elapsed = round(time.time() - phenotype_t0, 1)
        log_progress({
            "event": "phenotype_done",
            "phenotype": phen,
            "elapsed_sec": phen_elapsed,
            "running_counts": dict(counts),
        })

    overall_elapsed = round(time.time() - overall_t0, 1)
    print(f"\n=== Workload complete in {overall_elapsed}s ({overall_elapsed / 3600:.1f}h) ===")
    print(f"Phenotypes processed: {counts['phenotypes_done']}/{len(phenotypes)}")
    print(f"Test cases run: {counts['test_cases_run']}")
    print(f"Test cases skipped (existing result): {counts['phenotypes_skipped']}")
    print(f"Test cases failed: {counts['test_cases_failed']}")
    log_progress({"event": "session_end", "counts": counts, "elapsed_sec": overall_elapsed})
    return 0


if __name__ == "__main__":
    sys.exit(main())
