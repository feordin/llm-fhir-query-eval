"""Per-phenotype isolated evaluation suite.

For each phenotype: wipe the FHIR server, load only that phenotype's minimal
bundle, verify it loaded exactly, then run every test case for that phenotype
through the sanity matrix. Loading one phenotype at a time is what eliminates
the cross-phenotype contamination of the shared $import.

The wipe/load/verify step is its own script (reload_phenotype.py); this driver
just sequences it with run_sanity_matrix.py per phenotype.

Multi-model support: pass --providers to sweep multiple LLM specs in parallel
within each test case (phenotype reloads remain sequential).

Requires UMLS_API_KEY in the environment for Tier 2/3 (source .env first):
    set -a && source .env && set +a

    # Single-model (original behaviour):
    python scripts/run_isolated_suite.py asthma psoriasis stroke \\
        --provider copilot --model claude-sonnet-4.6 --tiers 1,2

    # Multi-model (parallel within each test case):
    python scripts/run_isolated_suite.py asthma psoriasis \\
        --providers copilot:claude-sonnet-4.6 copilot:claude-opus-4.7 \\
                    ollama:qwen3.5:9b \\
        --tiers 1,2
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from reload_phenotype import _test_cases_for  # noqa: E402

PY = sys.executable
RELOAD = str(REPO / "scripts" / "reload_phenotype.py")
MATRIX = str(REPO / "scripts" / "run_sanity_matrix.py")
LOGS_DIR = REPO / "results" / "isolated-suite-logs"
DEFAULT_MATRIX_TIMEOUT = 3600  # 1 hour per matrix invocation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Small / context-limited model patterns. When a spec's model name matches
# any of these substrings (case-insensitive), the harness auto-enables
# --lean-prompt for that spec -- the full 6.4 KB agentic prompt + 16 KB T3
# methodology overwhelms <=~14B models. Use --no-auto-lean to disable.
#
# Patterns are SIZE-SPECIFIC so we don't accidentally match a 70B+ variant
# that happens to share a family name (e.g. qwen-2.5-72b is frontier-class).
# Examples that auto-lean:  qwen3.5:9b, qwen-2.5-7b, qwen3-14b, phi-4-mini,
#                           llama-3.1-8b, llama-3.2-3b, gemma2:9b, mistral-7b.
# Examples that do NOT:     qwen-2.5-72b, qwen3-235b, llama-3.3-70b,
#                           gemini-2.5-pro, claude-sonnet-4.6, gpt-5.4.
SMALL_MODEL_PATTERNS = (
    # Qwen <=14B (the 9b ollama tag, 7b/14b families, and qwen3-8/14b)
    "qwen3.5:", "qwen2.5:", "qwen-2.5-7b", "qwen-2.5-3b", "qwen-2.5-1.5b",
    "qwen3-4b", "qwen3-8b", "qwen3-14b",
    # Same families on OpenRouter use dash-form (e.g. qwen/qwen3.5-9b)
    "qwen3.5-9b", "qwen3.5-4b", "qwen3.5-14b",
    "qwen-2.5-14b",
    # Phi (all phi variants are small)
    "phi-4-mini", "phi-4", "phi-3", "phi3", "phi4-mini", "microsoft/phi-",
    # Llama 8B and smaller
    "llama-3.1-8b", "llama-3-8b", "llama-3.2-1b", "llama-3.2-3b",
    "llama3.1:8b", "llama3.2:",
    # Gemma 9B and smaller (large gemmas don't exist on OpenRouter today)
    "gemma2:9b", "gemma2:2b", "gemma-2-9b", "gemma-2-2b",
    "gemma3:", "gemma-3-",
    # Mistral 7B
    "mistral-7b", "mistral:7b",
    # Deepseek R1 distill small
    "deepseek-r1-distill-qwen-7b", "deepseek-r1-distill-qwen-14b",
    "deepseek-r1-distill-llama-8b",
    "deepseek-r1:7b", "deepseek-r1:8b", "deepseek-r1:14b",
)


def _is_small_model(provider: str, model: str) -> bool:
    """True if the model spec matches a known small-context pattern."""
    name = model.lower()
    return any(pat in name for pat in SMALL_MODEL_PATTERNS)


def _parse_specs(specs: list[str]) -> list[tuple[str, str]]:
    """Parse 'provider:model' strings; model may itself contain colons.

    >>> _parse_specs(["copilot:claude-sonnet-4.6", "ollama:qwen3.5:9b"])
    [('copilot', 'claude-sonnet-4.6'), ('ollama', 'qwen3.5:9b')]
    """
    result: list[tuple[str, str]] = []
    for spec in specs:
        if ":" not in spec:
            raise ValueError(f"--providers spec must be 'provider:model', got: {spec!r}")
        provider, model = spec.split(":", 1)
        result.append((provider, model))
    return result


def _safe_name(provider: str, model: str) -> str:
    """Filesystem-safe label for a provider+model pair."""
    return f"{provider}:{model}".replace(":", "-").replace("/", "-")


def _run_one_matrix(
    spec: tuple[str, str],
    tc: Path,
    args: argparse.Namespace,
    logs_dir: Path,
    matrix_timeout: int,
) -> tuple[str, int, float]:
    """Run run_sanity_matrix.py for one (spec, test-case) pair.

    Streams subprocess output to a per-spec log file only (not stdout) to
    avoid interleaved chaos from parallel threads. Emits brief per-spec
    banners to stdout.

    Returns (spec_label, returncode, elapsed_seconds).
    """
    provider, model = spec
    label = f"{provider}:{model}"
    safe = _safe_name(provider, model)

    log_path = logs_dir / f"{tc.stem}__{safe}.log"
    logs_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        PY, MATRIX,
        "-t", tc.stem,
        "--provider", provider,
        "--model", model,
        "--tiers", args.tiers,
        "--prompt-variants", args.prompt_variants,
        "--fhir-url", args.fhir_url,
        "--cell-timeout-sec", str(args.cell_timeout_sec),
        "--max-cell-workers", str(args.max_cell_workers),
    ]
    if args.base_url:
        cmd += ["--base-url", args.base_url]
    if args.api_key:
        cmd += ["--api-key", args.api_key]
    if args.api_version:
        cmd += ["--api-version", args.api_version]
    if args.skill_file:
        cmd += ["--skill-file", args.skill_file]
    if args.label_suffix:
        cmd += ["--label-suffix", args.label_suffix]
    # Per-spec lean prompt: forced via --lean-prompt for all specs, OR
    # auto-enabled for specs matching SMALL_MODEL_PATTERNS unless the operator
    # passed --no-auto-lean.
    use_lean = args.lean_prompt or (
        not args.no_auto_lean and _is_small_model(provider, model)
    )
    if use_lean:
        cmd += ["--lean-prompt"]

    lean_tag = "  [lean]" if use_lean else ""
    print(f"    [START] {label}{lean_tag}  tc={tc.stem}  log={log_path.name}",
          flush=True)
    t0 = time.time()
    rc: int

    with log_path.open("w", encoding="utf-8") as logf:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                logf.write(line)
            rc = proc.wait(timeout=matrix_timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            msg = f"\n!! [{label}] TIMEOUT after {matrix_timeout}s -- killed\n"
            logf.write(msg)
            rc = 124

    elapsed = time.time() - t0
    status = "TIMEOUT" if rc == 124 else ("OK" if rc == 0 else f"rc={rc}")
    print(f"    [DONE ] {label}  tc={tc.stem}  {status}  {elapsed:.0f}s", flush=True)
    return label, rc, elapsed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phenotypes", nargs="+",
                    help="phenotype names (synthea/output dir names)")

    # --- provider/model: single-spec (legacy) OR multi-spec ---
    spec_grp = ap.add_mutually_exclusive_group()
    spec_grp.add_argument(
        "--providers", nargs="+", metavar="PROVIDER:MODEL",
        help="One or more 'provider:model' specs to run in parallel per test case "
             "(model names may contain colons, e.g. ollama:qwen3.5:9b). "
             "Overrides --provider / --model when given.",
    )
    spec_grp.add_argument(
        "--provider", default="ollama",
        choices=["ollama", "foundry-local", "openai-compat", "azure-openai", "copilot"],
        help="LLM provider for single-model mode (default: ollama).",
    )
    ap.add_argument("--model", default="qwen3.5:9b",
                    help="Model name for single-model mode (default: qwen3.5:9b).")

    # --- shared / global flags ---
    ap.add_argument("--base-url", default=None,
                    help="Override LLM endpoint URL (e.g. for openai-compat / azure-openai).")
    ap.add_argument("--api-key",
                    default=(os.environ.get("AZURE_OPENAI_API_KEY")
                             or os.environ.get("AZURE_API_KEY")
                             or os.environ.get("OPENAI_COMPAT_API_KEY")),
                    help="API key for openai-compat / azure-openai (env fallback).")
    ap.add_argument("--api-version", default=None,
                    help="Azure OpenAI api-version (azure-openai provider only).")
    ap.add_argument("--lean-prompt", action="store_true",
                    help="Force the lean agentic prompt for ALL specs. Useful "
                         "for measuring lean-prompt effect on frontier models. "
                         "By default, lean is auto-enabled only for small "
                         "models (qwen, phi, llama, gemma, mistral-7b...).")
    ap.add_argument("--no-auto-lean", action="store_true",
                    help="Disable the auto-enable of --lean-prompt for small "
                         "models. Only --lean-prompt (if passed) is honored.")
    ap.add_argument("--label-suffix", default=None,
                    help="Passed through to run_sanity_matrix: tag the spec label "
                         "(e.g. '+T3lean') so a variant run is a distinct column.")
    ap.add_argument("--skill-file", default=None,
                    help="Passed through to run_sanity_matrix: comma-separated "
                         "file(s) prepended to the closed-book (Tier 1) system "
                         "prompt for the off-the-shelf skill baseline. Tags the "
                         "spec '+fhirskill'. Use with --tiers 1.")
    ap.add_argument("--tiers", default="2")
    ap.add_argument("--prompt-variants", default="naive,broad,expert")
    ap.add_argument("--fhir-url", default="https://jaerwinllm.azurewebsites.net")
    ap.add_argument("--cell-timeout-sec", type=int, default=700)
    ap.add_argument("--max-cell-workers", type=int, default=6,
                    help="Concurrent (tier x variant) cells per matrix. Total "
                         "concurrent LLM subprocesses is (num provider specs) x "
                         "this -- keep modest on a single host (default: 6).")
    ap.add_argument("--matrix-timeout-sec", type=int, default=DEFAULT_MATRIX_TIMEOUT,
                    help="Wall-clock timeout per matrix invocation in seconds (default: 3600).")
    args = ap.parse_args()

    # Resolve specs
    if args.providers:
        try:
            specs = _parse_specs(args.providers)
        except ValueError as exc:
            ap.error(str(exc))
            return 1  # unreachable; keeps mypy happy
    else:
        specs = [(args.provider, args.model)]

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # phenotype -> list of (label, rc, elapsed) per test case
    suite_results: list[tuple[str, str, list[tuple[str, int, float]]]] = []
    suite_t0 = time.time()

    for pheno in args.phenotypes:
        print(f"\n{'=' * 72}\n=== PHENOTYPE: {pheno}\n{'=' * 72}", flush=True)
        pheno_t0 = time.time()

        # 1. wipe + load + verify (sequential; fail-fast). Pass --fhir-url
        # through via env so sharded runs hit their assigned server.
        reload_env = os.environ.copy()
        reload_env["FHIR_RELOAD_URL"] = args.fhir_url
        reload = subprocess.run([PY, RELOAD, pheno], env=reload_env)
        if reload.returncode != 0:
            print(f"!! {pheno}: reload/verify FAILED -- skipping test cases", flush=True)
            suite_results.append((pheno, "RELOAD-FAILED", []))
            continue

        # 2. iterate test cases sequentially; parallelize specs within each
        tcs = _test_cases_for(pheno)
        if not tcs:
            print(f"!! {pheno}: no test cases found", flush=True)
            suite_results.append((pheno, "no-test-cases", []))
            continue

        pheno_spec_results: list[tuple[str, int, float]] = []
        for tc in tcs:
            print(f"\n--- matrix: {tc.stem}  [{len(specs)} spec(s)]", flush=True)
            if len(specs) == 1:
                # Fast path: no extra thread overhead
                label, rc, elapsed = _run_one_matrix(
                    specs[0], tc, args, LOGS_DIR, args.matrix_timeout_sec)
                pheno_spec_results.append((label, rc, elapsed))
            else:
                with ThreadPoolExecutor(max_workers=len(specs)) as ex:
                    futures = {
                        ex.submit(_run_one_matrix, spec, tc, args,
                                  LOGS_DIR, args.matrix_timeout_sec): spec
                        for spec in specs
                    }
                    for fut in as_completed(futures):
                        try:
                            label, rc, elapsed = fut.result()
                        except Exception as exc:  # noqa: BLE001
                            spec = futures[fut]
                            label = f"{spec[0]}:{spec[1]}"
                            print(f"    [ERROR] {label}  tc={tc.stem}  {exc}", flush=True)
                            label, rc, elapsed = label, -1, 0.0
                        pheno_spec_results.append((label, rc, elapsed))

        pheno_elapsed = int(time.time() - pheno_t0)
        suite_results.append((pheno, f"{len(tcs)} tc(s) in {pheno_elapsed}s",
                               pheno_spec_results))

    # --- Suite summary ---
    total_elapsed = int(time.time() - suite_t0)
    print(f"\n{'=' * 72}")
    print(f"=== SUITE SUMMARY ({total_elapsed}s total) ===")
    print(f"{'=' * 72}")
    for pheno, status, spec_results in suite_results:
        print(f"\n  {pheno} — {status}")
        if spec_results:
            # Aggregate by label: show best rc across all test cases for a terse view
            from collections import defaultdict
            agg: dict[str, list[int]] = defaultdict(list)
            for label, rc, _ in spec_results:
                agg[label].append(rc)
            for label, rcs in sorted(agg.items()):
                worst = max(rcs)
                tag = "PASS" if worst == 0 else ("TIMEOUT" if worst == 124 else f"FAIL(rc={worst})")
                print(f"    {label:50} {tag}")

    reload_failures = [p for p, s, _ in suite_results if s == "RELOAD-FAILED"]
    return 1 if reload_failures else 0


if __name__ == "__main__":
    sys.exit(main())
