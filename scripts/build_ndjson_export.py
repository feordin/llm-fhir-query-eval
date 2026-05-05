"""Build NDJSON shards for Microsoft FHIR `$import` from Synthea bundles.

Walks every bundle under `synthea/output/<phenotype>/{positive,control}/fhir/*.json`,
groups resources by resourceType, and writes one NDJSON file per resource type
(one resource per line, no wrapping array).

Output: `data/ndjson-export/<ResourceType>.ndjson`

Microsoft FHIR `$import` recommended load order:
  1. Foundation: Practitioner, Location, Organization, PractitionerRole
  2. Patient
  3. Encounter
  4. Everything else

This script writes them all; you load them in order against the cloud server.

Usage:
    python scripts/build_ndjson_export.py
    python scripts/build_ndjson_export.py --resource-types Practitioner,Location  # subset only
    python scripts/build_ndjson_export.py --output-dir data/ndjson-export
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Synthea bundles use `urn:uuid:<uuid>` for in-bundle references. Those only
# resolve during transaction-bundle processing; via $import they would be
# stored verbatim and break every cross-resource search. We rewrite them to
# `<ResourceType>/<uuid>` (relative literal references) before emitting NDJSON.
URN_UUID_RE = re.compile(
    r"urn:uuid:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)

REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO / "data" / "ndjson-export"

# Recommended load order for $import (referential dependencies)
LOAD_ORDER = [
    # Foundation — load first
    "Organization",
    "Location",
    "Practitioner",
    "PractitionerRole",
    # Patient core
    "Patient",
    # Encounter (references Patient + Practitioner + Location)
    "Encounter",
    # Clinical resources (reference Patient + Encounter)
    "Condition",
    "Procedure",
    "Observation",
    "MedicationRequest",
    "MedicationAdministration",
    "AllergyIntolerance",
    "Immunization",
    "DiagnosticReport",
    "DocumentReference",
    "ImagingStudy",
    "CarePlan",
    "CareTeam",
    "Goal",
    "Claim",
    "ExplanationOfBenefit",
    "Provenance",
    "SupplyDelivery",
    "Device",
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT),
                   help=f"NDJSON output dir (default: {DEFAULT_OUTPUT})")
    p.add_argument("--resource-types", default=None,
                   help="Comma-separated resource types to emit (default: all)")
    p.add_argument("--only-phenotypes", default=None,
                   help="Comma-separated phenotype slugs (default: all)")
    args = p.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    target_types = None
    if args.resource_types:
        target_types = set(args.resource_types.split(","))

    target_phenotypes = None
    if args.only_phenotypes:
        target_phenotypes = set(args.only_phenotypes.split(","))

    synthea_root = REPO / "synthea" / "output"
    if not synthea_root.exists():
        sys.exit(f"No Synthea output found at {synthea_root}")

    # Collect bundle files
    bundle_files = []
    for phen_dir in sorted(p for p in synthea_root.iterdir() if p.is_dir()):
        if target_phenotypes and phen_dir.name not in target_phenotypes:
            continue
        for sub in ("positive", "control"):
            d = phen_dir / sub / "fhir"
            if d.is_dir():
                bundle_files.extend(sorted(d.glob("*.json")))
    print(f"Found {len(bundle_files)} bundles to process")

    # ---- Pass 1: build a uuid -> resourceType map across ALL bundles ----
    # The map must be complete before we rewrite references, because a
    # reference in (say) an Encounter may point at a Patient in a different
    # bundle's PractitionerRole, etc. (Synthea also emits referenced
    # Practitioners/Organizations/Locations once per bundle.) We don't apply
    # the --resource-types filter here — references can still point at types
    # we won't emit (e.g. Encounter -> Practitioner), and we want those
    # rewrites to land correctly even if the target file isn't kept.
    uuid_to_type: dict[str, str] = {}
    print("Pass 1: building uuid -> resourceType map")
    for i, path in enumerate(bundle_files, 1):
        if i % 1000 == 0:
            print(f"  ...{i}/{len(bundle_files)} bundles  (map size {len(uuid_to_type):,})")
        try:
            with path.open(encoding="utf-8") as f:
                bundle = json.load(f)
        except Exception as e:
            print(f"  WARN: failed to read {path.name}: {e}")
            continue
        for entry in bundle.get("entry", []):
            r = entry.get("resource", {})
            rid = r.get("id")
            rtype = r.get("resourceType")
            if rid and rtype:
                uuid_to_type[rid] = rtype
    print(f"  uuid map complete: {len(uuid_to_type):,} entries")

    # ---- Pass 2: stream per-type NDJSON with rewritten references ----
    seen_ids: dict[str, set[str]] = defaultdict(set)
    counts: dict[str, int] = defaultdict(int)
    duplicates: dict[str, int] = defaultdict(int)
    refs_rewritten = 0
    refs_unmapped = 0
    out_handles: dict[str, "object"] = {}

    def _ref_repl(m: "re.Match[str]") -> str:
        nonlocal refs_rewritten, refs_unmapped
        uuid = m.group(1)
        target_rtype = uuid_to_type.get(uuid)
        if target_rtype:
            refs_rewritten += 1
            return f"{target_rtype}/{uuid}"
        refs_unmapped += 1
        return m.group(0)

    print("\nPass 2: writing NDJSON with reference rewrite")
    for i, path in enumerate(bundle_files, 1):
        if i % 1000 == 0:
            print(f"  ...{i}/{len(bundle_files)} bundles")
        try:
            with path.open(encoding="utf-8") as f:
                bundle = json.load(f)
        except Exception as e:
            print(f"  WARN: failed to read {path.name}: {e}")
            continue
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            rtype = resource.get("resourceType")
            rid = resource.get("id")
            if not rtype or not rid:
                continue
            if target_types and rtype not in target_types:
                continue
            if rid in seen_ids[rtype]:
                duplicates[rtype] += 1
                continue
            seen_ids[rtype].add(rid)
            line = json.dumps(resource, separators=(",", ":"))
            line = URN_UUID_RE.sub(_ref_repl, line)
            handle = out_handles.get(rtype)
            if handle is None:
                handle = (out_dir / f"{rtype}.ndjson").open("w", encoding="utf-8")
                out_handles[rtype] = handle
            handle.write(line)
            handle.write("\n")
            counts[rtype] += 1

    for handle in out_handles.values():
        handle.close()

    print(f"\nNDJSON shards in {out_dir}")
    for rtype, _ in sorted(((r, c) for r, c in counts.items())):
        out_path = out_dir / f"{rtype}.ndjson"
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"  {rtype:25s} {counts[rtype]:>8d} resources  {size_mb:>8.1f} MB"
              f"  ({duplicates[rtype]} dedup'd)")
    print(f"\nReferences rewritten: {refs_rewritten:,}"
          f"  unmapped: {refs_unmapped:,} (left as urn:uuid: — likely outside-bundle pointers)")

    # Summary in load order
    print(f"\nRecommended $import load order:")
    for i, rtype in enumerate(LOAD_ORDER, 1):
        if rtype in counts:
            print(f"  {i:2d}. {rtype:25s} ({counts[rtype]} resources)")
    other = [r for r in counts if r not in LOAD_ORDER]
    for i, rtype in enumerate(other, len(LOAD_ORDER) + 1):
        print(f"  {i:2d}. {rtype:25s} ({counts[rtype]} resources) [no defined dependency]")

    print(f"\nTotal resources written: {sum(counts.values()):,}")
    print(f"Output dir: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
