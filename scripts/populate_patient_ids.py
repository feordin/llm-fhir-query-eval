#!/usr/bin/env python3
"""
Populate expected_patient_ids in test case JSON files by scanning Synthea FHIR bundles.

For each test case in test-cases/phekb/ that has empty expected_patient_ids,
this script scans the corresponding Synthea output bundles and determines
which patients match the test case criteria based on resource type and codes.

Usage:
    python scripts/populate_patient_ids.py                    # Process all test cases
    python scripts/populate_patient_ids.py --phenotype asthma # Process one phenotype
    python scripts/populate_patient_ids.py --dry-run          # Show what would change
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


# Project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES_DIR = PROJECT_ROOT / "test-cases" / "phekb"
SYNTHEA_OUTPUT_DIR = PROJECT_ROOT / "synthea" / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate expected_patient_ids in test case JSON files from Synthea bundles."
    )
    parser.add_argument(
        "--phenotype",
        type=str,
        default=None,
        help="Process only test cases for this phenotype (matches against Synthea output dir name).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without modifying files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing patient IDs (by default, only empty lists are populated).",
    )
    return parser.parse_args()


def detect_test_case_type(test_case: dict) -> str:
    """Determine the test case type from filename/id conventions.

    Returns one of: dx, meds, labs, procedures, comprehensive, path4, unknown
    """
    tc_id = test_case["id"]

    if tc_id.endswith("-comprehensive"):
        return "comprehensive"
    if "-path4-" in tc_id:
        return "path4"
    if tc_id.endswith("-dx"):
        return "dx"
    if tc_id.endswith("-meds"):
        return "meds"
    if tc_id.endswith("-labs"):
        return "labs"
    if tc_id.endswith("-procedures"):
        return "procedures"

    # Fall back to expected_query.resource_type
    resource_type = test_case.get("expected_query", {}).get("resource_type", "")
    type_map = {
        "Condition": "dx",
        "MedicationRequest": "meds",
        "Observation": "labs",
        "Procedure": "procedures",
    }
    return type_map.get(resource_type, "unknown")


def get_synthea_dir_from_test_case(test_case: dict) -> Path | None:
    """Extract the Synthea output directory from test_data.resources paths."""
    resources = test_case.get("test_data", {}).get("resources", [])
    for res_path in resources:
        # Paths look like: synthea/output/<phenotype>/positive/fhir/
        full_path = PROJECT_ROOT / res_path
        if full_path.exists():
            # Go up to the phenotype dir (positive/fhir -> positive -> phenotype)
            return full_path.parent.parent
    # Try without the positive/fhir suffix
    for res_path in resources:
        parts = Path(res_path).parts
        # Find "output" in the path and take the next part as phenotype
        for i, part in enumerate(parts):
            if part == "output" and i + 1 < len(parts):
                phenotype_dir = SYNTHEA_OUTPUT_DIR / parts[i + 1]
                if phenotype_dir.exists():
                    return phenotype_dir
    return None


def find_fhir_bundle_dirs(phenotype_dir: Path) -> list[Path]:
    """Find all directories containing FHIR bundle JSON files for a phenotype."""
    dirs = []
    # Check positive/fhir/
    positive_fhir = phenotype_dir / "positive" / "fhir"
    if positive_fhir.exists():
        dirs.append(positive_fhir)
    # Check direct fhir/ (alternate structure)
    direct_fhir = phenotype_dir / "fhir"
    if direct_fhir.exists():
        dirs.append(direct_fhir)
    return dirs


def load_bundle(filepath: Path) -> dict | None:
    """Load a FHIR bundle JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  WARNING: Failed to load {filepath.name}: {e}", file=sys.stderr)
        return None


def get_patient_id(bundle: dict) -> str | None:
    """Extract the Patient resource ID from a bundle."""
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            return resource.get("id")
    return None


def get_resource_codes(resource: dict) -> set[tuple[str, str]]:
    """Extract (system, code) tuples from a FHIR resource's code field.

    Handles:
    - Condition, Observation, Procedure: resource.code.coding[]
    - MedicationRequest: resource.medicationCodeableConcept.coding[]
    """
    codes = set()
    resource_type = resource.get("resourceType", "")

    if resource_type == "MedicationRequest":
        codeable = resource.get("medicationCodeableConcept", {})
    else:
        codeable = resource.get("code", {})

    for coding in codeable.get("coding", []):
        system = coding.get("system", "")
        code = coding.get("code", "")
        if system and code:
            codes.add((system, code))

    return codes


def extract_required_codes(test_case: dict) -> set[tuple[str, str]]:
    """Get the set of (system, code) pairs from metadata.required_codes."""
    codes = set()
    for rc in test_case.get("metadata", {}).get("required_codes", []):
        system = rc.get("system", "")
        code = rc.get("code", "")
        if system and code:
            codes.add((system, code))
    return codes


