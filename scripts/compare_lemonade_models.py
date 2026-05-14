"""Ad-hoc comparison: run the same Tier-2 agentic test through several
Lemonade models and report speed + quality side by side.

Usage: python scripts/compare_lemonade_models.py
"""
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from src.llm.agentic_provider import LemonadeAgenticProvider  # noqa: E402

MODELS = [
    "Phi-4-mini-reasoning-Hybrid",
    "Phi-4-mini-instruct-NPU",
    "Qwen3-8B-Hybrid",
]
FHIR_URL = "https://jaerwinllm.azurewebsites.net"
PROMPT = "Find all patients with a diagnosis of asthma."
MAX_ITERATIONS = 10

rows = []
for model in MODELS:
    print(f"\n=== {model} ===", flush=True)
    p = LemonadeAgenticProvider(model=model, fhir_base_url=FHIR_URL,
                                tier=2, max_iterations=MAX_ITERATIONS)
    t0 = time.time()
    parsed, err = None, None
    try:
        r = p.generate_fhir_query(PROMPT)
        parsed = str(r.parsed_query)
    except Exception as e:
        err = str(e)[:160]
    elapsed = time.time() - t0
    md = p.last_run_metadata.model_dump(exclude_none=True) if p.last_run_metadata else {}
    out_tok = md.get("output_tokens") or 0
    tps = round(out_tok / elapsed, 1) if elapsed else 0
    row = {
        "model": model,
        "elapsed_sec": round(elapsed, 1),
        "tool_calls": len(p.tool_trace),
        "iterations": md.get("iterations_used"),
        "in_tok": md.get("input_tokens"),
        "out_tok": out_tok,
        "out_tps": tps,
        "stop_reason": md.get("stop_reason"),
        "result": parsed if parsed else f"ERROR: {err}",
    }
    rows.append(row)
    print(f"  elapsed={row['elapsed_sec']}s tool_calls={row['tool_calls']} "
          f"out_tps={tps} stop={row['stop_reason']}")
    print(f"  result: {row['result'][:200]}")

print("\n\n=== COMPARISON ===")
hdr = f"{'model':<32} {'time':>7} {'tools':>6} {'iters':>6} {'out_tps':>8} {'stop':<16}"
print(hdr)
print("-" * len(hdr))
for r in rows:
    print(f"{r['model']:<32} {r['elapsed_sec']:>6}s {r['tool_calls']:>6} "
          f"{str(r['iterations']):>6} {r['out_tps']:>8} {str(r['stop_reason']):<16}")
print()
for r in rows:
    print(f"{r['model']}:\n  {r['result'][:280]}\n")
