"""Sanity-check matrix runner: 3 prompts × 3 tiers on a single test case + model.

For one test case ID, runs every (prompt_variant × tier) combination through
the right provider and prints a P/R/F1 grid. Produces a JSON report under
results/sanity-<timestamp>.json.

Per provider, the tiers map to:
  ollama:        T1=`ollama run` subprocess, T2/3=OllamaAgenticProvider
  foundry-local: T1=FoundryLocalProvider, T2/3=FoundryAgenticProvider (NPU)

Usage:
    # Full matrix on the workstation (Ollama):
    python scripts/run_sanity_matrix.py \\
        --test-case phekb-crohns-disease-biologic-without-dx \\
        --provider ollama --model qwen3:8b \\
        --fhir-url https://localhost:8443

    # On the Snapdragon (Foundry Local NPU):
    python scripts/run_sanity_matrix.py \\
        --test-case phekb-asthma \\
        --provider foundry-local --model qwen2.5-7b \\
        --fhir-url https://<cloud-fhir-host>

    # Internal: run a single cell (called by the matrix as a subprocess for hard timeout):
    python scripts/run_sanity_matrix.py \\
        --test-case <id> --provider <p> --model <m> --fhir-url <url> \\
        --single-cell --cell-tier 2 --cell-variant naive --cell-out /tmp/cell.json

Per-cell wall-clock timeout: 5 minutes (configurable with --cell-timeout-sec).
On timeout the cell is recorded as error="timeout" and the matrix moves on.
"""
from __future__ import annotations
import argparse
import json
import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from src.llm import get_provider  # noqa: E402
from src.llm.provider import FHIR_SYSTEM_PROMPT_VERSION  # noqa: E402
from src.llm.agentic_provider import AGENTIC_SYSTEM_PROMPT_VERSION, TOOL_SCHEMA_VERSION  # noqa: E402
from src.fhir.client import FHIRClient  # noqa: E402
from src.evaluation.runner import EvaluationRunner  # noqa: E402
from src.api.models.test_case import TestCase  # noqa: E402

PROMPT_VARIANTS = ["naive", "broad", "expert"]
TIERS = [1, 2, 3]
SUPPORTED_PROVIDERS = ["ollama", "foundry-local", "openai-compat", "azure-openai", "copilot"]

# Reduce the agent's spin ceiling to keep cells bounded
AGENT_MAX_ITERATIONS = 20


def load_test_case(tc_id: str) -> TestCase:
    tc_path = REPO / "test-cases" / "phekb" / f"{tc_id}.json"
    if not tc_path.exists():
        sys.exit(f"Test case not found: {tc_path}")
    with tc_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return TestCase(**data)


def _agentic_fhir_url(fhir_url: str) -> str:
    base = fhir_url.rstrip("/")
    is_root_mounted = base.lower().startswith("https://") or ":8443" in base
    return base if (is_root_mounted or base.endswith("/fhir")) else base + "/fhir"


