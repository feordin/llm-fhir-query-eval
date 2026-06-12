"""Invoke Microsoft FHIR `$import` to bulk-load standardized MIMIC NDJSON from blob.

Builds the `Parameters` body (InitialLoad mode) from the NDJSON files staged in a
blob container, POSTs `$import` async, and polls to completion. Loads in the
Microsoft-recommended order: foundation -> Patient -> Encounter -> clinical.

Prereqs (see docs/MIMIC-IMPORT-RUNBOOK.md): the server has Import enabled,
IntegrationDataStore pointed at the storage account, TaskHosting MaxRunningTaskCount
>= 6, and the FHIR service's managed identity has Storage Blob Data access. The
server should be EMPTY (use reload_phenotype.py --wipe-only first).

Usage:
    python scripts/mimic_import.py \
        --fhir-url https://jaerwinllm.azurewebsites.net \
        --blob-base https://jaerwinimport.blob.core.windows.net/fhir-mimic \
        --ndjson-dir data/mimic-standardized
    # --dry-run prints the body without POSTing.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
from src.fhir.client import FHIRClient  # noqa: E402

# Microsoft FHIR $import recommended load order. A file is included only if it
# exists in --ndjson-dir; its resource type is the filename stem.
LOAD_ORDER = [
    "Organization", "Location", "Practitioner", "PractitionerRole",
    "Patient", "Encounter",
    "Condition", "Procedure", "Observation", "MedicationRequest", "Medication",
]


def _resource_type(stem: str) -> str:
    """Map an NDJSON filename stem to its FHIR resource type.

    The standardizer emits MIMIC-style names (MimicCondition, MimicObservationLabevents);
    build_ndjson_export emits plain types (Condition). Normalize both."""
    s = stem
    if s.startswith("Mimic"):
        s = s[len("Mimic"):]
    for rt in LOAD_ORDER:
        if s == rt or s.startswith(rt):
            return rt
    return s


def build_import_body(ndjson_dir: Path, blob_base: str, mode: str = "IncrementalLoad") -> dict:
    """One `input` part per NDJSON file, ordered by LOAD_ORDER then name.

    mode: 'IncrementalLoad' (default, VALIDATED) keeps the server queryable and
    requires Import__InitialImportMode=false. 'InitialLoad' is faster but locks the
    server read-only (Import__InitialImportMode=true must be set) -- not what the
    eval wants, since it must query the data afterward.
    """
    files = sorted(ndjson_dir.glob("*.ndjson"))
    if not files:
        sys.exit(f"no .ndjson files in {ndjson_dir}")
    order = {rt: i for i, rt in enumerate(LOAD_ORDER)}
    files.sort(key=lambda p: (order.get(_resource_type(p.stem), 99), p.name))
    inputs = []
    for f in files:
        rt = _resource_type(f.stem)
        inputs.append({"name": "input", "part": [
            {"name": "type", "valueString": rt},
            {"name": "url", "valueUri": f"{blob_base.rstrip('/')}/{f.name}"},
        ]})
    return {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "inputFormat", "valueString": "application/fhir+ndjson"},
            {"name": "mode", "valueString": mode},
            *inputs,
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fhir-url", required=True)
    ap.add_argument("--blob-base", required=True,
                    help="blob container base URL, e.g. https://acct.blob.core.windows.net/fhir-mimic")
    ap.add_argument("--ndjson-dir", default="data/mimic-standardized")
    ap.add_argument("--mode", default="IncrementalLoad",
                    choices=["IncrementalLoad", "InitialLoad"],
                    help="IncrementalLoad (default, server stays queryable, needs "
                         "Import__InitialImportMode=false) or InitialLoad (faster, "
                         "locks server, needs InitialImportMode=true).")
    ap.add_argument("--poll-timeout", type=int, default=7200)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    body = build_import_body(Path(args.ndjson_dir), args.blob_base, args.mode)
    n = sum(1 for p in body["parameter"] if p["name"] == "input")
    print(f"$import body: {n} input files, mode=InitialLoad", flush=True)
    for p in body["parameter"]:
        if p["name"] == "input":
            t = next(x["valueString"] for x in p["part"] if x["name"] == "type")
            u = next(x["valueUri"] for x in p["part"] if x["name"] == "url")
            print(f"  {t:18} {u}")
    if args.dry_run:
        print("\n--dry-run: not POSTing.")
        return 0

    client = FHIRClient(base_url=args.fhir_url, fhir_version="", verify_ssl=False)
    resp = client._session.post(
        f"{args.fhir_url.rstrip('/')}/$import",
        json=body,
        headers={"Prefer": "respond-async", "Content-Type": "application/fhir+json"},
        timeout=120,
    )
    print(f"POST $import -> HTTP {resp.status_code}", flush=True)
    if resp.status_code not in (202, 200):
        sys.exit(f"$import not accepted: {resp.status_code} {resp.text[:500]}")
    status_url = resp.headers.get("Content-Location")
    if not status_url:
        sys.exit(f"no Content-Location to poll; headers={dict(resp.headers)}")
    print(f"polling: {status_url}", flush=True)
    t0 = time.time()
    while True:
        time.sleep(20)
        s = client._session.get(status_url, timeout=60)
        el = int(time.time() - t0)
        if s.status_code == 200:
            try:
                out = s.json().get("output", s.json())
            except Exception:
                out = s.text[:300]
            print(f"$import COMPLETE after {el}s: {json.dumps(out)[:500]}", flush=True)
            return 0
        if s.status_code == 202:
            print(f"  ...{el}s: {s.headers.get('X-Progress', 'running')}", flush=True)
        else:
            sys.exit(f"poll failed: HTTP {s.status_code} {s.text[:300]}")
        if time.time() - t0 > args.poll_timeout:
            sys.exit(f"$import did not finish within {args.poll_timeout}s")


if __name__ == "__main__":
    sys.exit(main())
