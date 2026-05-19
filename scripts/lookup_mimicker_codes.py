"""Resolve mimicker display strings -> SNOMED codes via the nih-umls MCP.

Reads data/mimicker_packs.json, deduplicates display strings, looks each up
in UMLS, writes data/mimicker_codes.json (committed for reproducibility).

Idempotent: re-running honors the existing cache; only NEW terms hit UMLS.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, Optional

REPO = Path(__file__).resolve().parent.parent
PACKS = REPO / "data" / "mimicker_packs.json"
CODES = REPO / "data" / "mimicker_codes.json"


def resolve_one(term: str, resolver: Callable[[str], Optional[dict]]) -> Optional[dict]:
    """Resolve one display string via the provided callable. Returns
    {"system", "code", "display"} or None if unresolved."""
    return resolver(term)


def build_codes_map(
    packs: dict,
    resolver: Callable[[str], Optional[dict]],
    cache_path: Path,
) -> dict:
    """Resolve all unique mimicker terms across all phenotype packs.

    Args:
        packs: {phenotype: [{"display": str, "prevalence": float}, ...]}
        resolver: term -> {"system", "code", "display"} or None
        cache_path: existing cache JSON file (preserved on re-runs)

    Returns:
        {display_string: {"system", "code", "display"}}
    """
    existing: dict = {}
    if cache_path.exists():
        existing = json.loads(cache_path.read_text(encoding="utf-8"))

    terms = sorted({m["display"] for pack in packs.values() for m in pack})
    result = dict(existing)
    for term in terms:
        if term in result:
            continue  # cached
        resolved = resolve_one(term, resolver)
        if resolved:
            result[term] = resolved
        # silently skip unresolved -- log handled by caller via main()
    cache_path.write_text(json.dumps(result, indent=2, sort_keys=True),
                          encoding="utf-8")
    return result


def _umls_mcp_resolver(term: str) -> Optional[dict]:
    """Real resolver: call the nih-umls MCP via the helper in the umls skill.

    Returns the best SNOMED CT match (rootSource == 'SNOMEDCT_US') or None.

    Implementation note: the umls MCP is invoked from the LLM client side,
    not directly from this script. For this script, the operator runs it in a
    Claude Code session where the MCP is available, OR the operator pre-
    populates data/mimicker_codes.json from a manual UMLS session (using
    /umls codes-for <term>) and re-runs this script idempotently to fill
    in any gaps.
    """
    print(f"  [MANUAL] '{term}' not in cache and no MCP access from this script.")
    print(f"           Run in Claude Code: /umls codes-for {term!r}")
    print(f"           Then add to {CODES.relative_to(REPO)} and re-run.")
    return None


def main() -> int:
    if not PACKS.exists():
        print(f"missing {PACKS}; run Task 1 first")
        return 1
    packs = json.loads(PACKS.read_text(encoding="utf-8"))
    result = build_codes_map(packs, _umls_mcp_resolver, CODES)

    # Report
    all_terms = sorted({m["display"] for pack in packs.values() for m in pack})
    resolved = sum(1 for t in all_terms if t in result)
    print(f"\n{resolved}/{len(all_terms)} mimicker terms resolved -> {CODES.relative_to(REPO)}")
    if resolved < len(all_terms):
        print("Unresolved (operator: run /umls codes-for each and re-run):")
        for t in all_terms:
            if t not in result:
                print(f"  - {t}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
