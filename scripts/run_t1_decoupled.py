"""Decoupled Tier-1 (closed-book) backfill: generate first, score later.

WHY THIS EXISTS
---------------
Tier 1 is closed-book: the LLM produces a query from the prompt ALONE and never
touches the FHIR server. The server is only needed at *scoring* time -- to run
the generated query (and the gold query) against an isolated, single-phenotype
data load and compare patient sets.

The in-suite runner (`run_isolated_suite.py`) interleaves the per-phenotype
wipe/load/verify with the LLM cell subprocesses. Under sustained load the reload
step's bundle-file probes intermittently starve while dozens of Copilot CLI
(node.exe) subprocesses run -- the "no minimal bundles found" blocker. Because
T1 generation needs no server, we can split the two phases so they never run
concurrently:

  generate -- all phenotypes x variants x specs, fully parallel, NO reload, NO
              FHIR server. Persists one record per (test-case, variant, spec).
  score    -- one phenotype at a time: reload (exclusive -- nothing else is
              running, so the probes never starve), then replay each stored
              generation through the SAME EvaluationRunner used by the live
              harness, and write a canonical sanity-matrix-*.json the aggregator
              already understands.

Scoring fidelity: a tiny ReplayProvider returns the stored raw response, so
EvaluationRunner.run_single() runs byte-identically to a live run (multi-query
union, negation difference, single-query -- all preserved).

USAGE
-----
    # Phase 1 -- generate (no server). Plain + the Anthropic fhir skill:
    python scripts/run_t1_decoupled.py generate \
        --phenotypes-file scripts/.opus_backfill_phenos.txt \
        --model claude-opus-4.7 \
        --skill-file vendor/anthropic-fhir-skill/SKILL.md,vendor/anthropic-fhir-skill/references/resource-examples.md \
        --max-workers 8

    # Phase 2 -- score (sequential reload, no LLM). Run after generate finishes:
    python scripts/run_t1_decoupled.py score \
        --phenotypes-file scripts/.opus_backfill_phenos.txt \
        --model claude-opus-4.7 --with-skill \
        --fhir-url https://jaerwinllm.azurewebsites.net

Both phases are resumable: generate skips records that already exist; score skips
(tc, spec) pairs whose sanity-matrix file already exists for this run label.
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
sys.path.insert(0, str(REPO / "scripts"))

from src.llm import build_generated_query, LLMProvider  # noqa: E402
from src.llm.copilot_provider import CopilotProvider  # noqa: E402
from src.llm.provider import FHIR_SYSTEM_PROMPT_VERSION  # noqa: E402
from src.evaluation.runner import EvaluationRunner  # noqa: E402
from src.api.models.test_case import TestCase  # noqa: E402
from src.api.models.evaluation import GeneratedQuery  # noqa: E402

# Reuse the EXACT helpers the live harness uses so behaviour can't drift.
from run_sanity_matrix import make_fhir_client, _read_skill  # noqa: E402
from reload_phenotype import _test_cases_for  # noqa: E402

PY = sys.executable
RELOAD = str(REPO / "scripts" / "reload_phenotype.py")
RESULTS = REPO / "results"
STAGE = RESULTS / "t1-decoupled-stage"
DEFAULT_VARIANTS = ["naive", "broad", "expert"]
GEN_RETRIES = 3
GEN_TRANSIENT = ("empty content", "Connection", "session.idle", "no output",
                 "timeout")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _safe_model(label_model: str) -> str:
    return label_model.replace(":", "-").replace("/", "-")


def _label_model(model: str, with_skill: bool) -> str:
    """Spec label as the aggregator sees it: skill runs are tagged '+fhirskill'."""
    return f"{model}+fhirskill" if with_skill else model


def _read_phenos(args: argparse.Namespace) -> list[str]:
    if args.phenotypes:
        return list(args.phenotypes)
    if args.phenotypes_file:
        text = Path(args.phenotypes_file).read_text(encoding="utf-8")
        return [ln.strip() for ln in text.splitlines() if ln.strip()]
    # Default: every phenotype with a synthea/output dir.
    return sorted(p.name for p in (REPO / "synthea" / "output").iterdir() if p.is_dir())


def _stage_dir(label_model: str) -> Path:
    return STAGE / _safe_model(label_model)


def _record_path(label_model: str, tc_id: str, variant: str) -> Path:
    return _stage_dir(label_model) / f"{tc_id}__{variant}.json"


def _load_tc(tc_id: str) -> TestCase:
    with (REPO / "test-cases" / "phekb" / f"{tc_id}.json").open(encoding="utf-8") as f:
        return TestCase(**json.load(f))


# ---------------------------------------------------------------------------
# Phase 1 -- generate (no FHIR server)
# ---------------------------------------------------------------------------

def _generate_one(model: str, system_prefix: str, label_model: str,
                  tc_id: str, variant: str, prompt_text: str,
                  timeout_sec: int) -> dict:
    """Closed-book generation for one (tc, variant). Returns a record dict."""
    rec = {"tc_id": tc_id, "variant": variant, "provider": "copilot",
           "model": model, "label_model": label_model,
           "prompt_text": prompt_text}
    last_err = ""
    for attempt in range(1, GEN_RETRIES + 1):
        t0 = time.time()
        try:
            provider = CopilotProvider(model=model, timeout_sec=timeout_sec,
                                       system_prefix=system_prefix)
            gen = provider.generate_fhir_query(prompt_text)
            rec.update({
                "raw_response": (gen.raw_response or "")[:8000],
                "primary_query_url": gen.parsed_query.url if gen.parsed_query else None,
                "additional_query_urls": [q.url for q in gen.additional_queries],
                "queries_generated": len(gen.all_queries),
                "gen_elapsed_sec": round(time.time() - t0, 1),
                "error": None,
            })
            return rec
        except Exception as e:  # noqa: BLE001
            last_err = str(e)[:200]
            if attempt < GEN_RETRIES and any(p in last_err for p in GEN_TRANSIENT):
                time.sleep(2)
                continue
            break
    rec.update({"raw_response": "", "primary_query_url": None,
                "additional_query_urls": [], "queries_generated": 0,
                "gen_elapsed_sec": round(time.time() - t0, 1),
                "error": last_err or "generation failed"})
    return rec


def cmd_generate(args: argparse.Namespace) -> int:
    phenos = _read_phenos(args)
    variants = args.prompt_variants.split(",")
    system_prefix = _read_skill(args.skill_file) if args.skill_file else ""
    with_skill = bool(args.skill_file)
    label_model = _label_model(args.model, with_skill)
    out_dir = _stage_dir(label_model)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build the job list: (tc_id, variant, prompt_text). Skip existing records.
    jobs: list[tuple[str, str, str]] = []
    skipped = 0
    for pheno in phenos:
        for tc_path in _test_cases_for(pheno):
            tc = _load_tc(tc_path.stem)
            for variant in variants:
                rp = _record_path(label_model, tc.id, variant)
                if rp.exists() and not args.overwrite:
                    # Keep an existing record only if it succeeded; retry errors.
                    try:
                        if json.loads(rp.read_text(encoding="utf-8")).get("error") is None:
                            skipped += 1
                            continue
                    except Exception:  # noqa: BLE001
                        pass
                jobs.append((tc.id, variant, tc.get_prompt(variant)))

    print(f"GENERATE [{label_model}]: {len(phenos)} phenotypes -> {len(jobs)} cells "
          f"to generate ({skipped} already done), {args.max_workers} workers",
          flush=True)
    if not jobs:
        print("nothing to do.", flush=True)
        return 0

    done = 0
    fails = 0
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=args.max_workers) as ex:
        futs = {
            ex.submit(_generate_one, args.model, system_prefix, label_model,
                      tc_id, variant, prompt_text, args.timeout_sec): (tc_id, variant)
            for tc_id, variant, prompt_text in jobs
        }
        for fut in as_completed(futs):
            tc_id, variant = futs[fut]
            try:
                rec = fut.result()
            except Exception as e:  # noqa: BLE001
                rec = {"tc_id": tc_id, "variant": variant, "label_model": label_model,
                       "raw_response": "", "error": f"worker crashed: {e}"[:200]}
            _record_path(label_model, tc_id, variant).write_text(
                json.dumps(rec, indent=2), encoding="utf-8")
            done += 1
            if rec.get("error"):
                fails += 1
            if done % 25 == 0 or done == len(jobs):
                el = int(time.time() - t_start)
                print(f"  {done}/{len(jobs)}  ({fails} errors)  {el}s", flush=True)

    print(f"GENERATE [{label_model}] complete: {done} cells, {fails} errors, "
          f"{int(time.time() - t_start)}s", flush=True)
    return 0


# ---------------------------------------------------------------------------
# Phase 2 -- score (sequential reload, no LLM)
# ---------------------------------------------------------------------------

class ReplayProvider(LLMProvider):
    """Returns a stored closed-book response so scoring replays a prior run."""

    def __init__(self, raw_response: str):
        self._raw = raw_response
        self.last_run_metadata = None

    def generate_fhir_query(self, prompt: str, context: str = "") -> GeneratedQuery:
        return build_generated_query(self._raw)


def _score_cell(fhir_client, tc: TestCase, rec: dict) -> dict:
    """Replay one stored generation through EvaluationRunner; mirror the live
    cell dict produced by run_sanity_matrix.run_one_cell."""
    variant = rec["variant"]
    cell = {"tier": 1, "prompt_variant": variant}
    t0 = time.time()
    raw = rec.get("raw_response") or ""
    if rec.get("error") or not raw.strip():
        cell["elapsed_sec"] = 0.0
        cell["error"] = (rec.get("error") or "empty generation")[:200]
        return cell
    try:
        provider = ReplayProvider(raw)
        runner = EvaluationRunner(fhir_client, provider)
        cell_prompt = rec.get("prompt_text") or tc.get_prompt(variant)
        cell_tc = tc.model_copy(update={
            "prompt": cell_prompt, "prompts": {"naive": cell_prompt}})
        result = runner.run_single(cell_tc, provider_name="copilot",
                                   model_name=rec["model"])
        exec_r = result.evaluation_results.execution_match
        gen = result.generated_query
        cell.update({
            "elapsed_sec": round(time.time() - t0, 1),
            "passed": exec_r.passed,
            "precision": exec_r.precision,
            "recall": exec_r.recall,
            "f1": exec_r.f1_score,
            "expected_count": exec_r.expected_count,
            "actual_count": exec_r.actual_count,
            "queries_generated": len(gen.all_queries),
            "primary_query_url": gen.parsed_query.url if gen.parsed_query else None,
            "additional_query_urls": [q.url for q in gen.additional_queries],
            "raw_response": raw[:8000],
            "prompt_text": cell_prompt,
        })
    except Exception as e:  # noqa: BLE001
        cell.update({"elapsed_sec": round(time.time() - t0, 1),
                     "error": str(e)[:200]})
    return cell


def _write_matrix(tc_id: str, label_model: str, fhir_url: str,
                  cells: list[dict]) -> Path:
    cells.sort(key=lambda c: DEFAULT_VARIANTS.index(c["prompt_variant"])
               if c["prompt_variant"] in DEFAULT_VARIANTS else 99)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    safe = _safe_model(label_model)
    out = RESULTS / f"sanity-matrix-{tc_id}-copilot-{safe}-{ts}.json"
    out.write_text(json.dumps({
        "test_case": tc_id,
        "provider": "copilot",
        "model": label_model,
        "fhir_url": fhir_url,
        "host": socket.gethostname(),
        "timestamp": ts,
        "cell_timeout_sec": 0,
        "agent_max_iterations": 0,
        "prompt_versions": {"closed_book": FHIR_SYSTEM_PROMPT_VERSION},
        "source": "run_t1_decoupled.py score",
        "results": cells,
    }, indent=2), encoding="utf-8")
    return out


def _reload(pheno: str, fhir_url: str) -> bool:
    env = os.environ.copy()
    env["FHIR_RELOAD_URL"] = fhir_url
    r = subprocess.run([PY, RELOAD, pheno], env=env)
    return r.returncode == 0


def cmd_score(args: argparse.Namespace) -> int:
    phenos = _read_phenos(args)
    variants = args.prompt_variants.split(",")
    label_models = [_label_model(args.model, ws)
                    for ws in ([False, True] if args.both
                               else [args.with_skill])]
    print(f"SCORE: {len(phenos)} phenotypes x specs {label_models} on {args.fhir_url}",
          flush=True)

    suite_t0 = time.time()
    summary: list[tuple[str, str]] = []
    for i, pheno in enumerate(phenos, 1):
        print(f"\n{'=' * 64}\n[{i}/{len(phenos)}] {pheno}\n{'=' * 64}", flush=True)

        # Skip the (expensive) reload if every output file for this phenotype
        # already exists (full resume).
        tcs = _test_cases_for(pheno)
        if not tcs:
            print(f"  no test cases for {pheno}", flush=True)
            summary.append((pheno, "no-test-cases"))
            continue
        if not args.reload_done and not _reload(pheno, args.fhir_url):
            print(f"!! {pheno}: reload FAILED -- skipping", flush=True)
            summary.append((pheno, "RELOAD-FAILED"))
            continue

        fhir_client = make_fhir_client(args.fhir_url)
        n_files = 0
        n_cells = 0
        n_missing = 0
        for tc_path in tcs:
            tc = _load_tc(tc_path.stem)
            for label_model in label_models:
                cells = []
                for variant in variants:
                    rp = _record_path(label_model, tc.id, variant)
                    if not rp.exists():
                        n_missing += 1
                        cells.append({"tier": 1, "prompt_variant": variant,
                                      "error": "no generation record"})
                        continue
                    rec = json.loads(rp.read_text(encoding="utf-8"))
                    cell = _score_cell(fhir_client, tc, rec)
                    cells.append(cell)
                    n_cells += 1
                _write_matrix(tc.id, label_model, args.fhir_url, cells)
                n_files += 1
        print(f"  -> {n_files} matrix files, {n_cells} scored cells"
              + (f", {n_missing} missing records" if n_missing else ""),
              flush=True)
        summary.append((pheno, f"{n_files} files / {n_cells} cells"))

    print(f"\n{'=' * 64}\n=== SCORE SUMMARY ({int(time.time() - suite_t0)}s) ===")
    for pheno, status in summary:
        print(f"  {pheno:46} {status}", flush=True)
    failed = [p for p, s in summary if s == "RELOAD-FAILED"]
    return 1 if failed else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        g = p.add_mutually_exclusive_group()
        g.add_argument("--phenotypes", nargs="+", help="explicit phenotype names")
        g.add_argument("--phenotypes-file", help="file with one phenotype per line")
        p.add_argument("--model", default="claude-opus-4.7",
                       help="Copilot model name (default: claude-opus-4.7)")
        p.add_argument("--prompt-variants", default=",".join(DEFAULT_VARIANTS))

    g = sub.add_parser("generate", help="Phase 1: closed-book generation (no server)")
    add_common(g)
    g.add_argument("--skill-file", default=None,
                   help="comma-separated skill file(s); presence tags spec '+fhirskill'")
    g.add_argument("--max-workers", type=int, default=8)
    g.add_argument("--timeout-sec", type=int, default=240,
                   help="per-call closed-book timeout (default 240)")
    g.add_argument("--overwrite", action="store_true",
                   help="regenerate even if a successful record exists")
    g.set_defaults(func=cmd_generate)

    s = sub.add_parser("score", help="Phase 2: sequential reload + replay scoring")
    add_common(s)
    skill_grp = s.add_mutually_exclusive_group()
    skill_grp.add_argument("--with-skill", action="store_true",
                           help="score the '+fhirskill' spec instead of plain")
    skill_grp.add_argument("--both", action="store_true",
                           help="score BOTH plain and '+fhirskill' specs per reload")
    s.add_argument("--fhir-url", default="https://jaerwinllm.azurewebsites.net")
    s.add_argument("--reload-done", action="store_true",
                   help="skip the reload step (server already holds this phenotype)")
    s.set_defaults(func=cmd_score)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
