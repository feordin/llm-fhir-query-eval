"""Sanity-check matrix runner: 3 prompts × 3 tiers on a single test case + model.

For one test case ID, runs every (prompt_variant × tier) combination through
the right provider and prints a P/R/F1 grid. Produces a JSON report under
results/sanity-<timestamp>.json.

Tier 1 = closed-book (CommandProvider — `ollama run <model>`)
Tier 2 = tools-assisted (OllamaAgenticProvider with tier=2)
Tier 3 = tools + methodology (OllamaAgenticProvider with tier=3)

Usage:
    # Full matrix:
    python scripts/run_sanity_matrix.py \\
        --test-case phekb-crohns-disease-biologic-without-dx \\
        --model phi4 \\
        --fhir-url https://localhost:8443

    # Internal: run a single cell (called by the matrix as a subprocess for hard timeout):
    python scripts/run_sanity_matrix.py \\
        --test-case <id> --model <m> --fhir-url <url> \\
        --single-cell --cell-tier 2 --cell-variant naive --cell-out /tmp/cell.json

Per-cell wall-clock timeout: 5 minutes (configurable with --cell-timeout-sec).
On timeout the cell is recorded as error="timeout" and the matrix moves on.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from src.llm import get_provider  # noqa: E402
from src.fhir.client import FHIRClient  # noqa: E402
from src.evaluation.runner import EvaluationRunner  # noqa: E402
from src.api.models.test_case import TestCase  # noqa: E402

PROMPT_VARIANTS = ["naive", "broad", "expert"]
TIERS = [1, 2, 3]

# Reduce the agent's spin ceiling to keep cells bounded
AGENT_MAX_ITERATIONS = 8


def load_test_case(tc_id: str) -> TestCase:
    tc_path = REPO / "test-cases" / "phekb" / f"{tc_id}.json"
    if not tc_path.exists():
        sys.exit(f"Test case not found: {tc_path}")
    with tc_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return TestCase(**data)


def make_provider(tier: int, model: str, fhir_url: str):
    if tier == 1:
        return get_provider("command", command=f"ollama run {model}")
    base = fhir_url.rstrip("/")
    is_root_mounted = base.lower().startswith("https://") or ":8443" in base
    agentic_fhir = base if (is_root_mounted or base.endswith("/fhir")) else base + "/fhir"
    return get_provider(
        "ollama-agentic",
        model=model,
        fhir_url=agentic_fhir,
        tier=tier,
        max_iterations=AGENT_MAX_ITERATIONS,
    )


def make_fhir_client(fhir_url: str) -> FHIRClient:
    is_https = fhir_url.lower().startswith("https://")
    is_root_mounted = is_https or ":8443" in fhir_url
    return FHIRClient(
        base_url=fhir_url,
        fhir_version="" if is_root_mounted else "fhir",
        verify_ssl=not is_https,
    )


def run_one_cell(tc_id: str, tier: int, variant: str, model: str, fhir_url: str) -> dict:
    """Execute a single (tier, variant) cell and return the result dict.

    Called both directly (in --single-cell mode by the subprocess) and from
    the matrix orchestrator below.
    """
    tc = load_test_case(tc_id)
    fhir_client = make_fhir_client(fhir_url)
    cell = {"tier": tier, "prompt_variant": variant}
    t0 = time.time()
    try:
        provider = make_provider(tier, model, fhir_url)
        runner = EvaluationRunner(fhir_client, provider)
        cell_prompt_text = tc.get_prompt(variant)
        cell_tc = tc.model_copy(update={
            "prompt": cell_prompt_text,
            "prompts": {"naive": cell_prompt_text},
        })
        result = runner.run_single(cell_tc, provider_name="ollama", model_name=model)
        exec_r = result.evaluation_results.execution_match
        cell.update({
            "elapsed_sec": round(time.time() - t0, 1),
            "passed": exec_r.passed,
            "precision": exec_r.precision,
            "recall": exec_r.recall,
            "f1": exec_r.f1_score,
            "expected_count": exec_r.expected_count,
            "actual_count": exec_r.actual_count,
        })
    except Exception as e:
        cell.update({
            "elapsed_sec": round(time.time() - t0, 1),
            "error": str(e)[:200],
        })
    return cell


def run_cell_subprocess(tc_id: str, tier: int, variant: str, model: str,
                        fhir_url: str, timeout_sec: int) -> dict:
    """Run a single cell in a subprocess with a hard wall-clock timeout."""
    out_dir = REPO / "results"
    out_dir.mkdir(exist_ok=True)
    cell_out = out_dir / f"_cell_tmp_{os.getpid()}_{tier}_{variant}.json"
    cmd = [
        sys.executable, str(Path(__file__).resolve()),
        "--test-case", tc_id,
        "--model", model,
        "--fhir-url", fhir_url,
        "--single-cell",
        "--cell-tier", str(tier),
        "--cell-variant", variant,
        "--cell-out", str(cell_out),
    ]
    cell = {"tier": tier, "prompt_variant": variant}
    t0 = time.time()
    try:
        subprocess.run(cmd, timeout=timeout_sec, check=False,
                       capture_output=True, text=True)
        if cell_out.exists():
            with cell_out.open(encoding="utf-8") as f:
                cell = json.load(f)
            cell_out.unlink()
        else:
            cell["elapsed_sec"] = round(time.time() - t0, 1)
            cell["error"] = "subprocess produced no output (likely crashed before writing)"
    except subprocess.TimeoutExpired:
        cell["elapsed_sec"] = timeout_sec
        cell["error"] = f"timeout after {timeout_sec}s — cell killed"
        try:
            cell_out.unlink()
        except FileNotFoundError:
            pass
    return cell


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--test-case", "-t", required=True)
    p.add_argument("--model", default="phi4")
    p.add_argument("--fhir-url", default="https://localhost:8443")
    p.add_argument("--tiers", default="1,2,3")
    p.add_argument("--prompt-variants", default="naive,broad,expert")
    p.add_argument("--cell-timeout-sec", type=int, default=300,
                   help="Per-cell wall-clock timeout (default: 300 = 5 min)")
    # Internal flags for the subprocess single-cell mode
    p.add_argument("--single-cell", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--cell-tier", type=int, help=argparse.SUPPRESS)
    p.add_argument("--cell-variant", help=argparse.SUPPRESS)
    p.add_argument("--cell-out", help=argparse.SUPPRESS)
    args = p.parse_args()

    if args.single_cell:
        cell = run_one_cell(args.test_case, args.cell_tier, args.cell_variant,
                            args.model, args.fhir_url)
        with open(args.cell_out, "w", encoding="utf-8") as f:
            json.dump(cell, f, indent=2)
        return 0

    tiers = [int(t) for t in args.tiers.split(",")]
    variants = args.prompt_variants.split(",")

    tc = load_test_case(args.test_case)
    fhir_client = make_fhir_client(args.fhir_url)
    if not fhir_client.health_check():
        sys.exit(f"FHIR server not healthy at {args.fhir_url}")

    print(f"\n=== Sanity matrix: {tc.id} | model={args.model} | server={args.fhir_url} ===")
    print(f"Tiers: {tiers}, Prompt variants: {variants}")
    print(f"Negation test: {tc.metadata.negation}")
    print(f"Expected patient count: {len(tc.test_data.expected_patient_ids)}")
    print(f"Per-cell timeout: {args.cell_timeout_sec}s | Agent max iterations: {AGENT_MAX_ITERATIONS}")
    print()

    results = []
    for tier in tiers:
        for variant in variants:
            label = f"T{tier} | {variant:6s}"
            print(f"--- {label} starting...", flush=True)
            cell = run_cell_subprocess(tc.id, tier, variant, args.model,
                                       args.fhir_url, args.cell_timeout_sec)
            if "f1" in cell:
                print(f"    {label} -> P={cell['precision']} R={cell['recall']} F1={cell['f1']} "
                      f"(expected={cell['expected_count']}, got={cell['actual_count']}, {cell['elapsed_sec']}s)")
            else:
                print(f"    {label} -> ERROR: {cell.get('error','')[:200]}")
            results.append(cell)

    # Summary
    print("\n=== Matrix summary ===")
    print(f"{'Tier':<6} {'Prompt':<8} {'P':<6} {'R':<6} {'F1':<6} {'Expected':<10} {'Actual':<10} {'Time':<8}")
    for r in results:
        if "f1" in r:
            print(f"T{r['tier']:<5} {r['prompt_variant']:<8} "
                  f"{r['precision']:<6} {r['recall']:<6} {r['f1']:<6} "
                  f"{r['expected_count']:<10} {r['actual_count']:<10} {r['elapsed_sec']}s")
        else:
            print(f"T{r['tier']:<5} {r['prompt_variant']:<8} ERROR: {r.get('error','')[:60]}")

    out_dir = REPO / "results"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    safe_model = args.model.replace(":", "-").replace("/", "-")
    out_path = out_dir / f"sanity-matrix-{tc.id}-{safe_model}-{ts}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({
            "test_case": tc.id,
            "model": args.model,
            "fhir_url": args.fhir_url,
            "cell_timeout_sec": args.cell_timeout_sec,
            "agent_max_iterations": AGENT_MAX_ITERATIONS,
            "results": results,
        }, f, indent=2)
    print(f"\nFull report: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
