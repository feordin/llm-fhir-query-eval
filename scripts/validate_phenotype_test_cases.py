"""Execute test case queries against HAPI FHIR and populate expected_patient_ids.

For each test case in the given list, runs the expected_query.url against HAPI,
collects unique patient IDs from the results, and updates the JSON in-place with:
  - test_data.expected_patient_ids
  - test_data.expected_result_count

For multi_query test cases, executes all queries in metadata.expected_queries and
unions the patient IDs.

Patient IDs come from Synthea bundles (stable UUIDs) by mapping HAPI Patient/<id>
references back to the Patient.identifier.value (Synthea UUID) in the bundle.
"""
import json
import sys
import urllib.parse
from pathlib import Path

import requests

FHIR_BASE = "http://localhost:8080/fhir"
TEST_CASE_DIR = Path("test-cases/phekb")


def get_synthea_uuid_for_hapi_patient(hapi_patient_id: str, cache: dict) -> str | None:
    """Look up the stable Synthea UUID from a HAPI patient ID."""
    if hapi_patient_id in cache:
        return cache[hapi_patient_id]
    r = requests.get(f"{FHIR_BASE}/Patient/{hapi_patient_id}")
    if r.status_code != 200:
        cache[hapi_patient_id] = None
        return None
    p = r.json()
    # Synthea stamps Patient.identifier with a "https://github.com/synthetichealth/synthea" system
    for ident in p.get("identifier", []):
        if ident.get("system") == "https://github.com/synthetichealth/synthea":
            cache[hapi_patient_id] = ident.get("value")
            return ident.get("value")
    cache[hapi_patient_id] = None
    return None


def fetch_patient_ids_for_query(query_path: str, cache: dict) -> set[str]:
    """Run a FHIR query, walk pagination, return set of stable Synthea UUIDs of patients."""
    patient_ids: set[str] = set()
    # Bump page count to reduce pagination
    url = f"{FHIR_BASE}/{query_path}&_count=200" if "?" in query_path else f"{FHIR_BASE}/{query_path}?_count=200"
    pages = 0
    while url and pages < 20:
        pages += 1
        r = requests.get(url)
        if r.status_code != 200:
            print(f"    HTTP {r.status_code} on {url[:120]}", file=sys.stderr)
            break
        bundle = r.json()
        for entry in bundle.get("entry", []):
            res = entry.get("resource", {})
            rt = res.get("resourceType")
            # Extract patient reference
            patient_ref = None
            if rt == "Patient":
                patient_ref = res.get("id")
            elif rt in ("Condition", "MedicationRequest", "Observation", "Procedure"):
                subject = res.get("subject", {}) or res.get("patient", {})
                ref = subject.get("reference", "")
                if ref.startswith("Patient/"):
                    patient_ref = ref.split("/", 1)[1]
            if patient_ref:
                synthea_uuid = get_synthea_uuid_for_hapi_patient(patient_ref, cache)
                if synthea_uuid:
                    patient_ids.add(synthea_uuid)
        # Check for next page
        next_url = None
        for link in bundle.get("link", []):
            if link.get("relation") == "next":
                next_url = link.get("url")
                break
        url = next_url
    return patient_ids


def get_phenotype_dx_query(phenotype: str) -> str | None:
    """Look up the corresponding -dx test case to get the SNOMED dx codes."""
    dx_path = TEST_CASE_DIR / f"phekb-{phenotype}-dx.json"
    if not dx_path.exists():
        return None
    with open(dx_path, encoding="utf-8") as f:
        dx_tc = json.load(f)
    return dx_tc["expected_query"]["url"]


def get_phenotype_meds_query(phenotype: str) -> str | None:
    """Look up the corresponding -meds test case to get the RxNorm med codes."""
    meds_path = TEST_CASE_DIR / f"phekb-{phenotype}-meds.json"
    if not meds_path.exists():
        return None
    with open(meds_path, encoding="utf-8") as f:
        meds_tc = json.load(f)
    return meds_tc["expected_query"]["url"]


def validate_test_case(tc_path: Path, cache: dict) -> dict:
    """Run the test case query and return updated test data + report."""
    with open(tc_path, encoding="utf-8") as f:
        tc = json.load(f)

    tc_id = tc.get("id", "")
    phenotype = tc.get("source_id", "")
    is_multi = tc.get("metadata", {}).get("multi_query", False)
    is_meds_only = "-meds-only" in tc_id
    is_labs_only = "-labs-only" in tc_id

    if is_multi:
        queries = tc["metadata"]["expected_queries"]
    else:
        queries = [tc["expected_query"]["url"]]

    all_patient_ids: set[str] = set()
    for q in queries:
        ids = fetch_patient_ids_for_query(q, cache)
        all_patient_ids |= ids
        print(f"    Query: {q[:100]}...  -> {len(ids)} patients")

    # For meds-only: exclude patients with the dx
    # For labs-only: exclude patients with the dx AND patients with the meds
    if is_meds_only or is_labs_only:
        dx_query = get_phenotype_dx_query(phenotype)
        if dx_query:
            dx_patients = fetch_patient_ids_for_query(dx_query, cache)
            print(f"    Excluding {len(dx_patients)} patients with diagnosis")
            all_patient_ids -= dx_patients
    if is_labs_only:
        meds_query = get_phenotype_meds_query(phenotype)
        if meds_query:
            meds_patients = fetch_patient_ids_for_query(meds_query, cache)
            print(f"    Excluding {len(meds_patients)} patients with meds")
            all_patient_ids -= meds_patients

    # Update test data
    sorted_ids = sorted(all_patient_ids)
    tc["test_data"]["expected_patient_ids"] = sorted_ids
    tc["test_data"]["expected_result_count"] = len(sorted_ids)
    tc["updated_at"] = "2026-04-27T00:00:00.000000Z"

    with open(tc_path, "w", encoding="utf-8") as f:
        json.dump(tc, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return {"id": tc["id"], "patient_count": len(sorted_ids), "queries_run": len(queries)}


def main():
    phenotypes = sys.argv[1:] if len(sys.argv) > 1 else ["hypothyroidism", "dementia", "depression"]
    cache: dict = {}
    results = []

    for phen in phenotypes:
        print(f"\n=== {phen.upper()} ===")
        for tc_path in sorted(TEST_CASE_DIR.glob(f"phekb-{phen}-*.json")):
            print(f"  {tc_path.name}")
            try:
                report = validate_test_case(tc_path, cache)
                results.append(report)
                print(f"    -> {report['patient_count']} expected patients across {report['queries_run']} queries")
            except Exception as e:
                print(f"    ERROR: {e}", file=sys.stderr)
                results.append({"id": tc_path.stem, "error": str(e)})

    print("\n=== SUMMARY ===")
    for r in results:
        if "error" in r:
            print(f"  FAIL {r['id']}: {r['error']}")
        else:
            print(f"  OK   {r['id']:50s} -> {r['patient_count']:3d} patients ({r['queries_run']} qry)")


if __name__ == "__main__":
    main()