def get_required_codes_by_resource_type(
    test_case: dict,
) -> dict[str, set[tuple[str, str]]]:
    """Group required_codes by their target FHIR resource type based on code system.

    Returns a dict mapping resource_type -> set of (system, code).
    """
    system_to_resource = {
        "http://snomed.info/sct": None,  # Could be Condition or Procedure
        "http://hl7.org/fhir/sid/icd-10-cm": "Condition",
        "http://www.nlm.nih.gov/research/umls/rxnorm": "MedicationRequest",
        "http://loinc.org": "Observation",
    }

    result: dict[str, set[tuple[str, str]]] = {}

    for rc in test_case.get("metadata", {}).get("required_codes", []):
        system = rc.get("system", "")
        code = rc.get("code", "")
        if not system or not code:
            continue

        resource_type = system_to_resource.get(system)
        if resource_type is None:
            # SNOMED can be either Condition or Procedure; infer from test case
            tc_type = detect_test_case_type(test_case)
            if tc_type == "procedures":
                resource_type = "Procedure"
            else:
                resource_type = "Condition"

        result.setdefault(resource_type, set()).add((system, code))

    return result


def patient_has_matching_resource(
    bundle: dict,
    target_resource_type: str,
    required_codes: set[tuple[str, str]],
) -> bool:
    """Check if a patient bundle contains a resource of the given type with a matching code."""
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") != target_resource_type:
            continue
        resource_codes = get_resource_codes(resource)
        # Check if any required code matches
        if resource_codes & required_codes:
            return True
    return False


def count_matching_resources(
    bundle: dict,
    target_resource_type: str,
    required_codes: set[tuple[str, str]],
) -> int:
    """Count how many resources of the given type match the required codes."""
    count = 0
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") != target_resource_type:
            continue
        resource_codes = get_resource_codes(resource)
        if resource_codes & required_codes:
            count += 1
    return count


def patient_has_no_condition(
    bundle: dict,
    condition_codes: set[tuple[str, str]],
) -> bool:
    """Check that a patient does NOT have a Condition with any of the given codes."""
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") != "Condition":
            continue
        resource_codes = get_resource_codes(resource)
        if resource_codes & condition_codes:
            return False
    return True


def process_test_case(
    test_case_path: Path,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any] | None:
    """Process a single test case file. Returns a summary dict or None if skipped."""
    with open(test_case_path, "r", encoding="utf-8") as f:
        test_case = json.load(f)

    tc_id = test_case["id"]
    existing_ids = test_case.get("test_data", {}).get("expected_patient_ids", [])

    # Skip if already populated (unless --force)
    if existing_ids and not force:
        return {"id": tc_id, "status": "skipped", "reason": "already populated"}

    # Determine test case type
    tc_type = detect_test_case_type(test_case)
    if tc_type == "unknown":
        return {"id": tc_id, "status": "skipped", "reason": f"unknown test case type"}

    # Find Synthea output directory
    phenotype_dir = get_synthea_dir_from_test_case(test_case)
    if phenotype_dir is None:
        return {
            "id": tc_id,
            "status": "skipped",
            "reason": "no Synthea output directory found",
        }

    # Find bundle directories (positive patients only)
    bundle_dirs = find_fhir_bundle_dirs(phenotype_dir)
    if not bundle_dirs:
        return {
            "id": tc_id,
            "status": "skipped",
            "reason": f"no FHIR bundle dirs in {phenotype_dir.name}",
        }

    # Get required codes
    required_codes = extract_required_codes(test_case)
    if not required_codes and tc_type != "comprehensive":
        return {
            "id": tc_id,
            "status": "skipped",
            "reason": "no required_codes in metadata",
        }

    # Determine target resource type from expected_query
    expected_resource_type = test_case.get("expected_query", {}).get(
        "resource_type", ""
    )

    # Build the resource type -> codes mapping for matching
    codes_by_resource = get_required_codes_by_resource_type(test_case)

    # Scan all bundles in positive directories
    matching_patient_ids = []
    total_matching_resources = 0

    for bundle_dir in bundle_dirs:
        for bundle_file in sorted(bundle_dir.glob("*.json")):
            bundle = load_bundle(bundle_file)
            if bundle is None:
                continue

            patient_id = get_patient_id(bundle)
            if patient_id is None:
                continue

            if tc_type == "comprehensive":
                # All positive patients match
                matching_patient_ids.append(patient_id)
            elif tc_type == "path4":
                # Path4: has meds AND labs but NO matching Condition
                # Get the diagnosis codes to exclude (SNOMED T2DM code)
                dx_codes = codes_by_resource.get("Condition", set())
                med_codes = codes_by_resource.get("MedicationRequest", set())
                lab_codes = codes_by_resource.get("Observation", set())

                has_meds = med_codes and patient_has_matching_resource(
                    bundle, "MedicationRequest", med_codes
                )
                has_labs = lab_codes and patient_has_matching_resource(
                    bundle, "Observation", lab_codes
                )
                no_dx = patient_has_no_condition(bundle, dx_codes) if dx_codes else True

                if has_meds and has_labs and no_dx:
                    matching_patient_ids.append(patient_id)
            elif tc_type == "dx":
                dx_codes = codes_by_resource.get("Condition", required_codes)
                if patient_has_matching_resource(bundle, "Condition", dx_codes):
                    matching_patient_ids.append(patient_id)
                    total_matching_resources += count_matching_resources(
                        bundle, "Condition", dx_codes
                    )
            elif tc_type == "meds":
                med_codes = codes_by_resource.get("MedicationRequest", required_codes)
                if patient_has_matching_resource(
                    bundle, "MedicationRequest", med_codes
                ):
                    matching_patient_ids.append(patient_id)
                    total_matching_resources += count_matching_resources(
                        bundle, "MedicationRequest", med_codes
                    )
            elif tc_type == "labs":
                lab_codes = codes_by_resource.get("Observation", required_codes)
                if patient_has_matching_resource(bundle, "Observation", lab_codes):
                    matching_patient_ids.append(patient_id)
                    total_matching_resources += count_matching_resources(
                        bundle, "Observation", lab_codes
                    )
            elif tc_type == "procedures":
                proc_codes = codes_by_resource.get("Procedure", required_codes)
                if patient_has_matching_resource(bundle, "Procedure", proc_codes):
                    matching_patient_ids.append(patient_id)
                    total_matching_resources += count_matching_resources(
                        bundle, "Procedure", proc_codes
                    )

    matching_patient_ids = sorted(set(matching_patient_ids))

    # Determine expected_result_count
    if tc_type == "comprehensive":
        # For comprehensive, count is number of unique patients
        result_count = len(matching_patient_ids)
    elif tc_type == "path4":
        result_count = len(matching_patient_ids)
    else:
        # For single-resource queries, count is number of matching resources
        result_count = total_matching_resources if total_matching_resources > 0 else len(matching_patient_ids)

    # Update the test case
    if not dry_run:
        test_case["test_data"]["expected_patient_ids"] = matching_patient_ids
        test_case["test_data"]["expected_result_count"] = result_count

        with open(test_case_path, "w", encoding="utf-8") as f:
            json.dump(test_case, f, indent=2, ensure_ascii=False)
            f.write("\n")

    return {
        "id": tc_id,
        "status": "updated" if not dry_run else "would update",
        "type": tc_type,
        "phenotype_dir": phenotype_dir.name,
        "patient_count": len(matching_patient_ids),
        "result_count": result_count,
        "patient_ids": matching_patient_ids,
    }


