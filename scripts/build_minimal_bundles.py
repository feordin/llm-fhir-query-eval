"""Build minimal per-phenotype FHIR transaction bundles for isolated test runs.

Synthea patient bundles are ~96% resources no test case queries (Claim,
ExplanationOfBenefit, Immunization, DiagnosticReport, DocumentReference,
Provenance, ...). This filters each phenotype's positive+control bundles down
to only the resource types *that phenotype's* test cases query, and rewrites
Synthea's ``urn:uuid:`` references to literal ``ResourceType/id`` form so
references to dropped resources stay harmless (dangling) instead of breaking
the transaction.

Output is a gzipped FHIR transaction Bundle of PUTs (chunked under the server's
transaction-size cap). PUT ``Type/id`` preserves the Synthea UUID as the
resource id, so each test case's ``expected_patient_ids`` stays valid. Gzip
keeps the committed artifacts ~6 MB instead of ~89 MB; a loader just
``gzip.open()``s before POSTing.

Keeping a phenotype's data isolated on the server (load one, test, wipe) is
what eliminates the cross-phenotype contamination found in the shared $import.

Output: ``data/minimal-bundles/<phenotype>.json.gz`` (or
``<phenotype>-NNN.json.gz`` when chunked).

Usage:
    python scripts/build_minimal_bundles.py            # all phenotypes
    python scripts/build_minimal_bundles.py asthma     # just one (or several)
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

# Every FHIR resource type a test case could plausibly reference. Used to
# recognise resource types parsed out of query URLs.
FHIR_TYPES = {
    "Patient", "Condition", "MedicationRequest", "Observation", "Procedure",
    "Encounter", "MedicationStatement", "AllergyIntolerance", "Immunization",
    "DiagnosticReport", "ServiceRequest", "CarePlan", "Goal", "Specimen",
}

# Conservative fallback keep-set: the union of every resource type any test
# case queries. Used for phenotypes whose test cases can't be located.
GLOBAL_KEEP = {
    "Patient", "Condition", "MedicationRequest", "Observation",
    "Procedure", "Encounter", "MedicationStatement", "AllergyIntolerance",
}

REPO = Path(__file__).resolve().parent.parent
SYNTHEA_OUT = REPO / "synthea" / "output"
TEST_CASES = REPO / "test-cases" / "phekb"
DEST = REPO / "data" / "minimal-bundles"


def _types_in_query(url: str) -> set[str]:
    """Extract every FHIR resource type a query URL touches."""
    found: set[str] = set()
    if not url:
        return found
    m = re.match(r"^/?([A-Z][A-Za-z]+)", url)
    if m and m.group(1) in FHIR_TYPES:
        found.add(m.group(1))
    for t in re.findall(r"_has:([A-Z][A-Za-z]+):", url):
        found.add(t)
    for t in re.findall(r"_revinclude=([A-Z][A-Za-z]+):", url):
        found.add(t)
    for src, param in re.findall(r"_include=([A-Z][A-Za-z]+):([a-z\-]+)", url):
        if src in FHIR_TYPES:
            found.add(src)
        if param.capitalize() in FHIR_TYPES:
            found.add(param.capitalize())
        if param == "encounter":
            found.add("Encounter")
    for chained in re.findall(r"[?&]([a-z]+)\.", url):
        if chained.capitalize() in FHIR_TYPES:
            found.add(chained.capitalize())
        if chained == "encounter":
            found.add("Encounter")
    return found


def keep_sets_by_phenotype(pheno_names: set[str]) -> dict[str, set[str]]:
    """Map each phenotype -> the resource types its own test cases query.

    A test case file ``phekb-X.json`` belongs to the phenotype that is the
    LONGEST output-dir name matching ``X`` exactly or as an ``X-...`` prefix,
    so ``phekb-asthma-response-inhaled-steroids-dx`` maps to
    ``asthma-response-inhaled-steroids``, not ``asthma``.
    """
    by_pheno: dict[str, set[str]] = {p: set() for p in pheno_names}
    for f in sorted(TEST_CASES.glob("phekb-*.json")):
        stem = f.stem[len("phekb-"):]
        owner = None
        for p in pheno_names:
            if stem == p or stem.startswith(p + "-"):
                if owner is None or len(p) > len(owner):
                    owner = p
        if owner is None:
            continue
        tc = json.loads(f.read_text(encoding="utf-8"))
        urls = []
        eq = tc.get("expected_query") or {}
        if eq.get("url"):
            urls.append(eq["url"])
        urls += tc.get("metadata", {}).get("expected_queries") or []
        for u in urls:
            by_pheno[owner] |= _types_in_query(u)
    # Always need Patient; fall back to GLOBAL_KEEP if no test cases were found.
    for p in pheno_names:
        by_pheno[p] = (by_pheno[p] | {"Patient"}) if by_pheno[p] else set(GLOBAL_KEEP)
    return by_pheno


def _rewrite_refs(node, id_to_type: dict) -> None:
    """Normalise references so a transaction bundle of only the kept resources loads.

    Synthea uses three reference styles; each must be handled or the transaction
    is rejected:
      * ``urn:uuid:<id>``  -- in-bundle ref; rewrite to literal ``Type/<id>``
                              (or drop if the id isn't known).
      * ``Type?param=...`` -- conditional ref to a cross-bundle resource we drop
                              (Practitioner, Organization); the server can't
                              resolve it, so drop the ``reference`` field. These
                              only appear in optional fields (recorder,
                              requester, serviceProvider, ...), so dropping is safe.
      * ``Type/<id>``      -- already literal; left as-is. A dangling literal ref
                              is harmless -- the server doesn't existence-check it.
    """
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if key == "reference" and isinstance(value, str):
                if value.startswith("urn:uuid:"):
                    uuid = value[len("urn:uuid:"):]
                    rtype = id_to_type.get(uuid)
                    if rtype:
                        node[key] = f"{rtype}/{uuid}"
                    else:
                        del node[key]  # unknown target -- drop dangling urn ref
                elif "?" in value:
                    del node[key]  # conditional ref to a dropped resource
            else:
                _rewrite_refs(value, id_to_type)
    elif isinstance(node, list):
        for item in node:
            _rewrite_refs(item, id_to_type)


# Max entries per transaction bundle. The Microsoft FHIR server caps
# transaction bundles (default 500); chunk well under that.
CHUNK_SIZE = 300


def build_phenotype(pheno_dir: Path, keep_types: set[str]):
    """Return (kept_resources, counts_by_type) for one phenotype's output dir."""
    # Pass 1: map every resource id -> resourceType across all bundles, so refs
    # to dropped resource types can still be rewritten to literal form.
    bundles = []
    id_to_type: dict[str, str] = {}
    for sub in ("positive", "control"):
        fhir_dir = pheno_dir / sub / "fhir"
        if not fhir_dir.is_dir():
            continue
        for f in sorted(fhir_dir.glob("*.json")):
            if "Information" in f.name:  # hospitalInformation / practitionerInformation
                continue
            bundle = json.loads(f.read_text(encoding="utf-8"))
            bundles.append(bundle)
            for entry in bundle.get("entry", []):
                res = entry.get("resource", {})
                rid, rtype = res.get("id"), res.get("resourceType")
                if rid and rtype:
                    id_to_type[rid] = rtype

    # Pass 2: collect + rewrite kept resources, deduped by (type, id).
    kept = []
    seen: set[tuple[str, str]] = set()
    counts: dict[str, int] = {}
    for bundle in bundles:
        for entry in bundle.get("entry", []):
            res = entry.get("resource", {})
            rtype, rid = res.get("resourceType"), res.get("id")
            if rtype not in keep_types:
                continue
            key = (rtype, rid)
            if key in seen:
                continue
            seen.add(key)
            _rewrite_refs(res, id_to_type)
            kept.append(res)
            counts[rtype] = counts.get(rtype, 0) + 1
    return kept, counts


def _transaction_bundle(resources: list[dict]) -> dict:
    """Wrap resources in a FHIR transaction Bundle of PUTs.

    PUT ``Type/id`` upserts with the client-supplied id, so Synthea UUIDs are
    preserved and ``expected_patient_ids`` stays valid.
    """
    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "fullUrl": f"{r['resourceType']}/{r['id']}",
                "resource": r,
                "request": {"method": "PUT", "url": f"{r['resourceType']}/{r['id']}"},
            }
            for r in resources
        ],
    }


