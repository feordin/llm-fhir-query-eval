"""Refresh test cases' expected_patient_ids from the live FHIR server.

For each test case in test-cases/phekb/ that belongs to <phenotype>, run its
gold query (or queries, applying union/negation as appropriate) against the
currently-loaded server and write the resulting patient IDs back into the
test case JSON. Use this AFTER reloading the regenerated phenotype's data, so
expected_patient_ids matches the new generation.

Reuses _expected_patient_set semantics from reload_phenotype.py: single
expected_query.url -> patient set; multi-query unions; negation as
query[0] minus query[1..].
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from src.fhir.client import FHIRClient  # noqa: E402
from reload_phenotype import _expected_patient_set, _test_cases_for, BASE_URL  # noqa: E402


def rederive_test_case(client, tc_file: Path) -> bool:
    """Run the test case's gold query/queries; rewrite expected_patient_ids
    if it changed. Returns True iff the file was modified."""
    tc = json.loads(tc_file.read_text(encoding="utf-8"))
    new_ids = _expected_patient_set(client, tc)
    if new_ids is None:  # no gold query at all -- skip
        return False
    new_sorted = sorted(new_ids)
    old_sorted = sorted(tc.get("test_data", {}).get("expected_patient_ids") or [])
    if new_sorted == old_sorted:
        return False
    tc.setdefault("test_data", {})["expected_patient_ids"] = new_sorted
    tc["test_data"]["expected_result_count"] = len(new_sorted)
    tc_file.write_text(json.dumps(tc, indent=2), encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phenotype", help="phenotype dir name (synthea/output/<name>)")
    ap.add_argument("--dry-run", action="store_true",
                    help="show diffs but do not write")
    args = ap.parse_args()

    client = FHIRClient(base_url=BASE_URL, fhir_version="", verify_ssl=False)
    tcs = _test_cases_for(args.phenotype)
    if not tcs:
        print(f"no test cases owned by '{args.phenotype}'")
        return 1

    n_changed = 0
    for f in tcs:
        before = json.loads(f.read_text(encoding="utf-8"))
        before_n = len(before.get("test_data", {}).get("expected_patient_ids") or [])
        if args.dry_run:
            tc = before
            new_ids = _expected_patient_set(client, tc) or set()
            after_n = len(new_ids)
            mark = "" if before_n == after_n else f"  ({before_n} -> {after_n})"
            print(f"  {f.stem:55} would have {after_n} patients{mark}")
            continue
        changed = rederive_test_case(client, f)
        after = json.loads(f.read_text(encoding="utf-8"))
        after_n = len(after.get("test_data", {}).get("expected_patient_ids") or [])
        flag = "UPDATED" if changed else "unchanged"
        print(f"  {f.stem:55} {flag}  ({before_n} -> {after_n})")
        if changed:
            n_changed += 1
    print(f"\n{n_changed} of {len(tcs)} test cases updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
