#!/usr/bin/env python3
"""
Batch evaluation runner: Tier 1 (closed book) vs Tier 2 (agentic) head-to-head.

Usage:
    python run_batch_eval.py
    python run_batch_eval.py --tier 2         # Only agentic
    python run_batch_eval.py --tier 1         # Only closed book
    python run_batch_eval.py --model qwen3-coder:30b
"""

import sys, os, json, glob, time, argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from src.llm import get_provider
from src.llm.provider import parse_fhir_query_from_text, parse_fhir_queries_from_text
from src.fhir.client import FHIRClient
from src.evaluation.runner import EvaluationRunner
from src.api.models.test_case import TestCase


def load_all_test_cases(project_root: Path) -> list[tuple[str, TestCase]]:
    """Load all test cases that have multi-path structure (dx, meds, labs, procedures, comprehensive)."""
    patterns = [
        "phekb-*-dx.json", "phekb-*-meds.json", "phekb-*-labs.json",
        "phekb-*-procedures.json", "phekb-*-comprehensive.json",
        "phekb-*-path4-meds-labs.json"
    ]
    tc_dir = project_root / "test-cases" / "phekb"
    tests = []
    seen = set()
    for pat in patterns:
        for f in sorted(tc_dir.glob(pat)):
            with open(f) as fh:
                data = json.load(fh)
            tc_id = data["id"]
            if tc_id in seen:
                continue
            seen.add(tc_id)
            try:
                tc = TestCase(**data)
                tests.append((tc_id, tc))
            except Exception as e:
                print(f"  SKIP {tc_id}: {e}")
    return tests


def run_tier1(tc: TestCase, model: str, prompt_variant: str = "naive") -> dict:
    """Run Tier 1 closed-book evaluation."""
    try:
        llm = get_provider("command", command=f"ollama run {model} --nowordwrap")
        gen = llm.generate_fhir_query(tc.get_prompt(prompt_variant))
        return {
            "raw_response": gen.raw_response[:500],
            "parsed_url": gen.parsed_query.url,
            "success": True,
            "error": None
        }
    except Exception as e:
        return {
            "raw_response": "",
            "parsed_url": "",
            "success": False,
            "error": str(e)[:200]
        }


def run_tier2(tc: TestCase, model: str, fhir_url: str, prompt_variant: str = "naive") -> dict:
    """Run Tier 2 agentic evaluation."""
    try:
        llm = get_provider("ollama-agentic", model=model, fhir_url=fhir_url)
        gen = llm.generate_fhir_query(tc.get_prompt(prompt_variant))
        return {
            "raw_response": gen.raw_response[:500],
            "parsed_url": gen.parsed_query.url,
            "tool_trace": llm.tool_trace,
            "tool_count": len(llm.tool_trace),
            "success": True,
            "error": None
        }
    except Exception as e:
        return {
            "raw_response": "",
            "parsed_url": "",
            "tool_trace": [],
            "tool_count": 0,
            "success": False,
            "error": str(e)[:200]
        }


