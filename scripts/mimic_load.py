"""Wipe one FHIR server and $import the MIMIC demo from the shared blob, verify.

The Azure-config half (RBAC, app settings, restart) is done by the bash driver
setup_mimic_server.sh; this handles the FHIR HTTP half: wipe -> $import (the 13
NDJSON from the fhir-mimic blob container, IncrementalLoad) -> verify Patient count.

Exit 0 on success (Patient count > 0), 1 otherwise -- so the driver can restart+retry.

Usage:  python scripts/mimic_load.py --server jaerwinllm5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))
from src.fhir.client import FHIRClient  # noqa: E402
import reload_phenotype  # noqa: E402  -- wipe_server reads its module-global BASE_URL

BLOB_BASE = "https://jaerwinimport.blob.core.windows.net/fhir-mimic"
FILES = [
    ("MimicOrganization", "Organization"), ("MimicLocation", "Location"),
    ("MimicPatient", "Patient"),
    ("MimicEncounter", "Encounter"), ("MimicEncounterED", "Encounter"),
    ("MimicEncounterICU", "Encounter"),
    ("MimicCondition", "Condition"), ("MimicConditionED", "Condition"),
    ("MimicProcedure", "Procedure"), ("MimicProcedureED", "Procedure"),
    ("MimicProcedureICU", "Procedure"),
    ("MimicObservationED", "Observation"), ("MimicObservationLabevents", "Observation"),
]


def do_import(client: FHIRClient, url: str) -> dict:
    inputs = [{"name": "input", "part": [
        {"name": "type", "valueString": rt},
        {"name": "url", "valueUri": f"{BLOB_BASE}/{fn}.ndjson"}]} for fn, rt in FILES]
    body = {"resourceType": "Parameters", "parameter": [
        {"name": "inputFormat", "valueString": "application/fhir+ndjson"},
        {"name": "mode", "valueString": "IncrementalLoad"}, *inputs]}
    r = client._session.post(f"{url}/$import", json=body,
                             headers={"Prefer": "respond-async", "Content-Type": "application/fhir+json"},
                             timeout=120)
    if r.status_code not in (200, 202):
        return {"status": "post-fail", "code": r.status_code, "text": r.text[:200]}
    loc = r.headers.get("Content-Location")
    t0 = time.time()
    for _ in range(80):
        time.sleep(12)
        s = client._session.get(loc, timeout=60)
        if s.status_code == 200:
            return {"status": "ok", "elapsed": int(time.time() - t0),
                    "output": s.json().get("output", [])}
        if s.status_code == 202:
            continue
        return {"status": "err", "code": s.status_code, "text": s.text[:200]}
    return {"status": "timeout"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    ap.add_argument("--no-wipe", action="store_true")
    args = ap.parse_args()
    url = f"https://{args.server}.azurewebsites.net"
    client = FHIRClient(base_url=url, fhir_version="", verify_ssl=False)

    if not args.no_wipe:
        print(f"  [{args.server}] wiping...", flush=True)
        reload_phenotype.BASE_URL = url  # target THIS server, not the module default
        try:
            reload_phenotype.wipe_server(client)
        except Exception as e:  # noqa: BLE001
            print(f"  [{args.server}] wipe warning: {str(e)[:120]}", flush=True)

    print(f"  [{args.server}] $import...", flush=True)
    res = do_import(client, url)
    if res["status"] != "ok":
        print(f"  [{args.server}] IMPORT FAILED: {res}", flush=True)
        return 1
    counts = {o.get("type"): o.get("count") for o in res["output"]}
    n = client.execute_query("Patient?_summary=count").get("total")
    print(f"  [{args.server}] IMPORT OK ({res['elapsed']}s) {counts}  | Patient count = {n}", flush=True)
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
