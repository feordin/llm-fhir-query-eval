"""MIMIC-IV evaluator: score model queries against the recomputed MIMIC gold cohorts.

This is the MIMIC counterpart to run_sanity_matrix. The model GENERATION is
identical (same prompts, same providers/tiers) -- only the SCORING differs:

  - gold = the MIMIC patient set from recompute_mimic_gold.py (NOT the synthetic
    expected_patient_ids, which are Synthea UUIDs meaningless on MIMIC), and
  - the model's query is run live against the loaded MIMIC server and patient ids
    are extracted with resolve_stable_ids=False (no Synthea remap).

Per (phenotype, path, prompt-variant, tier) it generates a query, runs it against
MIMIC, and computes P/R/F1 vs the gold cohort. Writes a sanity-matrix-*.json per
(test-case, spec) tagged '+mimic' so the existing aggregator picks it up as a
distinct column.

Evaluable paths on MIMIC: dx (ICD prefix), labs (LOINC threshold), comprehensive
(dx ∪ labs). meds (NDC) and procedures (ICD-10-PCS) don't crosswalk to our
RxNorm/CPT-SNOMED codes, so they're skipped.

Usage (T1 smoke test on one phenotype):
    python scripts/run_mimic_eval.py --phenotypes hypertension \
        --paths dx --tiers 1 --variants naive,broad,expert \
        --provider copilot --model claude-opus-4.7 \
        --fhir-url https://jaerwinllm4.azurewebsites.net
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from run_sanity_matrix import make_provider, make_fhir_client, _read_skill  # noqa: E402

TC_DIR = REPO / "test-cases" / "phekb"
RESULTS = REPO / "results"
PATH_SUFFIX = {"dx": "-dx", "comprehensive": "-comprehensive", "labs": "-labs"}


def _find_tc(phenotype: str, path: str) -> Path | None:
    """Pick the representative test case file for a (phenotype, path)."""
    if path == "dx":
        for cand in (f"phekb-{phenotype}-dx.json", f"phekb-{phenotype}-dx-icd10.json"):
            if (TC_DIR / cand).exists():
                return TC_DIR / cand
        hits = sorted(TC_DIR.glob(f"phekb-{phenotype}-dx*.json"))
        return hits[0] if hits else None
    p = TC_DIR / f"phekb-{phenotype}{PATH_SUFFIX[path]}.json"
    return p if p.exists() else None


def _score(gold: set, got: set) -> dict:
    tp = len(gold & got)
    precision = tp / len(got) if got else (1.0 if not gold else 0.0)
    recall = tp / len(gold) if gold else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4),
            "f1": round(f1, 4), "expected_count": len(gold), "actual_count": len(got)}


def _run_cell(tc, prompt: str, tier: int, variant: str, provider_name: str,
              model: str, fhir_url: str, gold: set, fhir_client,
              cell_timeout: int, lean: bool, system_prefix: str) -> dict:
    cell = {"tier": tier, "prompt_variant": variant}
    t0 = time.time()
    try:
        provider = make_provider(tier, provider_name, model, fhir_url,
                                 cell_timeout_sec=cell_timeout, lean_prompt=lean,
                                 system_prefix=system_prefix)
        gen = provider.generate_fhir_query(prompt)
        urls = [gen.parsed_query.url] if gen.parsed_query else []
        urls += [q.url for q in gen.additional_queries]
        got = set()
        for u in urls:
            if not u:
                continue
            try:
                got |= set(fhir_client.get_patient_ids_from_query(u, resolve_stable_ids=False))
            except Exception as e:  # noqa: BLE001 -- a malformed model URL shouldn't kill the cell
                cell.setdefault("query_errors", []).append(str(e)[:80])
        cell.update(_score(gold, got))
        cell.update({
            "elapsed_sec": round(time.time() - t0, 1),
            "passed": cell["f1"] >= 0.7,
            "queries_generated": len(urls),
            "primary_query_url": urls[0] if urls else None,
            "additional_query_urls": urls[1:],
            "raw_response": (gen.raw_response or "")[:8000],
            "prompt_text": prompt,
        })
    except Exception as e:  # noqa: BLE001
        cell.update({"elapsed_sec": round(time.time() - t0, 1), "error": str(e)[:200]})
    return cell


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phenotypes", nargs="*", help="default: all in the gold file")
    ap.add_argument("--gold", default="data/mimic-gold.json")
    ap.add_argument("--paths", default="dx,comprehensive,labs")
    ap.add_argument("--variants", default="naive,broad,expert")
    ap.add_argument("--tiers", default="1,2,3")
    ap.add_argument("--provider", default="copilot")
    ap.add_argument("--model", default="claude-opus-4.7")
    ap.add_argument("--fhir-url", required=True, help="the loaded MIMIC FHIR server")
    ap.add_argument("--cell-timeout-sec", type=int, default=700)
    ap.add_argument("--lean-prompt", action="store_true")
    ap.add_argument("--skill-file", default=None)
    args = ap.parse_args(argv)

    gold_all = json.loads((REPO / args.gold).read_text(encoding="utf-8"))
    # strip() guards against trailing \r when phenotype names come from a bash
    # mapfile of Windows-line-ended output.
    phenos = [p.strip() for p in (args.phenotypes or list(gold_all.keys())) if p.strip()]
    paths = args.paths.split(",")
    variants = args.variants.split(",")
    tiers = [int(t) for t in args.tiers.split(",")]
    system_prefix = _read_skill(args.skill_file) if args.skill_file else ""
    label_model = args.model + ("+fhirskill" if args.skill_file else "+mimic")
    fhir_client = make_fhir_client(args.fhir_url)
    RESULTS.mkdir(exist_ok=True)

    n_files = 0
    for pheno in phenos:
        g = gold_all.get(pheno)
        if not g:
            continue
        for path in paths:
            gold = set(g.get(path) or [])
            if not gold:
                continue
            tc_path = _find_tc(pheno, path)
            if not tc_path:
                print(f"  {pheno}/{path}: no test case for prompts -- skip", flush=True)
                continue
            sys.path.insert(0, str(REPO / "backend"))
            from src.api.models.test_case import TestCase
            tc = TestCase(**json.loads(tc_path.read_text(encoding="utf-8")))
            cells = []
            for tier in tiers:
                for variant in variants:
                    prompt = tc.get_prompt(variant)
                    lean = args.lean_prompt
                    cell = _run_cell(tc, prompt, tier, variant, args.provider, args.model,
                                     args.fhir_url, gold, fhir_client,
                                     args.cell_timeout_sec, lean, system_prefix)
                    tag = (f"P={cell.get('precision')} R={cell.get('recall')} "
                           f"F1={cell.get('f1')}" if "f1" in cell else
                           f"ERR {cell.get('error', '')[:60]}")
                    print(f"  {pheno}/{path} T{tier} {variant:6} -> {tag} "
                          f"(gold={len(gold)}, got={cell.get('actual_count','?')})", flush=True)
                    cells.append(cell)
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            safe = label_model.replace(":", "-").replace("/", "-")
            out = RESULTS / f"sanity-matrix-{tc.id}-{args.provider}-{safe}-{ts}.json"
            out.write_text(json.dumps({
                "test_case": tc.id, "provider": args.provider, "model": label_model,
                "fhir_url": args.fhir_url, "host": socket.gethostname(), "timestamp": ts,
                "source": "run_mimic_eval.py", "mimic_path": path,
                "results": cells,
            }, indent=2), encoding="utf-8")
            n_files += 1
    print(f"\nwrote {n_files} MIMIC matrix files (model spec '{label_model}')")
    return 0


if __name__ == "__main__":
    sys.exit(main())
