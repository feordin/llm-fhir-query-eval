"""Build an NDC -> RxNorm (RxCUI) crosswalk for MIMIC Medication resources.

MIMIC-on-FHIR Medications carry only NDC under a MIMIC-local system, so our
RxNorm-coded medication gold cannot score the meds path. This script resolves
each distinct NDC via the NLM RxNav `ndcstatus` API (no key required) and
writes data/ndc_rxnorm_map.json: {ndc: {"rxcui", "name", "status"}}.

Idempotent: existing map entries are kept; only new NDCs hit the API.

Usage:
    python scripts/build_ndc_rxnorm_map.py [--ndc-list data/mimic-ndc-list.txt]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RXNAV = "https://rxnav.nlm.nih.gov/REST/ndcstatus.json?ndc="


def lookup(ndc: str, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(RXNAV + ndc, timeout=30) as r:
                st = json.load(r).get("ndcStatus") or {}
            rxcui = st.get("rxcui") or ""
            if rxcui and rxcui != "0":
                return {"rxcui": rxcui, "name": st.get("conceptName", ""),
                        "status": st.get("status", "")}
            return None  # known-unmapped
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ndc-list", default="data/mimic-ndc-list.txt")
    ap.add_argument("--out", default="data/ndc_rxnorm_map.json")
    ap.add_argument("--sleep", type=float, default=0.08)
    args = ap.parse_args(argv)

    ndcs = [l.strip() for l in (REPO / args.ndc_list).read_text().splitlines() if l.strip()]
    out_path = REPO / args.out
    m = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    todo = [n for n in ndcs if n not in m]
    print(f"{len(ndcs)} NDCs, {len(todo)} to resolve", flush=True)
    hits = errs = 0
    for i, ndc in enumerate(todo):
        try:
            res = lookup(ndc)
        except Exception as e:
            errs += 1
            print(f"  ERR {ndc}: {e}", flush=True)
            continue
        m[ndc] = res  # None recorded too, so reruns skip known-unmapped
        if res:
            hits += 1
        if (i + 1) % 500 == 0:
            print(f"  {i+1}/{len(todo)} ({hits} mapped)", flush=True)
            out_path.write_text(json.dumps(m, indent=0), encoding="utf-8")
        time.sleep(args.sleep)
    out_path.write_text(json.dumps(m, indent=0), encoding="utf-8")
    mapped = sum(1 for v in m.values() if v)
    print(f"DONE: {mapped}/{len(m)} NDCs mapped to RxCUI ({errs} errors) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