def main() -> int:
    only = set(sys.argv[1:]) or None
    DEST.mkdir(parents=True, exist_ok=True)
    pheno_dirs = sorted(p for p in SYNTHEA_OUT.iterdir() if p.is_dir())
    if only:
        pheno_dirs = [p for p in pheno_dirs if p.name in only]
        missing = only - {p.name for p in pheno_dirs}
        if missing:
            print(f"WARNING: no synthea/output dir for: {sorted(missing)}")

    keep_sets = keep_sets_by_phenotype({p.name for p in pheno_dirs})

    grand_resources = 0
    grand_bytes = 0
    grand_files = 0
    built = 0
    for pheno_dir in pheno_dirs:
        keep_types = keep_sets[pheno_dir.name]
        kept, counts = build_phenotype(pheno_dir, keep_types)
        if not kept:
            print(f"  {pheno_dir.name:52} (no kept resources -- skipped)")
            continue

        # Clear any stale chunks for this phenotype, then write fresh ones.
        for stale in DEST.glob(f"{pheno_dir.name}.json.gz"):
            stale.unlink()
        for stale in DEST.glob(f"{pheno_dir.name}-[0-9][0-9][0-9].json.gz"):
            stale.unlink()

        chunks = [kept[i:i + CHUNK_SIZE] for i in range(0, len(kept), CHUNK_SIZE)]
        pheno_bytes = 0
        for idx, chunk in enumerate(chunks, 1):
            name = (f"{pheno_dir.name}.json.gz" if len(chunks) == 1
                    else f"{pheno_dir.name}-{idx:03d}.json.gz")
            text = json.dumps(_transaction_bundle(chunk), separators=(",", ":"))
            data = gzip.compress(text.encode("utf-8"))
            (DEST / name).write_bytes(data)
            pheno_bytes += len(data)
            grand_files += 1

        built += 1
        grand_resources += len(kept)
        grand_bytes += pheno_bytes
        summary = " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        chunk_note = f" [{len(chunks)} bundles]" if len(chunks) > 1 else ""
        print(f"  {pheno_dir.name:52} {len(kept):6} resources{chunk_note}  ({summary})")

    print(f"\n{built} phenotypes -> {grand_files} bundle files, {grand_resources} "
          f"resources, {grand_bytes / 1e6:.1f} MB total in {DEST.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
