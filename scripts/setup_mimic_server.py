"""Configure ONE Microsoft FHIR App Service for $import and load the MIMIC demo.

Automates the recipe validated on jaerwinllm4 (see docs/MIMIC-IMPORT-RUNBOOK.md):
  1. grant BOTH the system + user managed identity Storage Blob Data Contributor
     on the storage account (the server picks one; granting both is safe);
  2. set app settings: Import enabled, IncrementalLoad (InitialImportMode=false so
     the server stays queryable), IntegrationDataStore -> storage, TaskHosting=6;
  3. wait for RBAC propagation, then RESTART (clears the server's cached blob-auth
     -- this was the crux: the import 403s until a restart after the grant);
  4. wipe (bulk-delete works because InitialImportMode=false);
  5. $import the 13 MIMIC NDJSON from the shared blob container (IncrementalLoad);
  6. verify Patient count.

az operations are retried because the PIM-activated Contributor role propagates
inconsistently across ARM replicas (intermittent AuthorizationFailed).

Usage:
    python scripts/setup_mimic_server.py --server jaerwinllm5
    python scripts/setup_mimic_server.py --server jaerwinllm5 --skip-import  # config+RBAC only
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))
from src.fhir.client import FHIRClient  # noqa: E402
from reload_phenotype import wipe_server  # noqa: E402

SUB = "11a09cd2-9add-4367-9951-bbe32d977d66"
STORAGE = "jaerwinimport"
STORAGE_ID = (f"/subscriptions/{SUB}/resourceGroups/jaerwinllm/providers/"
              f"Microsoft.Storage/storageAccounts/{STORAGE}")
ROLE_BLOB = "ba92f5b4-2d11-453d-a403-e96b0029c9fe"  # Storage Blob Data Contributor
BLOB_BASE = f"https://{STORAGE}.blob.core.windows.net/fhir-mimic"
FILES = [  # (filename-stem, resourceType), MS-FHIR load order
    ("MimicOrganization", "Organization"), ("MimicLocation", "Location"),
    ("MimicPatient", "Patient"),
    ("MimicEncounter", "Encounter"), ("MimicEncounterED", "Encounter"),
    ("MimicEncounterICU", "Encounter"),
    ("MimicCondition", "Condition"), ("MimicConditionED", "Condition"),
    ("MimicProcedure", "Procedure"), ("MimicProcedureED", "Procedure"),
    ("MimicProcedureICU", "Procedure"),
    ("MimicObservationED", "Observation"), ("MimicObservationLabevents", "Observation"),
]


def az(args: list, retries: int = 5, ok_empty: bool = False) -> str:
    """Run an `az` command, retrying transient PIM/ARM AuthorizationFailed."""
    last = ""
    for i in range(retries):
        r = subprocess.run(["az", *args], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip()
        last = (r.stderr or r.stdout)[:200]
        if ("AuthorizationFailed" in last or "MissingSubscription" in last) and i < retries - 1:
            time.sleep(20)
            continue
        break
    raise RuntimeError(f"az {' '.join(args[:3])}... failed: {last}")


def grant_blob_role(principal: str, label: str) -> None:
    guid = str(uuid.uuid4())
    body = {"properties": {
        "roleDefinitionId": f"/subscriptions/{SUB}/providers/Microsoft.Authorization/roleDefinitions/{ROLE_BLOB}",
        "principalId": principal, "principalType": "ServicePrincipal"}}
    url = (f"https://management.azure.com{STORAGE_ID}/providers/Microsoft.Authorization/"
           f"roleAssignments/{guid}?api-version=2022-04-01")
    try:
        az(["rest", "--method", "put", "--url", url, "--body", json.dumps(body)])
        print(f"  granted blob role to {label} ({principal[:8]})", flush=True)
    except RuntimeError as e:
        if "RoleAssignmentExists" in str(e):
            print(f"  {label} already has blob role", flush=True)
        else:
            raise


def wait_health(url: str, timeout: int = 240) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = subprocess.run(["curl", "-sk", "-o", "/dev/null", "-w", "%{http_code}",
                            "--max-time", "15", f"{url}/metadata"], capture_output=True, text=True)
        if r.stdout.strip() == "200":
            return
        time.sleep(10)
    print(f"  WARN: {url} not healthy after {timeout}s", flush=True)


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
    for _ in range(60):
        time.sleep(12)
        s = client._session.get(loc, timeout=60)
        if s.status_code == 200:
            return {"status": "ok", "elapsed": int(time.time() - t0), "output": s.json().get("output", [])}
        if s.status_code == 202:
            continue
        return {"status": "err", "code": s.status_code, "text": s.text[:200]}
    return {"status": "timeout"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    ap.add_argument("--skip-import", action="store_true")
    ap.add_argument("--prop-wait", type=int, default=180, help="RBAC propagation wait (s)")
    args = ap.parse_args()
    srv = args.server
    rg = srv
    url = f"https://{srv}.azurewebsites.net"
    print(f"=== setup {srv} ===", flush=True)

    az(["account", "set", "--subscription", SUB])
    sys_p = az(["webapp", "identity", "show", "-g", rg, "-n", srv, "--query", "principalId", "-o", "tsv"])
    user_p = az(["identity", "show", "-g", rg, "-n", f"{srv}-uami", "--query", "principalId", "-o", "tsv"])
    grant_blob_role(sys_p, "system-MI")
    grant_blob_role(user_p, "user-MI")

    az(["webapp", "config", "appsettings", "set", "-g", rg, "-n", srv, "--settings",
        "FhirServer__Operations__Import__Enabled=true",
        "FhirServer__Operations__Import__InitialImportMode=false",
        f"FhirServer__Operations__IntegrationDataStore__StorageAccountUri=https://{STORAGE}.blob.core.windows.net",
        "TaskHosting__Enabled=true", "TaskHosting__MaxRunningTaskCount=6", "-o", "none"])
    print("  app settings set; waiting %ds for RBAC propagation..." % args.prop_wait, flush=True)
    time.sleep(args.prop_wait)
    az(["webapp", "restart", "-g", rg, "-n", srv])
    print("  restarted; waiting for health...", flush=True)
    wait_health(url)

    if args.skip_import:
        print("  --skip-import: config+RBAC done.", flush=True)
        return 0

    client = FHIRClient(base_url=url, fhir_version="", verify_ssl=False)
    print("  wiping...", flush=True)
    try:
        wipe_server(client)
    except Exception as e:  # noqa: BLE001
        print(f"  wipe warning: {str(e)[:120]}", flush=True)

    for attempt in range(1, 4):
        res = do_import(client, url)
        if res["status"] == "ok":
            counts = {o.get("type"): o.get("count") for o in res["output"]}
            print(f"  IMPORT OK ({res['elapsed']}s): {counts}", flush=True)
            break
        blob_403 = res.get("code") == 403 or "blob" in res.get("text", "").lower()
        print(f"  import attempt {attempt} -> {res}", flush=True)
        if attempt < 3 and blob_403:
            print("  blob 403 -> restart + wait + retry", flush=True)
            az(["webapp", "restart", "-g", rg, "-n", srv])
            wait_health(url)
            time.sleep(60)
        else:
            print(f"  IMPORT FAILED on {srv}", flush=True)
            return 1

    n = client.execute_query("Patient?_summary=count").get("total")
    print(f"  VERIFY {srv}: Patient count = {n}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
