"""Resolve mimicker display strings -> SNOMED codes via the nih-umls MCP.

Reads data/mimicker_packs.json, deduplicates display strings, looks each up
in UMLS, writes data/mimicker_codes.json (committed for reproducibility).

Idempotent: re-running honors the existing cache; only NEW terms hit UMLS.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Callable, Optional

REPO = Path(__file__).resolve().parent.parent
PACKS = REPO / "data" / "mimicker_packs.json"
CODES = REPO / "data" / "mimicker_codes.json"
UMLS_BASE = "https://uts-ws.nlm.nih.gov/rest"
SNOMED_SYSTEM = "http://snomed.info/sct"


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
        try:
            existing = json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"WARNING: corrupt cache at {cache_path}: {exc}. Starting from empty cache.")
            existing = {}

    terms = sorted({m["display"] for pack in packs.values() for m in pack})
    result = dict(existing)
    for term in terms:
        if term in result:
            continue  # cached
        resolved = resolve_one(term, resolver)
        if resolved:
            result[term] = resolved
        # silently skip unresolved -- log handled by caller via main()
    if result == existing:
        return result
    cache_path.write_text(json.dumps(result, indent=2, sort_keys=True),
                          encoding="utf-8")
    return result


def _umls_rest_resolver(term: str) -> Optional[dict]:
    """Resolve a term to a SNOMEDCT_US code via the UMLS REST API directly.

    Two-step lookup matching the nih-umls MCP pattern:
      1. /search exact -> first CUI
      2. /CUI/{cui}/atoms?sabs=SNOMEDCT_US&ttys=PT -> first SNOMED atom

    Requires UMLS_API_KEY in env. Returns None on any failure (missing key,
    404 atoms, network error) so the caller can log + skip cleanly.
    """
    import requests  # local import: not needed for unit tests
    api_key = os.environ.get("UMLS_API_KEY")
    if not api_key:
        print(f"  [SKIP] UMLS_API_KEY not set; cannot resolve {term!r}")
        return None
    try:
        # Step 1: search for the exact term
        r = requests.get(
            f"{UMLS_BASE}/search/current",
            params={"string": term, "searchType": "exact",
                    "pageSize": 1, "apiKey": api_key},
            timeout=10,
        )
        r.raise_for_status()
        results = r.json().get("result", {}).get("results", [])
        if not results or not results[0].get("ui"):
            return None
        cui = results[0]["ui"]
        # Step 2: get a SNOMED atom -- try PT first, fall back to any TTY.
        # Many concepts have SY/FN atoms but no PT; retry without the TTY filter
        # before giving up.
        atom = None
        for ttys in ("PT", None):
            params: dict = {"sabs": "SNOMEDCT_US", "pageSize": 1,
                            "apiKey": api_key}
            if ttys:
                params["ttys"] = ttys
            r = requests.get(
                f"{UMLS_BASE}/content/current/CUI/{cui}/atoms",
                params=params, timeout=10,
            )
            if r.status_code == 404:
                continue
            r.raise_for_status()
            atoms = r.json().get("result", [])
            if atoms:
                atom = atoms[0]
                break
        if not atom:
            return None
        # atom["code"] is a URL like .../SNOMEDCT_US/13645005 -- take the tail
        code = atom["code"].rsplit("/", 1)[-1]
        return {"system": SNOMED_SYSTEM, "code": code, "display": atom["name"]}
    except Exception as exc:  # noqa: BLE001
        print(f"  [ERROR] {term!r}: {exc}")
        return None


def main() -> int:
    if not PACKS.exists():
        print(f"missing {PACKS}; run Task 1 first")
        return 1
    packs = json.loads(PACKS.read_text(encoding="utf-8"))
    result = build_codes_map(packs, _umls_rest_resolver, CODES)

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
