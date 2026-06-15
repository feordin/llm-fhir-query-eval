"""Emit static JSON artifacts for the results-reporting frontend.

Reuses the trusted non-empty-wins cell collection and canonical-case logic so the
numbers reconcile with the sweep/grid reports. Writes to frontend/public/data/:

  leaderboard.json            all-up F1 per model x tier (comprehensive cell) + per-prompt
  phenotypes.json             108 phenotypes x model: comprehensive-cell F1 per tier (matrix)
  phenotypes/<phenotype>.json per-phenotype: every test case's 9-cell grid + full cell detail
  mimic.json                  per-phenotype MIMIC patient counts (if present)
  meta.json                   cutoff, models, generation timestamp (passed in), coverage

Usage:
  python scripts/build_frontend_data.py --since 20260516T000000Z \
      --exclude-models ollama --stamp 20260607T000000Z
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from aggregate_sweep import _collect_latest_cells, _tc_to_phenotype  # noqa: E402
from build_grid_report import canonical_cases  # noqa: E402
from mimic_phenotype_counts import PHENOTYPES  # noqa: E402

OUT = REPO / "frontend" / "public" / "data"
VARIANTS = ["naive", "broad", "expert"]
TIERS = [1, 2, 3]

# Cell fields surfaced in per-phenotype detail (everything we captured).
DETAIL_FIELDS = [
    "precision", "recall", "f1", "passed", "expected_count", "actual_count",
    "elapsed_sec", "queries_generated", "primary_query_url", "additional_query_urls",
    "raw_response", "prompt_text", "error",
]
META_FIELDS = ["output_tokens", "tool_calls_count", "stop_reason", "fallback_used"]


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def build(since: str, exclude: tuple, stamp: str) -> dict:
    cell_map, _ = _collect_latest_cells(since, PHENOTYPES, exclude)
    canon = canonical_cases()
    canon_tcs = {tc for tc in canon.values() if tc}

    # index: spec -> tc -> (tier, variant) -> cell
    tree = defaultdict(lambda: defaultdict(dict))
    specs = set()
    for (tc, spec, tier, variant), (ts, cell) in cell_map.items():
        specs.add(spec)
        tree[spec][tc][(tier, variant)] = cell
    specs = sorted(specs)

    # ---- best tier x prompt per spec, over ALL test cases (the "ceiling") ------
    # Distinct from the per-tier comprehensive-cohort means above: this is each
    # model's single best (tier, variant) combination averaged across every test
    # case (matches presentation Slide 14B).
    all_tv = defaultdict(lambda: defaultdict(list))  # spec -> (tier,variant) -> f1s
    for (tc, spec, tier, variant), (ts, cell) in cell_map.items():
        f1 = cell.get("f1")
        if f1 is not None:
            all_tv[spec][(tier, variant)].append(f1)

    def _best_combo(spec):
        means = {k: sum(v) / len(v) for k, v in all_tv[spec].items() if v}
        if not means:
            return None
        (t, v), f1 = max(means.items(), key=lambda kv: kv[1])
        return {"tier": t, "variant": v, "f1": f1}

    # ---- leaderboard.json: all-up over canonical cells, per model x tier -------
    lb_rows = []
    for spec in specs:
        per_tier = {}
        for t in TIERS:
            f1s = []
            by_prompt = {v: [] for v in VARIANTS}
            cov = [0, 0]
            for tc in canon_tcs:
                for v in VARIANTS:
                    c = tree[spec].get(tc, {}).get((t, v))
                    if c is None:
                        continue
                    cov[1] += 1
                    if c.get("f1") is not None:
                        f1s.append(c["f1"]); by_prompt[v].append(c["f1"]); cov[0] += 1
            per_tier[str(t)] = {
                "f1": _mean(f1s),
                "coverage": (cov[0] / cov[1]) if cov[1] else None,
                "by_prompt": {v: _mean(by_prompt[v]) for v in VARIANTS},
            }
        lb_rows.append({"model": spec, "tiers": per_tier, "best": _best_combo(spec)})

    leaderboard = {"models": specs, "tiers": TIERS, "rows": lb_rows, "stamp": stamp}

    # ---- phenotypes.json: matrix of comprehensive-cell F1 per tier -------------
    ph_rows = []
    for p in PHENOTYPES:
        tc = canon[p]
        scores = {}
        for spec in specs:
            cells = tree[spec].get(tc, {})
            scores[spec] = {
                str(t): _mean([cells[(t, v)]["f1"] for v in VARIANTS
                               if (t, v) in cells and cells[(t, v)].get("f1") is not None])
                for t in TIERS
            }
        ph_rows.append({"phenotype": p, "canonical_tc": tc, "scores": scores})
    phenotypes = {"phenotypes": ph_rows, "models": specs}

    # ---- per-phenotype detail files -------------------------------------------
    pheno_detail = {}
    for p in PHENOTYPES:
        # all test cases (any spec) belonging to this phenotype
        tcs = sorted({tc for spec in specs for tc in tree[spec]
                      if _tc_to_phenotype(tc, PHENOTYPES) == p})
        cases = []
        for tc in tcs:
            grids = {}
            for spec in specs:
                grid = {}
                for t in TIERS:
                    for v in VARIANTS:
                        c = tree[spec].get(tc, {}).get((t, v))
                        if c is None:
                            continue
                        cell = {k: c.get(k) for k in DETAIL_FIELDS if k in c}
                        rm = c.get("run_metadata") or {}
                        meta = {k: rm.get(k) for k in META_FIELDS if k in rm}
                        if meta:
                            cell["run_metadata"] = meta
                        grid[f"{t}-{v}"] = cell
                if grid:
                    grids[spec] = grid
            cases.append({"test_case": tc, "grids": grids})
        pheno_detail[p] = {"phenotype": p, "canonical_tc": canon[p], "cases": cases}

    # ---- mimic.json (optional) -------------------------------------------------
    mimic = None
    mimic_csv = None  # counts come from the report; re-derive lazily if available

    # ---- meta.json -------------------------------------------------------------
    meta = {
        "since": since, "stamp": stamp, "models": specs,
        "excluded": list(exclude),
        "tier_labels": {"1": "closed-book", "2": "agentic+tools", "3": "+methodology"},
        "prompt_labels": {"naive": "untrained user", "broad": "clinically-aware, no codes",
                          "expert": "code-aware spec"},
    }

    return {"leaderboard": leaderboard, "phenotypes": phenotypes,
            "pheno_detail": pheno_detail, "meta": meta, "mimic": mimic}


def write_all(data: dict):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "leaderboard.json").write_text(json.dumps(data["leaderboard"], indent=1), encoding="utf-8")
    (OUT / "phenotypes.json").write_text(json.dumps(data["phenotypes"], indent=1), encoding="utf-8")
    (OUT / "meta.json").write_text(json.dumps(data["meta"], indent=1), encoding="utf-8")
    pdir = OUT / "phenotypes"
    pdir.mkdir(exist_ok=True)
    for p, detail in data["pheno_detail"].items():
        (pdir / f"{p}.json").write_text(json.dumps(detail, indent=1), encoding="utf-8")
    if data.get("mimic"):
        (OUT / "mimic.json").write_text(json.dumps(data["mimic"], indent=1), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", required=True)
    ap.add_argument("--exclude-models", nargs="*", default=[])
    ap.add_argument("--stamp", required=True, help="generation timestamp (Date.now is unavailable in-script)")
    args = ap.parse_args(argv)
    data = build(args.since, tuple(args.exclude_models), args.stamp)
    write_all(data)
    n_detail = len(data["pheno_detail"])
    print(f"models: {len(data['leaderboard']['models'])}  phenotype detail files: {n_detail}")
    print(f"wrote {OUT}/leaderboard.json, phenotypes.json, meta.json, phenotypes/<{n_detail}>.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
