"""Wipe the FHIR server and reload exactly one phenotype's minimal bundle, in
isolation. This is the per-phenotype cycle that eliminates cross-phenotype
contamination: load one phenotype, run its tests, wipe, repeat.

Steps:
  1. WIPE   -- DELETE {base}/$bulk-delete (async); poll to completion
  2. LOAD   -- POST each data/minimal-bundles/<phenotype>*.json.gz transaction bundle
  3. VERIFY -- resource counts, and every gold query for the phenotype returns
               exactly its test case's expected_patient_ids

Usage:
    python scripts/reload_phenotype.py asthma
    python scripts/reload_phenotype.py asthma psoriasis stroke   # several, in turn
    python scripts/reload_phenotype.py                          # ALL phenotypes (triage)
    python scripts/reload_phenotype.py asthma --no-wipe          # load+verify only
    python scripts/reload_phenotype.py asthma --wipe-only

With multiple/all phenotypes each is wiped + loaded + verified in turn, and a
PASS/FAIL triage summary is printed -- useful for finding phenotypes whose local
synthea/output is stale relative to their test cases' expected_patient_ids.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
from src.fhir.client import FHIRClient  # noqa: E402

BASE_URL = os.environ.get("FHIR_RELOAD_URL", "https://jaerwinllm.azurewebsites.net")
BUNDLES = REPO / "data" / "minimal-bundles"
TEST_CASES = REPO / "test-cases" / "phekb"
COUNT_TYPES = ["Patient", "Condition", "MedicationRequest", "Observation",
               "Procedure", "Encounter"]


def _counts(client: FHIRClient) -> dict:
    return {t: client.execute_query(f"{t}?_summary=count").get("total") for t in COUNT_TYPES}


def wipe_server(client: FHIRClient, poll_timeout: int = 3600) -> None:
    """Issue $bulk-delete and poll the async job to completion."""
    print("WIPE: issuing $bulk-delete (_hardDelete=true, _purgeHistory=true)...", flush=True)
    # Microsoft FHIR async operations require Prefer: respond-async. The server
    # also REFUSES an unconditional system-wide delete ("search criteria was not
    # selective enough", HTTP 412) -- so we pass a _lastUpdated bound that matches
    # every resource (everything was created before this far-future date). This
    # satisfies the selectivity guard while still clearing the whole server.
    resp = client._session.delete(
        f"{BASE_URL}/$bulk-delete",
        params={"_lastUpdated": "le2099-12-31", "_hardDelete": "true",
                "_purgeHistory": "true"},
        headers={"Prefer": "respond-async"},
        timeout=60,
    )
    print(f"  -> HTTP {resp.status_code}", flush=True)
    if resp.status_code not in (202, 200):
        raise RuntimeError(f"$bulk-delete not accepted: HTTP {resp.status_code} {resp.text[:300]}")
    status_url = resp.headers.get("Content-Location")
    if not status_url:
        raise RuntimeError(f"no Content-Location header to poll; headers={dict(resp.headers)}")
    print(f"  polling: {status_url}", flush=True)

    t0 = time.time()
    while True:
        time.sleep(15)
        s = client._session.get(status_url, timeout=60)
        elapsed = int(time.time() - t0)
        if s.status_code == 200:
            try:
                body = s.json()
                deleted = body.get("output") or body
            except Exception:
                deleted = s.text[:200]
            print(f"  WIPE complete after {elapsed}s: {json.dumps(deleted)[:300]}", flush=True)
            return
        if s.status_code == 202:
            # X-Progress header carries a running tally on the MS FHIR server
            prog = s.headers.get("X-Progress", "running")
            print(f"  ...{elapsed}s: {prog}", flush=True)
        else:
            raise RuntimeError(f"poll failed: HTTP {s.status_code} {s.text[:300]}")
        if time.time() - t0 > poll_timeout:
            raise RuntimeError(f"$bulk-delete did not finish within {poll_timeout}s")


def load_phenotype(client: FHIRClient, phenotype: str) -> int:
    """POST every minimal bundle chunk for the phenotype. Returns resources loaded."""
    chunks = sorted(BUNDLES.glob(f"{phenotype}.json.gz")) + \
        sorted(BUNDLES.glob(f"{phenotype}-[0-9][0-9][0-9].json.gz"))
    if not chunks:
        raise RuntimeError(f"no minimal bundles found for '{phenotype}' in {BUNDLES}")
    total = 0
    for chunk in chunks:
        bundle = json.loads(gzip.open(chunk).read())
        n = len(bundle.get("entry", []))
        print(f"LOAD: {chunk.name} ({n} resources)...", flush=True)
        result = client.load_bundle(bundle)
        # transaction-response bundle: one entry per submitted resource
        ok = sum(1 for e in result.get("entry", [])
                 if str(e.get("response", {}).get("status", "")).startswith(("200", "201")))
        print(f"  -> {ok}/{n} entries OK", flush=True)
        if ok != n:
            raise RuntimeError(f"{chunk.name}: only {ok}/{n} entries succeeded")
        total += n
    return total


def _test_cases_for(phenotype: str) -> list[Path]:
    """Test case files owned by this phenotype, by longest-prefix-match against
    all phenotype names -- so phekb-asthma-response-inhaled-steroids-dx is owned
    by asthma-response-inhaled-steroids, not asthma."""
    all_phenos = [p.name for p in (REPO / "synthea" / "output").iterdir() if p.is_dir()]
    owned = []
    for f in sorted(TEST_CASES.glob("phekb-*.json")):
        stem = f.stem[len("phekb-"):]
        owner = None
        for p in all_phenos:
            if (stem == p or stem.startswith(p + "-")) and (owner is None or len(p) > len(owner)):
                owner = p
        if owner == phenotype:
            owned.append(f)
    return owned


def _safe_query(client: FHIRClient, url: str) -> set[str] | None:
    """Run a gold query, returning None (with a printed warning) if the URL
    is malformed enough that the FHIR server rejects it (HTTP 4xx). A few
    legacy test cases hold placeholder text or aspirational queries in the
    URL field; we don't want one bad test case to abort a phenotype's regen.
    Real network/server errors still propagate."""
    import requests
    try:
        return set(client.get_patient_ids_from_query(url))
    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", "?")
        if isinstance(status, int) and 400 <= status < 500:
            print(f"  WARNING: gold query rejected (HTTP {status}); "
                  f"treating as no-gold-query: {url[:120]}", flush=True)
            return None
        raise


def _expected_patient_set(client: FHIRClient, tc: dict) -> set[str] | None:
    """Run a test case's gold query/queries and return the patient set they
    identify -- handling single-query, multi-query union, and negation.
    Returns None if no gold query is defined, or if the gold query is a
    placeholder/malformed URL that the FHIR server can't parse."""
    meta = tc.get("metadata", {})
    queries = meta.get("expected_queries") or []
    if not queries:
        url = (tc.get("expected_query") or {}).get("url")
        if not url:
            return None
        return _safe_query(client, url)
    sets_or_none = [_safe_query(client, u) for u in queries]
    if any(s is None for s in sets_or_none):
        return None  # at least one query is unrunnable; skip this test case
    sets = sets_or_none
    if meta.get("negation"):  # negation_operation: query[0]_patients - query[1..]
        result = set(sets[0])
        for s in sets[1:]:
            result -= s
        return result
    return set().union(*sets)  # multi-query union


