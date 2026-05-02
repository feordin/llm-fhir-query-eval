"""
Augment Synthea FHIR Bundle output with additional code system crosswalks.

Synthea's FHIR exporter only emits the FIRST coding from a Synthea module's
`codes` array per resource. This script post-processes the generated Bundles
to add additional codings (ICD-9/ICD-10/CPT/etc.) to Conditions, Procedures,
Observations, and MedicationRequests, based on a SNOMED-keyed crosswalk map.

This implements the PheKB-doc-first principle for the Tier 1 revision sweep:
real-world EHR data uses multiple code systems on the same clinical concept,
and our test data should reflect that.

Workflow:
  synthea generate -> augment_fhir_codes.py -> fhir-eval load -> validate

Usage:
  # Augment all phenotype outputs:
  python scripts/augment_fhir_codes.py

  # Augment a specific phenotype:
  python scripts/augment_fhir_codes.py --phenotype abdominal-aortic-aneurysm

  # Dry-run (count changes, don't write):
  python scripts/augment_fhir_codes.py --phenotype abdominal-aortic-aneurysm --dry-run

The crosswalk map lives at data/code_augmentations.json and is keyed by
the SNOMED code that Synthea emits. Idempotent: re-running won't duplicate
codings.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAP_PATH = REPO / "data" / "code_augmentations.json"
OUTPUT_ROOT = REPO / "synthea" / "output"

AUGMENTABLE_RESOURCES = {"Condition", "Procedure", "Observation", "MedicationRequest", "AllergyIntolerance"}


def load_map() -> dict:
    if not MAP_PATH.exists():
        sys.exit(f"Crosswalk map not found at {MAP_PATH}. Build it first.")
    with MAP_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def existing_codes(coding_list: list[dict]) -> set[tuple[str, str]]:
    return {(c.get("system", ""), c.get("code", "")) for c in coding_list}


def augment_resource(resource: dict, crosswalk: dict, stats: dict) -> bool:
    """Augment a single resource's code.coding list. Returns True if modified."""
    if resource.get("resourceType") not in AUGMENTABLE_RESOURCES:
        return False
    code_field = resource.get("code") or resource.get("medicationCodeableConcept")
    if not code_field or "coding" not in code_field:
        return False
    coding_list = code_field["coding"]
    existing = existing_codes(coding_list)
    modified = False
    for coding in list(coding_list):
        code = coding.get("code")
        if code and code in crosswalk:
            for additional in crosswalk[code]:
                key = (additional["system"], additional["code"])
                if key in existing:
                    continue
                coding_list.append(additional)
                existing.add(key)
                modified = True
                stats["codings_added"] += 1
    if modified:
        stats["resources_modified"] += 1
    return modified


def augment_bundle(path: Path, crosswalk: dict, stats: dict, dry_run: bool) -> bool:
    with path.open(encoding="utf-8") as f:
        bundle = json.load(f)
    any_modified = False
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if augment_resource(resource, crosswalk, stats):
            any_modified = True
    if any_modified and not dry_run:
        with path.open("w", encoding="utf-8") as f:
            json.dump(bundle, f, indent=2)
        stats["files_modified"] += 1
    return any_modified


def discover_bundle_dirs(phenotype: str | None) -> list[Path]:
    if phenotype:
        targets = [OUTPUT_ROOT / phenotype]
    else:
        targets = [p for p in OUTPUT_ROOT.iterdir() if p.is_dir()]
    dirs = []
    for t in targets:
        for sub in ("positive", "control"):
            d = t / sub / "fhir"
            if d.is_dir():
                dirs.append(d)
    return dirs


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--phenotype", help="Specific phenotype to augment (default: all)")
    p.add_argument("--dry-run", action="store_true", help="Count changes without writing")
    args = p.parse_args()

    crosswalk = load_map()
    print(f"Loaded {len(crosswalk)} SNOMED-keyed crosswalk entries from {MAP_PATH.name}")

    bundle_dirs = discover_bundle_dirs(args.phenotype)
    if not bundle_dirs:
        sys.exit(f"No FHIR output dirs found for phenotype={args.phenotype}")

    stats = {"files_scanned": 0, "files_modified": 0, "resources_modified": 0, "codings_added": 0}
    for d in bundle_dirs:
        bundles = sorted(d.glob("*.json"))
        for path in bundles:
            stats["files_scanned"] += 1
            augment_bundle(path, crosswalk, stats, args.dry_run)

    print()
    print(f"Files scanned:        {stats['files_scanned']}")
    print(f"Files modified:       {stats['files_modified']}{' (dry-run)' if args.dry_run else ''}")
    print(f"Resources modified:   {stats['resources_modified']}")
    print(f"Codings added:        {stats['codings_added']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
