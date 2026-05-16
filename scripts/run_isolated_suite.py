"""Per-phenotype isolated evaluation suite.

For each phenotype: wipe the FHIR server, load only that phenotype's minimal
bundle, verify it loaded exactly, then run every test case for that phenotype
through the sanity matrix. Loading one phenotype at a time is what eliminates
the cross-phenotype contamination of the shared $import.

The wipe/load/verify step is its own script (reload_phenotype.py); this driver
just sequences it with run_sanity_matrix.py per phenotype.

Requires UMLS_API_KEY in the environment for Tier 2/3 (source .env first):
    set -a && source .env && set +a
    python scripts/run_isolated_suite.py asthma psoriasis stroke
    python scripts/run_isolated_suite.py --tiers 2 --prompt-variants naive,broad,expert <phenos...>
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from reload_phenotype import _test_cases_for  # noqa: E402  (phenotype->test-case ownership)

PY = sys.executable
RELOAD = str(REPO / "scripts" / "reload_phenotype.py")
MATRIX = str(REPO / "scripts" / "run_sanity_matrix.py")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    import os
    ap.add_argument("phenotypes", nargs="+", help="phenotype names (synthea/output dir names)")
    ap.add_argument("--model", default="qwen3.5:9b")
    ap.add_argument("--provider", default="ollama",
                    choices=["ollama", "foundry-local", "openai-compat", "azure-openai", "copilot"],
                    help="LLM provider (matches run_sanity_matrix's --provider)")
    ap.add_argument("--base-url", default=None,
                    help="Override LLM endpoint URL (e.g. for openai-compat / azure-openai)")
    ap.add_argument("--api-key", default=os.environ.get("AZURE_OPENAI_API_KEY")
                    or os.environ.get("AZURE_API_KEY")
                    or os.environ.get("OPENAI_COMPAT_API_KEY"),
                    help="API key for openai-compat / azure-openai (env fallback)")
    ap.add_argument("--api-version", default=None,
                    help="Azure OpenAI api-version (azure-openai provider only)")
    ap.add_argument("--lean-prompt", action="store_true",
                    help="Use the lean agentic prompt (small openai-compat models)")
    ap.add_argument("--tiers", default="2")
    ap.add_argument("--prompt-variants", default="naive,broad,expert")
    ap.add_argument("--fhir-url", default="https://jaerwinllm.azurewebsites.net")
    ap.add_argument("--cell-timeout-sec", type=int, default=700)
    args = ap.parse_args()

    results: list[tuple[str, str]] = []
    suite_t0 = time.time()

    for pheno in args.phenotypes:
        print(f"\n{'=' * 72}\n=== PHENOTYPE: {pheno}\n{'=' * 72}", flush=True)
        t0 = time.time()

        # 1. wipe + load + verify (fail-fast: don't score against bad data)
        reload = subprocess.run([PY, RELOAD, pheno])
        if reload.returncode != 0:
            print(f"!! {pheno}: reload/verify FAILED -- skipping its test cases", flush=True)
            results.append((pheno, "RELOAD-FAILED"))
            continue

        # 2. run every test case owned by this phenotype through the matrix
        tcs = _test_cases_for(pheno)
        if not tcs:
            print(f"!! {pheno}: no test cases found", flush=True)
            results.append((pheno, "no-test-cases"))
            continue
        for tc in tcs:
            print(f"\n--- matrix: {tc.stem}", flush=True)
            cmd = [
                PY, MATRIX,
                "-t", tc.stem,
                "--model", args.model,
                "--provider", args.provider,
                "--tiers", args.tiers,
                "--prompt-variants", args.prompt_variants,
                "--fhir-url", args.fhir_url,
                "--cell-timeout-sec", str(args.cell_timeout_sec),
            ]
            if args.base_url:
                cmd += ["--base-url", args.base_url]
            if args.lean_prompt:
                cmd += ["--lean-prompt"]
            if args.api_key:
                cmd += ["--api-key", args.api_key]
            if args.api_version:
                cmd += ["--api-version", args.api_version]
            subprocess.run(cmd)
        results.append((pheno, f"ran {len(tcs)} test case(s) in {int(time.time() - t0)}s"))

    print(f"\n{'=' * 72}\n=== SUITE SUMMARY ({int(time.time() - suite_t0)}s total) ===")
    for pheno, status in results:
        print(f"  {pheno:40} {status}")
    failed = [p for p, s in results if s == "RELOAD-FAILED"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
