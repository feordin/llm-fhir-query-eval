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
    python scripts/reload_phenotype.py asthma --no-wipe   # load+verify only
    python scripts/reload_phenotype.py asthma --wipe-only
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
from src.fhir.client import FHIRClient  # noqa: E402

BASE_URL = "https://jaerwinllm.azurewebsites.net"
BUNDLES = REPO / "data" / "minimal-bundles"
TEST_CASES = REPO / "test-cases" / "phekb"
COUNT_TYPES = ["Patient", "Condition", "MedicationRequest", "Observation",
               "Procedure", "Encounter"]


def _counts(client: FHIRClient) -> dict:
    return {t: client.execute_query(f"{t}?_summary=count").get("total") for t in COUNT_TYPES}


def wipe_server(client: FHIRClient, poll_timeout: int = 3600) -> None:
    """Issue $bulk-delete and poll the async job to completion."""
    print("WIPE: issuing $bulk-delete (_hardDelete=true, _purgeHistory=true)...", flush=True)
    # Microsoft FHIR async operations require Prefer: respond-async.
    resp = client._session.delete(
        f"{BASE_URL}/$bulk-delete",
        params={"_hardDelete": "true", "_purgeHistory": "true"},
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


def _expected_patient_set(client: FHIRClient, tc: dict) -> set[str] | None:
    """Run a test case's gold query/queries and return the patient set they
    identify -- handling single-query, multi-query union, and negation."""
    meta = tc.get("metadata", {})
    queries = meta.get("expected_queries") or []
    if not queries:
        url = (tc.get("expected_query") or {}).get("url")
        if not url:
            return None
        return set(client.get_patient_ids_from_query(url))
    sets = [set(client.get_patient_ids_from_query(u)) for u in queries]
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
        status = "OK" if not extra and not missing else f"MISMATCH +{len(extra)} -{len(missing)}"
        if extra or missing:
            all_ok = False
        print(f"  {f.stem:55} exp={len(exp):4} got={len(got):4}  {status}", flush=True)
    return all_ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("phenotype")
    ap.add_argument("--no-wipe", action="store_true", help="skip the wipe; load+verify only")
    ap.add_argument("--wipe-only", action="store_true", help="wipe only; no load/verify")
    args = ap.parse_args()

    client = FHIRClient(base_url=BASE_URL, fhir_version="", verify_ssl=False)
    t0 = time.time()

    if not args.no_wipe:
        print("BEFORE:", _counts(client), flush=True)
        wipe_server(client)
        print("AFTER WIPE:", _counts(client), flush=True)
    if args.wipe_only:
        print(f"\nDONE (wipe only) in {int(time.time()-t0)}s")
        return 0

    loaded = load_phenotype(client, args.phenotype)
    print(f"LOAD complete: {loaded} resources", flush=True)
    ok = verify_phenotype(client, args.phenotype)
    print(f"\n{'PASS' if ok else 'FAIL'} -- {args.phenotype} reload cycle in {int(time.time()-t0)}s")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