def make_provider(tier: int, provider: str, model: str, fhir_url: str,
                  base_url: str | None = None, cell_timeout_sec: int = 300,
                  lean_prompt: bool = False, api_key: str | None = None,
                  api_version: str | None = None, system_prefix: str = ""):
    """Construct the LLM provider for a given (tier, provider, model)."""
    if provider == "ollama":
        if tier == 1:
            # Give CommandProvider 30s of slack inside the wall-clock cell timeout
            # so its own TimeoutExpired fires cleanly before the subprocess wrapper kills it.
            inner_timeout = max(30, cell_timeout_sec - 30)
            return get_provider(
                "command",
                command=f"ollama run {model}",
                timeout_sec=inner_timeout,
            )
        return get_provider(
            "ollama-agentic",
            model=model,
            fhir_url=_agentic_fhir_url(fhir_url),
            tier=tier,
            max_iterations=AGENT_MAX_ITERATIONS,
        )
    if provider == "foundry-local":
        if tier == 1:
            return get_provider(
                "foundry-local",
                model=model,
                base_url=base_url,
            )
        return get_provider(
            "foundry-agentic",
            model=model,
            base_url=base_url,
            fhir_url=_agentic_fhir_url(fhir_url),
            tier=tier,
            max_iterations=AGENT_MAX_ITERATIONS,
        )
    if provider == "openai-compat":
        # Any OpenAI-compatible endpoint (AMD GAIA Lemonade, Azure AI Foundry
        # serverless, OpenAI direct, ...). base_url and api_key default via
        # the factory's env-var lookups.
        kw = {}
        if base_url is not None: kw["base_url"] = base_url
        if api_key is not None: kw["api_key"] = api_key
        if tier == 1:
            return get_provider("openai-compat", model=model, **kw)
        return get_provider(
            "openai-compat",
            model=model,
            fhir_url=_agentic_fhir_url(fhir_url),
            tier=tier,
            max_iterations=AGENT_MAX_ITERATIONS,
            lean_prompt=lean_prompt,
            **kw,
        )
    if provider == "copilot":
        # GitHub Copilot SDK. Auth via gh auth login (no --api-key needed).
        # Tier 1 -> closed-book CopilotProvider; Tier 2/3 -> CopilotAgenticProvider
        # with our 10 FHIR/UMLS/VSAC tools.
        if tier == 1:
            # Closed-book CopilotProvider's internal session.idle wait defaults
            # to 180s -- too tight for long expert prompts on big phenotypes.
            # Scale it to just under the cell subprocess timeout so a genuine
            # Copilot error surfaces before the subprocess is hard-killed.
            # system_prefix injects an off-the-shelf skill (e.g. Anthropic
            # fhir-developer) ahead of FHIR_SYSTEM_PROMPT for the baseline run.
            return get_provider("copilot", model=model,
                                timeout_sec=max(180, cell_timeout_sec - 30),
                                system_prefix=system_prefix)
        return get_provider(
            "copilot",
            model=model,
            fhir_url=_agentic_fhir_url(fhir_url),
            tier=tier,
            lean_prompt=lean_prompt,
        )
    if provider == "azure-openai":
        # Azure OpenAI Service deployment. base_url is the resource root,
        # `model` is the Azure deployment name, api_key + api_version required.
        kw = {}
        if base_url is not None: kw["base_url"] = base_url
        if api_key is not None: kw["api_key"] = api_key
        if api_version is not None: kw["api_version"] = api_version
        return get_provider(
            "azure-openai",
            model=model,
            fhir_url=_agentic_fhir_url(fhir_url),
            tier=tier,
            max_iterations=AGENT_MAX_ITERATIONS,
            lean_prompt=lean_prompt,
            **kw,
        )
    raise ValueError(f"Unsupported provider: {provider!r}. Choose from {SUPPORTED_PROVIDERS}")


def make_fhir_client(fhir_url: str) -> FHIRClient:
    is_https = fhir_url.lower().startswith("https://")
    is_root_mounted = is_https or ":8443" in fhir_url
    return FHIRClient(
        base_url=fhir_url,
        fhir_version="" if is_root_mounted else "fhir",
        verify_ssl=not is_https,
    )


def _strip_frontmatter(text: str) -> str:
    """Drop a leading YAML frontmatter block (--- ... ---) if present.

    The frontmatter is skill-discovery metadata, not instructional content, so we
    inject only the skill body for a faithful 'model gets the skill' baseline.
    """
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[text.find("\n", end + 1) + 1:].lstrip("\n")
    return text


def _read_skill(skill_file: str | None) -> str:
    """Read + concatenate one or more (comma-separated) skill files into one block."""
    if not skill_file:
        return ""
    parts = []
    for p in skill_file.split(","):
        p = p.strip()
        if p:
            parts.append(_strip_frontmatter(Path(p).read_text(encoding="utf-8")))
    return "\n\n".join(parts)


