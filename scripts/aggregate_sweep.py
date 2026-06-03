"""Aggregate sanity-matrix result JSONs into a markdown report.

Pass a list of phenotypes (kebab-case) and a since-timestamp; the script
picks the most-recent (test_case, provider:model) cell per pair, computes
per-model/tier/variant means, and writes a markdown report to docs/results/.

Usage:
    python scripts/aggregate_sweep.py \
        --since 20260521T200000Z \
        --label rigorous-21 \
        --phenotypes hypertension heart-failure asthma copd ...

The since-timestamp is the cutoff for inclusion; cells with earlier
result-file timestamps are ignored (so prior smoke-test runs don't pollute).
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results"
OUT_DIR = REPO / "docs" / "results"

_FILENAME_RE = re.compile(
    r"sanity-matrix-(phekb-.+?)-"
    r"(copilot|ollama|openai-compat|azure-openai|foundry-local)-"
    r"(.+?)-(\d{8}T\d{6}Z)\.json$"
)


def _tc_to_phenotype(tc: str, phenotypes: list[str]) -> str | None:
    """Longest-prefix-match: phekb-heart-failure-comprehensive -> heart-failure."""
    body = tc[len("phekb-"):]
    best = None
    for p in phenotypes:
        if body == p or body.startswith(p + "-"):
            if best is None or len(p) > len(best):
                best = p
    return best


def _collect_latest_cells(since: str, phenotypes: list[str]) -> tuple[dict, set]:
    """For each (test_case, spec, tier, variant), pick the latest *non-empty*
    F1 cell across all matching result files. If no non-empty cell exists for
    that key, fall back to the latest cell so empty-rate stays accurate.

    Returns (cells, files_used) where cells maps (tc, spec, tier, variant) ->
    (ts, cell_dict) and files_used is the set of source files actually
    contributing data."""
    best_nonnull: dict = {}
    best_any: dict = {}
    file_for: dict = {}  # key -> source path

    for f in sorted(RESULTS.glob("sanity-matrix-phekb-*.json")):
        m = _FILENAME_RE.search(f.name)
        if not m:
            continue
        tc, prov, model, ts = m.group(1), m.group(2), m.group(3), m.group(4)
        if ts < since:
            continue
        if _tc_to_phenotype(tc, phenotypes) is None:
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        spec = f"{prov}:{model}"
        for c in d.get("results", []):
            tier = c.get("tier")
            variant = c.get("prompt_variant")
            if tier is None or variant is None:
                continue
            key = (tc, spec, tier, variant)
            f1 = c.get("f1")
            if key not in best_any or ts > best_any[key][0]:
                best_any[key] = (ts, c)
                if key not in best_nonnull:
                    file_for[key] = f
            if f1 is not None and (key not in best_nonnull or ts > best_nonnull[key][0]):
                best_nonnull[key] = (ts, c)
                file_for[key] = f

    merged: dict = {}
    for key in best_any:
        merged[key] = best_nonnull[key] if key in best_nonnull else best_any[key]
    files_used = set(file_for.values())
    return merged, files_used


def aggregate(label: str, since: str, phenotypes: list[str]) -> Path:
    cell_map, files_used = _collect_latest_cells(since, phenotypes)

    # [model] -> {tier -> [f1s]}; per-phenotype: [pheno][model][tier] -> [f1s]
    agg = defaultdict(lambda: defaultdict(list))
    per_pheno = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    per_variant = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    empties = defaultdict(int)
    cells = defaultdict(int)
    tc_seen = defaultdict(set)

    for (tc, spec, tier, variant), (ts, c) in cell_map.items():
        pheno = _tc_to_phenotype(tc, phenotypes)
        tc_seen[spec].add(tc)
        cells[spec] += 1
        f1 = c.get("f1")
        if f1 is None:
            empties[spec] += 1
        else:
            agg[spec][tier].append(f1)
            per_pheno[pheno][spec][tier].append(f1)
            per_variant[spec][tier][variant].append(f1)

    models = sorted(agg)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    lines: list[str] = []
    lines.append(f"# Sweep results: {label}\n")
    lines.append(f"_Aggregated {timestamp} from {len(files_used)} result files "
                 f"(filenames since {since}; cell-level non-empty-wins dedup)._\n")
    lines.append(f"Phenotypes in scope: **{len(phenotypes)}**. Models compared: "
                 f"**{len(models)}**.\n")

    lines.append("## Headline: mean F1 by tier\n")
    lines.append("| Model | T1 closed-book | T2 agentic+tools | T3 +methodology | "
                 "Test cases | Cells | Empty % |")
    lines.append("|---|---|---|---|---|---|---|")
    for spec in models:
        row = [f"`{spec}`"]
        for t in (1, 2, 3):
            xs = agg[spec][t]
            row.append(f"**{sum(xs)/len(xs):.3f}**" if xs else "—")
        n_cells = cells[spec]
        empty_pct = 100.0 * empties[spec] / n_cells if n_cells else 0.0
        row.append(str(len(tc_seen[spec])))
        row.append(str(n_cells))
        row.append(f"{empty_pct:.1f}%")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("\n## Per-phenotype Tier 2 F1 (agentic+tools, mean over variants)\n")
    lines.append("| Phenotype | " + " | ".join(f"`{m}`" for m in models) + " |")
    lines.append("|" + "---|" * (len(models) + 1))
    for pheno in sorted(per_pheno):
        row = [f"`{pheno}`"]
        for m in models:
            xs = per_pheno[pheno][m][2]
            row.append(f"{sum(xs)/len(xs):.3f}" if xs else "—")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("\n## Per-variant breakdown (mean F1)\n")
    for spec in models:
        lines.append(f"### `{spec}`\n")
        lines.append("| Tier | naive | broad | expert |")
        lines.append("|---|---|---|---|")
        for t in (1, 2, 3):
            row = [f"T{t}"]
            for v in ("naive", "broad", "expert"):
                xs = per_variant[spec][t][v]
                row.append(f"{sum(xs)/len(xs):.3f}" if xs else "—")
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{label}.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out_path.relative_to(REPO)} ({len(cell_map)} cells across "
          f"{len(models)} models, {len(per_pheno)} phenotypes)")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", required=True,
                    help="Inclusion cutoff for result-file timestamps, e.g. 20260521T200000Z")
    ap.add_argument("--label", required=True,
                    help="Report slug used in output filename")
    ap.add_argument("--phenotypes", nargs="+", required=True,
                    help="Kebab-case phenotype names in scope for this report")
    args = ap.parse_args()
    aggregate(args.label, args.since, args.phenotypes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
