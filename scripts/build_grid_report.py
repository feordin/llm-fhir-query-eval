"""Per-test-case performance grids: for each model, for each test case, a 3x3
(prompt-variant x tier) grid of P/R/F1.

Reuses aggregate_sweep's non-empty-wins cell collection so numbers reconcile with
the headline sweep report. Emits a markdown report (model -> phenotype ->
test-case grids) and a flat CSV backbone.

Usage:
    python scripts/build_grid_report.py --since 20260527T000000Z \\
        --out docs/results/2026-06-07-per-testcase-grids \\
        --exclude-models ollama
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from aggregate_sweep import _collect_latest_cells, _tc_to_phenotype  # noqa: E402
from mimic_phenotype_counts import PHENOTYPES  # noqa: E402

VARIANTS = ["naive", "broad", "expert"]
TIERS = [1, 2, 3]


def canonical_cases() -> dict:
    """phenotype -> its 'all-patients' test case: -comprehensive if present, else
    the base `phekb-<p>`, else the shortest-named case."""
    import glob
    import os
    by: dict = {}
    for f in glob.glob(str(REPO / "test-cases" / "phekb" / "phekb-*.json")):
        tc = os.path.basename(f)[:-5]
        name = tc[len("phekb-"):]
        ph = next((p for p in sorted(PHENOTYPES, key=len, reverse=True)
                   if name == p or name.startswith(p + "-")), None)
        if ph:
            by.setdefault(ph, []).append(tc)
    canon = {}
    for p in PHENOTYPES:
        tcs = by.get(p, [])
        comp = [t for t in tcs if t.endswith("-comprehensive")]
        exact = [t for t in tcs if t == f"phekb-{p}"]
        canon[p] = comp[0] if comp else (exact[0] if exact else (sorted(tcs, key=len)[0] if tcs else None))
    return canon


def fmt_cell(cell: dict | None) -> str:
    """'P/R/F1' for a scored cell, '—' for missing/empty."""
    if not cell or cell.get("f1") is None:
        return "—"
    return f"{cell.get('precision', 0):.2f}/{cell.get('recall', 0):.2f}/{cell['f1']:.2f}"


def build(since: str, exclude: tuple) -> dict:
    """spec -> phenotype -> test_case -> {(tier, variant): cell}."""
    cell_map, _ = _collect_latest_cells(since, PHENOTYPES, exclude)
    tree: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for (tc, spec, tier, variant), (ts, cell) in cell_map.items():
        pheno = _tc_to_phenotype(tc, PHENOTYPES) or "?"
        tree[spec][pheno][tc][(tier, variant)] = cell
    return tree


def render_markdown(tree: dict, since: str) -> str:
    lines = [
        "# Per-Test-Case Performance Grids (P / R / F1)",
        "",
        f"Each cell is precision / recall / F1. Rows = prompt complexity, "
        f"columns = evaluation tier. Cells since {since}, non-empty-wins dedup "
        f"(reconciles with the headline sweep report). '—' = no scored cell.",
        "",
        "- **naive** = untrained-user phrasing · **broad** = clinically-aware, no codes · **expert** = code-aware spec",
        "- **T1** = closed-book · **T2** = agentic+tools · **T3** = +methodology",
        "",
    ]
    # all-up leaderboard: mean F1 of the canonical "all-patients" cell per model x tier
    canon = canonical_cases()
    canon_tc = {tc for tc in canon.values() if tc}
    lead = defaultdict(lambda: defaultdict(list))   # spec -> tier -> [f1]
    lead_cov = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for spec in tree:
        for pheno in tree[spec]:
            for tc in tree[spec][pheno]:
                if tc not in canon_tc:
                    continue
                for (tier, variant), c in tree[spec][pheno][tc].items():
                    lead_cov[spec][tier][1] += 1
                    if c.get("f1") is not None:
                        lead[spec][tier].append(c["f1"])
                        lead_cov[spec][tier][0] += 1
    lines.append("## All-up F1 leaderboard (comprehensive / all-patients cell)\n")
    lines.append("Mean F1 over each phenotype's **all-patients** test case "
                 "(`-comprehensive` where it exists, else the base case), averaged across "
                 "the naive/broad/expert prompts. This is the high-level model comparison: "
                 "*how well does each model find the whole cohort?*\n")
    lines.append("| model | T1 closed-book | T2 agentic+tools | T3 +methodology |")
    lines.append("|-------|----|----|----|")
    for spec in sorted(tree):
        cells = []
        for t in TIERS:
            xs = lead[spec][t]
            s, tot = lead_cov[spec][t]
            cells.append(f"**{sum(xs)/len(xs):.3f}** ({100*s/tot:.0f}%)" if xs else "—")
        lines.append(f"| `{spec}` | " + " | ".join(cells) + " |")
    lines.append("\n(Percentages = canonical-cell coverage; means are over scored cells.)\n")

    # coverage summary (scored cells / total, per model x tier)
    lines.append("## Coverage\n")
    lines.append("Share of cells with a scored result ('—' cells are unscored: timeout, "
                 "agentic error, or only run before the cutoff window).\n")
    lines.append("| model | T1 | T2 | T3 |")
    lines.append("|-------|----|----|----|")
    for spec in sorted(tree):
        cov = {t: [0, 0] for t in TIERS}
        for pheno in tree[spec]:
            for tc in tree[spec][pheno]:
                for (tier, variant), c in tree[spec][pheno][tc].items():
                    cov[tier][1] += 1
                    if c.get("f1") is not None:
                        cov[tier][0] += 1
        cells = []
        for t in TIERS:
            s, tot = cov[t]
            cells.append(f"{s}/{tot} ({100*s/tot:.0f}%)" if tot else "—")
        lines.append(f"| `{spec}` | " + " | ".join(cells) + " |")
    lines.append("")

    for spec in sorted(tree):
        lines.append(f"\n## Model: `{spec}`\n")
        for pheno in sorted(tree[spec]):
            lines.append(f"\n### {pheno}\n")
            for tc in sorted(tree[spec][pheno]):
                cells = tree[spec][pheno][tc]
                lines.append(f"\n**`{tc}`**\n")
                lines.append("| prompt | T1 | T2 | T3 |")
                lines.append("|--------|----|----|----|")
                for v in VARIANTS:
                    row = [v]
                    for t in TIERS:
                        row.append(fmt_cell(cells.get((t, v))))
                    lines.append("| " + " | ".join(row) + " |")
                lines.append("")
    return "\n".join(lines)


def write_csv(tree: dict, path: Path) -> int:
    n = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "phenotype", "test_case", "tier", "prompt_variant",
                    "precision", "recall", "f1", "expected_count", "actual_count"])
        for spec in sorted(tree):
            for pheno in sorted(tree[spec]):
                for tc in sorted(tree[spec][pheno]):
                    for (tier, variant), c in sorted(tree[spec][pheno][tc].items()):
                        w.writerow([spec, pheno, tc, tier, variant,
                                    c.get("precision"), c.get("recall"), c.get("f1"),
                                    c.get("expected_count"), c.get("actual_count")])
                        n += 1
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", required=True)
    ap.add_argument("--out", required=True, help="output path stem (.md + .csv appended)")
    ap.add_argument("--exclude-models", nargs="*", default=[])
    args = ap.parse_args(argv)

    tree = build(args.since, tuple(args.exclude_models))
    out = Path(args.out)
    md = render_markdown(tree, args.since)
    out.with_suffix(".md").write_text(md, encoding="utf-8")
    ncsv = write_csv(tree, out.with_suffix(".csv"))

    n_grids = sum(len(tree[s][p]) for s in tree for p in tree[s])
    print(f"models: {len(tree)}  test-case grids: {n_grids}  csv rows: {ncsv}")
    print(f"wrote {out.with_suffix('.md')}")
    print(f"wrote {out.with_suffix('.csv')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