def run_one_cell(tc_id: str, tier: int, variant: str, provider_name: str,
                 model: str, fhir_url: str, base_url: str | None = None,
                 cell_timeout_sec: int = 300, lean_prompt: bool = False,
                 api_key: str | None = None, api_version: str | None = None,
                 skill_file: str | None = None) -> dict:
    """Execute a single (tier, variant) cell and return the result dict.

    Called both directly (in --single-cell mode by the subprocess) and from
    the matrix orchestrator below.
    """
    tc = load_test_case(tc_id)
    fhir_client = make_fhir_client(fhir_url)
    cell = {"tier": tier, "prompt_variant": variant}
    t0 = time.time()
    try:
        provider = make_provider(tier, provider_name, model, fhir_url, base_url,
                                 cell_timeout_sec, lean_prompt, api_key, api_version,
                                 system_prefix=_read_skill(skill_file))
        runner = EvaluationRunner(fhir_client, provider)
        cell_prompt_text = tc.get_prompt(variant)
        cell_tc = tc.model_copy(update={
            "prompt": cell_prompt_text,
            "prompts": {"naive": cell_prompt_text},
        })
        result = runner.run_single(cell_tc, provider_name=provider_name, model_name=model)
        exec_r = result.evaluation_results.execution_match
        gen = result.generated_query
        # Capture the actual artefacts so post-hoc analysis doesn't need a re-run.
        # raw_response is capped at 8KB per cell to keep result JSONs reasonable.
        primary_url = gen.parsed_query.url if gen.parsed_query else None
        additional_urls = [q.url for q in gen.additional_queries]
        cell.update({
            "elapsed_sec": round(time.time() - t0, 1),
            "passed": exec_r.passed,
            "precision": exec_r.precision,
            "recall": exec_r.recall,
            "f1": exec_r.f1_score,
            "expected_count": exec_r.expected_count,
            "actual_count": exec_r.actual_count,
            "queries_generated": len(gen.all_queries),
            "primary_query_url": primary_url,
            "additional_query_urls": additional_urls,
            "raw_response": (gen.raw_response or "")[:8000],
            "prompt_text": cell_prompt_text,
        })
        # Attach run metadata from the provider if available
        if result.run_metadata:
            cell["run_metadata"] = result.run_metadata.model_dump(exclude_none=True)
    except Exception as e:
        cell.update({
            "elapsed_sec": round(time.time() - t0, 1),
            "error": str(e)[:200],
        })
    return cell