def evaluate_query(fhir: FHIRClient, tc: TestCase, parsed_url: str) -> dict:
    """Evaluate a generated query against the FHIR server."""
    try:
        # Execute the generated query
        result = fhir.execute_query(parsed_url)
        actual_ids = set()
        if result and "entry" in result:
            for entry in result["entry"]:
                res = entry.get("resource", {})
                rt = res.get("resourceType", "")
                if rt == "Patient":
                    actual_ids.add(res.get("id", ""))
                else:
                    # Extract patient reference
                    subj = res.get("subject", res.get("patient", {}))
                    ref = subj.get("reference", "") if isinstance(subj, dict) else ""
                    if ref.startswith("Patient/"):
                        actual_ids.add(ref.split("/")[1])

        actual_count = result.get("total", len(result.get("entry", []))) if result else 0

        # Compare with expected
        expected_ids = set(tc.test_data.expected_patient_ids) if tc.test_data.expected_patient_ids else set()
        expected_count = tc.test_data.expected_result_count or actual_count

        if expected_ids and actual_ids:
            intersection = expected_ids & actual_ids
            precision = len(intersection) / len(actual_ids) if actual_ids else 0
            recall = len(intersection) / len(expected_ids) if expected_ids else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        else:
            # Fall back to count comparison
            f1 = 1.0 if actual_count > 0 and actual_count == expected_count else (0.5 if actual_count > 0 else 0.0)
            precision = f1
            recall = f1

        return {
            "actual_count": actual_count,
            "expected_count": expected_count,
            "f1": round(f1, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "error": None
        }
    except Exception as e:
        return {
            "actual_count": 0,
            "expected_count": tc.test_data.expected_result_count or 0,
            "f1": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "error": str(e)[:200]
        }


def main():
    parser = argparse.ArgumentParser(description="Batch evaluation: Tier 1 vs Tier 2")
    parser.add_argument("--tier", type=int, choices=[1, 2], default=None, help="Run only this tier (default: both)")
    parser.add_argument("--model", default="qwen2.5:7b", help="Ollama model name")
    parser.add_argument("--fhir-url", default="http://localhost:8080/fhir", help="FHIR server URL")
    parser.add_argument("--limit", type=int, default=None, help="Max test cases to run")
    parser.add_argument("--filter", default=None, help="Filter test case IDs (substring match)")
    parser.add_argument("--prompt-variant", default="naive", choices=["naive", "expert"],
                        help="Which prompt variant to use (default: naive)")
    args = parser.parse_args()

    project_root = Path(__file__).parent
    run_tier1_flag = args.tier in (None, 1)
    run_tier2_flag = args.tier in (None, 2)

    print("=" * 80)
    print(f"FHIR Query Evaluation - Batch Run")
    print(f"Model: {args.model}")
    print(f"Tiers: {'1' if run_tier1_flag else ''}{'+' if run_tier1_flag and run_tier2_flag else ''}{'2' if run_tier2_flag else ''}")
    print(f"Prompt: {args.prompt_variant}")
    print(f"FHIR: {args.fhir_url}")
    print("=" * 80)

    # Load test cases
    tests = load_all_test_cases(project_root)
    if args.filter:
        tests = [(id, tc) for id, tc in tests if args.filter in id]
    if args.limit:
        tests = tests[:args.limit]

    print(f"\nLoaded {len(tests)} test cases")

    # Check FHIR server
    fhir = FHIRClient(base_url="http://localhost:8080")
    if not fhir.health_check():
        print("ERROR: FHIR server not responding!")
        sys.exit(1)

    results = []

    for i, (tc_id, tc) in enumerate(tests):
        complexity = tc.metadata.complexity if hasattr(tc.metadata, 'complexity') else '?'
        multi = tc.metadata.multi_query if hasattr(tc.metadata, 'multi_query') else False

        print(f"\n[{i+1}/{len(tests)}] {tc_id} ({complexity}, multi={multi})")

        row = {
            "test_case": tc_id,
            "complexity": complexity,
            "multi_query": multi,
        }

        # Tier 1: Closed Book
        if run_tier1_flag:
            print(f"  Tier 1 (closed book)...", end="", flush=True)
            t0 = time.time()
            t1_result = run_tier1(tc, args.model, args.prompt_variant)
            t1_time = time.time() - t0

            if t1_result["success"]:
                t1_eval = evaluate_query(fhir, tc, t1_result["parsed_url"])
                row["t1_query"] = t1_result["parsed_url"][:80]
                row["t1_f1"] = t1_eval["f1"]
                row["t1_count"] = t1_eval["actual_count"]
                row["t1_time"] = round(t1_time, 1)
                row["t1_error"] = t1_eval.get("error")
                print(f" F1={t1_eval['f1']:.2f} ({t1_eval['actual_count']} results, {t1_time:.1f}s)")
            else:
                row["t1_query"] = ""
                row["t1_f1"] = 0.0
                row["t1_count"] = 0
                row["t1_time"] = round(t1_time, 1)
                row["t1_error"] = t1_result["error"]
                print(f" ERROR: {t1_result['error'][:60]}")

        # Tier 2: Agentic
        if run_tier2_flag:
            print(f"  Tier 2 (agentic)...", end="", flush=True)
            t0 = time.time()
            t2_result = run_tier2(tc, args.model, args.fhir_url, args.prompt_variant)
            t2_time = time.time() - t0

            if t2_result["success"]:
                t2_eval = evaluate_query(fhir, tc, t2_result["parsed_url"])
                row["t2_query"] = t2_result["parsed_url"][:80]
                row["t2_f1"] = t2_eval["f1"]
                row["t2_count"] = t2_eval["actual_count"]
                row["t2_tools"] = t2_result["tool_count"]
                row["t2_time"] = round(t2_time, 1)
                row["t2_error"] = t2_eval.get("error")
                print(f" F1={t2_eval['f1']:.2f} ({t2_eval['actual_count']} results, {t2_result['tool_count']} tools, {t2_time:.1f}s)")
            else:
                row["t2_query"] = ""
                row["t2_f1"] = 0.0
                row["t2_count"] = 0
                row["t2_tools"] = 0
                row["t2_time"] = round(t2_time, 1)
                row["t2_error"] = t2_result["error"]
                print(f" ERROR: {t2_result['error'][:60]}")

        results.append(row)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # Print table
    print(f"\n{'Test Case':<45} {'Cmplx':>5} {'T1 F1':>6} {'T2 F1':>6} {'T2 Tools':>8} {'Winner':>8}")
    print("-" * 80)

    t1_wins = t2_wins = ties = 0
    t1_scores = []
    t2_scores = []

    for r in results:
        t1_f1 = r.get("t1_f1")
        t2_f1 = r.get("t2_f1")
        tools = r.get("t2_tools", "-")

        t1_str = f"{t1_f1:.2f}" if t1_f1 is not None else "skip"
        t2_str = f"{t2_f1:.2f}" if t2_f1 is not None else "skip"
        tools_str = str(tools) if tools is not None else "-"

        if t1_f1 is not None and t2_f1 is not None:
            t1_scores.append(t1_f1)
            t2_scores.append(t2_f1)
            if t2_f1 > t1_f1:
                winner = "T2 win"
                t2_wins += 1
            elif t1_f1 > t2_f1:
                winner = "T1"
                t1_wins += 1
            else:
                winner = "tie"
                ties += 1
        else:
            winner = "-"

        print(f"{r['test_case']:<45} {r.get('complexity','?'):>5} {t1_str:>6} {t2_str:>6} {tools_str:>8} {winner:>8}")

    if t1_scores:
        avg_t1 = sum(t1_scores) / len(t1_scores)
        avg_t2 = sum(t2_scores) / len(t2_scores)
        print("-" * 80)
        print(f"{'AVERAGE':<45} {'':>5} {avg_t1:>6.2f} {avg_t2:>6.2f} {'':>8}")
        print(f"\nTier 2 wins: {t2_wins}, Tier 1 wins: {t1_wins}, Ties: {ties}")

    # Save results
    results_file = project_root / "results" / f"batch_{args.model.replace(':', '-')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_file.parent.mkdir(exist_ok=True)
    with open(results_file, "w") as f:
        json.dump({
            "model": args.model,
            "prompt_variant": args.prompt_variant,
            "timestamp": datetime.now().isoformat(),
            "tiers": [1, 2] if (run_tier1_flag and run_tier2_flag) else [args.tier],
            "results": results
        }, f, indent=2, default=str)
    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
