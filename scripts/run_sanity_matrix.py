"""Sanity-check matrix runner: 3 prompts × 3 tiers on a single test case + model.

For one test case ID, runs every (prompt_variant × tier) combination through
the right provider and prints a P/R/F1 grid. Produces a JSON report under
results/sanity-<timestamp>.json.

Tier 1 = closed-book (CommandProvider — `ollama run <model>`)
Tier 2 = tools-assisted (OllamaAgenticProvider with tier=2)
Tier 3 = tools + methodology (OllamaAgenticProvider with tier=3)

Usage:
    python scripts/run_sanity_matrix.py \\
        --test-case phekb-crohns-disease-biologic-without-dx \\
        --model phi4 \\
        --fhir-url https://localhost:8443
"""
from __future__ import annotations
import argparse
import json
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


def load_test_case(tc_id: str) -> TestCase:
    tc_path = REPO / "test-cases" / "phekb" / f"{tc_id}.json"
    if not tc_path.exists():
        sys.exit(f"Test case not found: {tc_path}")
    with tc_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return TestCase(**data)


def make_provider(tier: int, model: str, fhir_url: str):
    """Build the right provider for the given tier."""
    if tier == 1:
        # Closed book: CommandProvider running `ollama run <model>`
        return get_provider(
            "command",
            command=f"ollama run {model}",
        )
    # Tier 2 + 3 use the agentic provider; tier kwarg controls methodology loading
    base = fhir_url.rstrip("/")
    is_root_mounted = base.lower().startswith("https://") or ":8443" in base
    if is_root_mounted or base.endswith("/fhir"):
        agentic_fhir = base
    else:
        agentic_fhir = base + "/fhir"
    return get_provider(
        "ollama-agentic",
        model=model,
        fhir_url=agentic_fhir,
        tier=tier,
        max_iterations=12,
    )


def make_fhir_client(fhir_url: str) -> FHIRClient:
    is_https = fhir_url.lower().startswith("https://")
    is_root_mounted = is_https or ":8443" in fhir_url
    return FHIRClient(
        base_url=fhir_url,
        fhir_version="" if is_root_mounted else "fhir",
        verify_ssl=not is_https,
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--test-case", "-t", required=True)
    p.add_argument("--model", default="phi4")
    p.add_argument("--fhir-url", default="https://localhost:8443")
    p.add_argument("--tiers", default="1,2,3", help="Comma-separated tiers to run (default: 1,2,3)")
    p.add_argument("--prompt-variants", default="naive,broad,expert",
                   help="Comma-separated prompt variants (default: naive,broad,expert)")
    args = p.parse_args()

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
    print()

    results = []
    for tier in tiers:
        for variant in variants:
            cell = {"tier": tier, "prompt_variant": variant}
            label = f"T{tier} | {variant:6s}"
            print(f"--- {label} starting...", flush=True)
            t0 = time.time()
            try:
                provider = make_provider(tier, args.model, args.fhir_url)
                runner = EvaluationRunner(fhir_client, provider)
                # Override the prompt variant the runner uses
                # The runner calls test_case.get_prompt() — which defaults to "naive".
                # We monkey-patch by overriding get_prompt on this instance.
                original_get_prompt = tc.get_prompt
                tc.get_prompt = lambda v=variant: original_get_prompt(v)  # type: ignore
                try:
                    result = runner.evaluate(tc, provider_name="ollama", model_name=args.model)
                finally:
                    tc.get_prompt = original_get_prompt  # type: ignore

                exec_r = result.execution_result
                cell.update({
                    "elapsed_sec": round(time.time() - t0, 1),
                    "passed": exec_r.passed,
                    "precision": exec_r.precision,
                    "recall": exec_r.recall,
                    "f1": exec_r.f1_score,
                    "expected_count": exec_r.expected_count,
                    "actual_count": exec_r.actual_count,
                })
                print(f"    {label} -> P={exec_r.precision} R={exec_r.recall} F1={exec_r.f1_score} "
                      f"(expected={exec_r.expected_count}, got={exec_r.actual_count}, {cell['elapsed_sec']}s)")
            except Exception as e:
                cell.update({
                    "elapsed_sec": round(time.time() - t0, 1),
                    "error": str(e)[:200],
                })
                print(f"    {label} -> ERROR: {str(e)[:200]}")
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

    # Save full report
    out_dir = REPO / "results"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"sanity-matrix-{tc.id}-{args.model}-{ts}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({
            "test_case": tc.id,
            "model": args.model,
            "fhir_url": args.fhir_url,
            "results": results,
        }, f, indent=2)
    print(f"\nFull report: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