def run_cell_subprocess(tc_id: str, tier: int, variant: str, provider_name: str,
                        model: str, fhir_url: str, base_url: str | None,
                        timeout_sec: int, lean_prompt: bool = False,
                        api_key: str | None = None,
                        api_version: str | None = None,
                        skill_file: str | None = None) -> dict:
    """Run a single cell in a subprocess with a hard wall-clock timeout."""
    out_dir = REPO / "results"
    out_dir.mkdir(exist_ok=True)
    cell_out = out_dir / f"_cell_tmp_{os.getpid()}_{tier}_{variant}.json"
    cmd = [
        sys.executable, str(Path(__file__).resolve()),
        "--test-case", tc_id,
        "--provider", provider_name,
        "--model", model,
        "--fhir-url", fhir_url,
        "--cell-timeout-sec", str(timeout_sec),
        "--single-cell",
        "--cell-tier", str(tier),
        "--cell-variant", variant,
        "--cell-out", str(cell_out),
    ]
    if base_url:
        cmd += ["--base-url", base_url]
    if lean_prompt:
        cmd += ["--lean-prompt"]
    if api_key:
        cmd += ["--api-key", api_key]
    if api_version:
        cmd += ["--api-version", api_version]
    if skill_file:
        cmd += ["--skill-file", skill_file]
    # Transient failures worth a retry: the Copilot SDK intermittently returns
    # an empty completion or the subprocess crashes before writing. A genuine
    # wall-clock timeout is retried at most once (it is expensive and often a
    # real "model too slow", but server hiccups do happen).
    TRANSIENT = ("empty content", "produced no output", "Connection",
                 "session.idle")
    MAX_ATTEMPTS = 3

    cell = {"tier": tier, "prompt_variant": variant}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        cell = {"tier": tier, "prompt_variant": variant}
        t0 = time.time()
        timed_out = False
        try:
            subprocess.run(cmd, timeout=timeout_sec, check=False,
                           capture_output=True, text=True)
            if cell_out.exists():
                with cell_out.open(encoding="utf-8") as f:
                    cell = json.load(f)
                cell_out.unlink()
            else:
                cell["elapsed_sec"] = round(time.time() - t0, 1)
                cell["error"] = ("subprocess produced no output "
                                 "(likely crashed before writing)")
        except subprocess.TimeoutExpired:
            timed_out = True
            cell["elapsed_sec"] = timeout_sec
            cell["error"] = f"timeout after {timeout_sec}s — cell killed"
            try:
                cell_out.unlink()
            except FileNotFoundError:
                pass

        err = cell.get("error")
        if not err:
            break  # success
        is_transient = any(p in err for p in TRANSIENT)
        # Retry transient errors; retry a timeout only once (attempt 1 -> 2).
        retryable = is_transient or (timed_out and attempt == 1)
        if attempt < MAX_ATTEMPTS and retryable:
            print(f"      retry {attempt}/{MAX_ATTEMPTS - 1} "
                  f"(T{tier} {variant}): {err[:70]}", flush=True)
            cell["retry_attempts"] = attempt
            continue
        if attempt > 1:
            cell["retry_attempts"] = attempt - 1
        break
    return cell


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--test-case", "-t", required=True)
    p.add_argument("--provider", default="ollama", choices=SUPPORTED_PROVIDERS,
                   help="LLM provider (default: ollama)")
    p.add_argument("--model", default="phi4")
    p.add_argument("--fhir-url", default="https://localhost:8443")
    p.add_argument("--base-url", default=None,
                   help="Override LLM endpoint URL (foundry-local: auto-discovered if omitted)")
    p.add_argument("--lean-prompt", action="store_true",
                   help="Use LEAN_AGENTIC_SYSTEM_PROMPT for Tier 2/3 (openai-compat) -- "
                        "recommended for small models that shortcut past tool use")
    p.add_argument("--api-key", default=os.environ.get("AZURE_OPENAI_API_KEY")
                   or os.environ.get("AZURE_API_KEY")
                   or os.environ.get("OPENAI_COMPAT_API_KEY"),
                   help="API key for openai-compat / azure-openai providers "
                        "(falls back to AZURE_OPENAI_API_KEY / AZURE_API_KEY / "
                        "OPENAI_COMPAT_API_KEY env vars)")
    p.add_argument("--api-version", default=None,
                   help="Azure OpenAI api-version (default: 2024-08-01-preview)")
    p.add_argument("--tiers", default="1,2,3")
    p.add_argument("--prompt-variants", default="naive,broad,expert")
    p.add_argument("--cell-timeout-sec", type=int, default=300,
                   help="Per-cell wall-clock timeout (default: 300 = 5 min)")
    p.add_argument("--max-cell-workers", type=int, default=6,
                   help="How many (tier x variant) cells to run concurrently. "
                        "Cells are read-only against the loaded FHIR data, so "
                        "they parallelize safely. NOTE: when run_isolated_suite "
                        "sweeps M model specs at once, total concurrent LLM "
                        "subprocesses is M x this value -- keep it modest "
                        "(default: 6).")
    p.add_argument("--label-suffix", default=None,
                   help="Append this suffix to the recorded model/spec label (e.g. "
                        "'+T3lean') so a variant run is a distinct aggregator column "
                        "without overwriting the base spec. Model sent to provider is unchanged.")
    p.add_argument("--skill-file", default=None,
                   help="Comma-separated file(s) whose text is prepended to the "
                        "closed-book (Tier 1) system prompt -- injects an "
                        "off-the-shelf agent skill (e.g. the vendored Anthropic "
                        "fhir-developer skill). Tags the output spec '+fhirskill'. "
                        "Copilot Tier 1 only; ignored by agentic tiers/providers.")
    # Internal flags for the subprocess single-cell mode
    p.add_argument("--single-cell", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--cell-tier", type=int, help=argparse.SUPPRESS)
    p.add_argument("--cell-variant", help=argparse.SUPPRESS)
    p.add_argument("--cell-out", help=argparse.SUPPRESS)
    args = p.parse_args()

    if args.single_cell:
        cell = run_one_cell(args.test_case, args.cell_tier, args.cell_variant,
                            args.provider, args.model, args.fhir_url,
                            args.base_url, args.cell_timeout_sec, args.lean_prompt,
                            args.api_key, args.api_version, skill_file=args.skill_file)
        with open(args.cell_out, "w", encoding="utf-8") as f:
            json.dump(cell, f, indent=2)
        return 0

    tiers = [int(t) for t in args.tiers.split(",")]
    variants = args.prompt_variants.split(",")

    tc = load_test_case(args.test_case)
    fhir_client = make_fhir_client(args.fhir_url)
    if not fhir_client.health_check():
        sys.exit(f"FHIR server not healthy at {args.fhir_url}")

    print(f"\n=== Sanity matrix: {tc.id} | provider={args.provider} | model={args.model} | server={args.fhir_url} ===")
    print(f"Tiers: {tiers}, Prompt variants: {variants}")
    print(f"Negation test: {tc.metadata.negation}")
    print(f"Expected patient count: {len(tc.test_data.expected_patient_ids)}")
    print(f"Per-cell timeout: {args.cell_timeout_sec}s | Agent max iterations: {AGENT_MAX_ITERATIONS}")
    print()

    # All (tier x variant) cells are read-only against the loaded FHIR data,
    # so they run concurrently. Only the wipe/load (done by the caller, before
    # this script) is exclusive. Each cell is its own subprocess writing a
    # tier+variant-unique temp file, so threads don't collide.
    cell_specs = [(tier, variant) for tier in tiers for variant in variants]
    workers = max(1, min(args.max_cell_workers, len(cell_specs)))
    print(f"Running {len(cell_specs)} cells, {workers} at a time...\n", flush=True)

    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {
            ex.submit(run_cell_subprocess, tc.id, tier, variant, args.provider,
                      args.model, args.fhir_url, args.base_url,
                      args.cell_timeout_sec, args.lean_prompt,
                      args.api_key, args.api_version, args.skill_file): (tier, variant)
            for tier, variant in cell_specs
        }
        for fut in as_completed(futures):
            tier, variant = futures[fut]
            label = f"T{tier} | {variant:6s}"
            try:
                cell = fut.result()
            except Exception as exc:  # noqa: BLE001
                cell = {"tier": tier, "prompt_variant": variant,
                        "error": f"cell thread crashed: {exc}"}
            if "f1" in cell:
                print(f"    {label} -> P={cell['precision']} R={cell['recall']} "
                      f"F1={cell['f1']} (expected={cell['expected_count']}, "
                      f"got={cell['actual_count']}, {cell['elapsed_sec']}s)",
                      flush=True)
            else:
                print(f"    {label} -> ERROR: {cell.get('error','')[:200]}",
                      flush=True)
            results.append(cell)

    # Stable order for the summary + JSON regardless of completion order.
    results.sort(key=lambda c: (c["tier"], variants.index(c["prompt_variant"])
                                if c["prompt_variant"] in variants else 99))

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
    # Tag the run as a distinct spec so the aggregator treats '<model><suffix>'
    # as its own column (the model sent to the provider is unchanged). Explicit
    # --label-suffix wins; otherwise skill runs auto-tag '+fhirskill'.
    suffix = args.label_suffix if args.label_suffix else ("+fhirskill" if args.skill_file else "")
    label_model = args.model + suffix
    safe_model = label_model.replace(":", "-").replace("/", "-")
    out_path = out_dir / f"sanity-matrix-{tc.id}-{args.provider}-{safe_model}-{ts}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({
            "test_case": tc.id,
            "provider": args.provider,
            "model": label_model,
            "fhir_url": args.fhir_url,
            "host": socket.gethostname(),
            "timestamp": ts,
            "cell_timeout_sec": args.cell_timeout_sec,
            "agent_max_iterations": AGENT_MAX_ITERATIONS,
            "prompt_versions": {
                "closed_book": FHIR_SYSTEM_PROMPT_VERSION,
                "agentic": AGENTIC_SYSTEM_PROMPT_VERSION,
                "tool_schema": TOOL_SCHEMA_VERSION,
            },
            "results": results,
        }, f, indent=2)
    print(f"\nFull report: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