def main():
    args = parse_args()

    if args.dry_run:
        print("=== DRY RUN MODE (no files will be modified) ===\n")

    # Collect test case files
    test_case_files = sorted(TEST_CASES_DIR.glob("phekb-*.json"))
    if not test_case_files:
        print(f"No test case files found in {TEST_CASES_DIR}")
        sys.exit(1)

    # Filter by phenotype if specified
    if args.phenotype:
        phenotype = args.phenotype.lower()
        filtered = []
        for f in test_case_files:
            # Match against filename or check if Synthea dir matches
            if phenotype in f.stem.lower():
                filtered.append(f)
            else:
                # Also check source_id and test_data.resources
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        tc = json.load(fh)
                    resources = tc.get("test_data", {}).get("resources", [])
                    source_id = tc.get("source_id", "")
                    if phenotype in source_id.lower() or any(
                        phenotype in r.lower() for r in resources
                    ):
                        filtered.append(f)
                except (json.JSONDecodeError, IOError):
                    pass
        test_case_files = filtered
        if not test_case_files:
            print(f"No test cases found matching phenotype '{args.phenotype}'")
            sys.exit(1)

    print(f"Processing {len(test_case_files)} test case files...\n")

    results = []
    for tc_file in test_case_files:
        result = process_test_case(tc_file, dry_run=args.dry_run, force=args.force)
        if result:
            results.append(result)

    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    updated = [r for r in results if "update" in r["status"]]
    skipped = [r for r in results if r["status"] == "skipped"]

    if updated:
        print(f"\n{'Updated' if not args.dry_run else 'Would update'} ({len(updated)}):")
        for r in updated:
            print(
                f"  {r['id']:55s} type={r['type']:15s} "
                f"patients={r['patient_count']:3d}  resources={r['result_count']}"
            )
            if args.dry_run and r["patient_ids"]:
                for pid in r["patient_ids"][:5]:
                    print(f"    - {pid}")
                if len(r["patient_ids"]) > 5:
                    print(f"    ... and {len(r['patient_ids']) - 5} more")

    if skipped:
        print(f"\nSkipped ({len(skipped)}):")
        for r in skipped:
            print(f"  {r['id']:55s} reason: {r['reason']}")

    print(f"\nTotal: {len(results)} processed, {len(updated)} {'updated' if not args.dry_run else 'would update'}, {len(skipped)} skipped")


if __name__ == "__main__":
    main()