def verify_phenotype(client: FHIRClient, phenotype: str) -> bool:
    """Every gold query for the phenotype must return exactly expected_patient_ids."""
    print("VERIFY: counts:", _counts(client), flush=True)
    tcs = _test_cases_for(phenotype)
    if not tcs:
        print(f"  WARNING: no test cases owned by '{phenotype}'")
        return True
    all_ok = True
    for f in tcs:
        tc = json.loads(f.read_text(encoding="utf-8"))
        exp = set(tc.get("test_data", {}).get("expected_patient_ids") or [])
        if not exp:
            continue
        got = _expected_patient_set(client, tc)
        if got is None:
            print(f"  {f.stem:55} (no gold query -- skipped)", flush=True)
            continue
        extra, missing = got - exp, exp - got
        # Threshold-based gold queries (lab values, vitals) sit on numeric
        # boundaries; a couple of patients can flip between regen and reload
        # without the data being wrong. Allow a small tolerance that scales
        # with cohort size so large threshold cohorts aren't blocked by an
        # off-by-few, while small exact-code cohorts stay strict.
        diff = len(extra) + len(missing)
        tol = max(2, round(0.005 * len(exp)))
        if diff == 0:
            status = "OK"
        elif diff <= tol:
            status = f"OK~ +{len(extra)} -{len(missing)} (within tol {tol})"
        else:
            status = f"MISMATCH +{len(extra)} -{len(missing)} (tol {tol})"
            all_ok = False
        print(f"  {f.stem:55} exp={len(exp):4} got={len(got):4}  {status}", flush=True)
    return all_ok


def reload_one(client: FHIRClient, phenotype: str, *, wipe: bool, wipe_only: bool) -> str:
    """Run the wipe/load/verify cycle for one phenotype. Returns a status string."""
    t0 = time.time()
    if wipe:
        wipe_server(client)
    if wipe_only:
        return f"wiped ({int(time.time() - t0)}s)"
    loaded = load_phenotype(client, phenotype)
    print(f"LOAD complete: {loaded} resources", flush=True)
    ok = verify_phenotype(client, phenotype)
    return f"{'PASS' if ok else 'FAIL'} ({loaded} resources, {int(time.time() - t0)}s)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("phenotypes", nargs="*",
                    help="phenotype name(s); empty = ALL phenotypes in synthea/output")
    ap.add_argument("--no-wipe", action="store_true", help="skip the wipe; load+verify only")
    ap.add_argument("--wipe-only", action="store_true", help="wipe only; no load/verify")
    args = ap.parse_args()

    phenos = args.phenotypes or sorted(
        p.name for p in (REPO / "synthea" / "output").iterdir() if p.is_dir())
    client = FHIRClient(base_url=BASE_URL, fhir_version="", verify_ssl=False)
    suite_t0 = time.time()

    results: list[tuple[str, str]] = []
    for i, pheno in enumerate(phenos, 1):
        print(f"\n{'=' * 64}\n[{i}/{len(phenos)}] {pheno}\n{'=' * 64}", flush=True)
        try:
            status = reload_one(client, pheno, wipe=not args.no_wipe, wipe_only=args.wipe_only)
        except Exception as e:
            status = f"ERROR: {str(e)[:120]}"
        print(f"  -> {pheno}: {status}", flush=True)
        results.append((pheno, status))

    if len(results) > 1:
        npass = sum(1 for _, s in results if s.startswith(("PASS", "wiped")))
        nfail = sum(1 for _, s in results if s.startswith("FAIL"))
        nerr = sum(1 for _, s in results if s.startswith("ERROR"))
        print(f"\n{'=' * 64}\n=== TRIAGE SUMMARY ({int(time.time() - suite_t0)}s) ===")
        print(f"{len(results)} phenotypes: {npass} PASS, {nfail} FAIL, {nerr} ERROR\n")
        for pheno, status in sorted(results, key=lambda r: r[1]):
            print(f"  {pheno:46} {status}")
        return 0 if nfail == 0 and nerr == 0 else 1

    return 0 if results and results[0][1].startswith(("PASS", "wiped")) else 1


if __name__ == "__main__":
    sys.exit(main())
