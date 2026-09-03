#!/usr/bin/env python3
"""FHIR server introspection helper for the cohort-query workflow.

Answers the three discovery questions the workflow needs, without guessing:
  1. What can this server do?           (capability summary from /metadata)
  2. How is the data actually coded?    (--census: code-system frequency per type)
  3. How big is a candidate cohort?     (--count: run a query with _summary=count)

Stdlib only (urllib); works against any open or bearer-token FHIR R4 endpoint.

Usage:
    python fhir_introspect.py https://fhir.example.com            # capability summary
    python fhir_introspect.py <base> --census Condition           # code-system census
    python fhir_introspect.py <base> --census Condition --n 200   # bigger sample
    python fhir_introspect.py <base> --count "Condition?code=http://hl7.org/fhir/sid/icd-10-cm|E11.9"
    FHIR_BEARER_TOKEN=... python fhir_introspect.py <base>        # authenticated
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
from collections import Counter


def _get(base: str, path: str, timeout: int = 60) -> dict:
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"Accept": "application/fhir+json"})
    token = os.environ.get("FHIR_BEARER_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    ctx = ssl.create_default_context()
    if os.environ.get("FHIR_INSECURE"):  # opt-in only, for test servers
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return json.load(r)


def capability_summary(base: str) -> None:
    cap = _get(base, "metadata")
    print(f"FHIR version : {cap.get('fhirVersion')}")
    print(f"Software     : {cap.get('software', {}).get('name', '?')}")
    rest = (cap.get("rest") or [{}])[0]
    for res in rest.get("resource", []):
        rtype = res.get("type")
        params = sorted(p.get("name", "") for p in res.get("searchParam", []))
        interesting = [p for p in params
                       if p in ("code", "value-quantity", "patient", "subject",
                                "onset-date", "authored-on", "category", "gender",
                                "birthdate", "date")]
        has = "_has " if res.get("searchRevInclude") else ""
        inc = "_include " if res.get("searchInclude") else ""
        if rtype in ("Patient", "Condition", "Observation", "MedicationRequest",
                     "Procedure", "Encounter", "Medication"):
            print(f"  {rtype:20s} {has}{inc}params: {', '.join(interesting) or '(none listed)'}")
    print("\nSupported profiles (first 10):")
    seen = 0
    for res in rest.get("resource", []):
        for p in res.get("supportedProfile", []) or []:
            print(f"  {res.get('type'):16s} {p}")
            seen += 1
            if seen >= 10:
                return
    if not seen:
        print("  (none declared — base FHIR; any code system possible)")


def census(base: str, rtype: str, n: int) -> None:
    """Frequency of coding.system (and dotted-ness/granularity) in a sample."""
    fetched, systems, samples = 0, Counter(), {}
    page = _get(base, f"{rtype}?_count={min(100, n)}")
    while page and fetched < n:
        for e in page.get("entry", []) or []:
            r = e.get("resource", {})
            fetched += 1
            for field in ("code", "medicationCodeableConcept"):
                cc = r.get(field)
                if isinstance(cc, dict):
                    for cd in cc.get("coding", []) or []:
                        s = cd.get("system", "(no system)")
                        systems[s] += 1
                        samples.setdefault(s, cd.get("code"))
            if "medicationReference" in r:
                systems["(medicationReference -> Medication resource)"] += 1
            if fetched >= n:
                break
        nxt = next((l["url"] for l in page.get("link", []) if l.get("relation") == "next"), None)
        if not nxt or fetched >= n:
            break
        req = urllib.request.Request(nxt, headers={"Accept": "application/fhir+json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            page = json.load(resp)
    print(f"{rtype}: sampled {fetched} resources")
    for s, c in systems.most_common():
        ex = samples.get(s, "")
        print(f"  {c:6d}  {s}   e.g. code={ex!r}")
    if not systems:
        print("  (no codings found — empty server or unexpected shape)")


def count(base: str, query: str) -> None:
    sep = "&" if "?" in query else "?"
    b = _get(base, f"{query}{sep}_summary=count")
    print(f"{query}\n  -> total = {b.get('total')}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", help="FHIR base URL, e.g. https://fhir.example.com/r4")
    ap.add_argument("--census", metavar="RESOURCETYPE",
                    help="code-system census for one resource type")
    ap.add_argument("--n", type=int, default=100, help="census sample size (default 100)")
    ap.add_argument("--count", metavar="QUERY",
                    help="run a relative FHIR query with _summary=count")
    args = ap.parse_args()
    if args.census:
        census(args.base, args.census, args.n)
    elif args.count:
        count(args.base, args.count)
    else:
        capability_summary(args.base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
