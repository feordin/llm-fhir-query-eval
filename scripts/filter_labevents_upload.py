"""Filter standardized MIMIC labevents to phenotype-criteria LOINCs, in chunks.

Full MIMIC labevents is 118M rows / 151 GB -- too heavy to $import wholesale.
The eval only *scores* lab paths on the LOINCs referenced by phenotype criteria
(criteria_loinc_union), so keep every Observation whose code.coding carries one
of those LOINCs and drop the rest. Output is written as ~chunk-bytes NDJSON
parts (MimicObservationLabevents_partNN.ndjson) sized for parallel $import.

Lines are written unchanged (already standardized). A compiled alternation
regex pre-filters candidates; each candidate is JSON-confirmed so a stray
matching string elsewhere in the resource can't leak rows in.

Usage:
    python scripts/filter_labevents_upload.py \
        --input .../fhir-standardized/MimicObservationLabevents.ndjson \
        --output-dir .../upload [--chunk-bytes 1900000000]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from mimic_phenotype_counts import PHENOTYPES, criteria_loinc_union  # noqa: E402

LOINC = "http://loinc.org"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--chunk-bytes", type=int, default=1_900_000_000)
    args = ap.parse_args(argv)

    loincs = criteria_loinc_union(PHENOTYPES)
    print(f"filtering to {len(loincs)} criteria LOINCs", flush=True)
    pre = re.compile("|".join(f'"{re.escape(c)}"' for c in sorted(loincs)))

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    part, part_bytes, fout = 0, 0, None

    def open_part():
        nonlocal fout, part, part_bytes
        if fout:
            fout.close()
        p = out_dir / f"MimicObservationLabevents_part{part:02d}.ndjson"
        fout = p.open("w", encoding="utf-8")
        part += 1
        part_bytes = 0

    open_part()
    total = kept = 0
    with open(args.input, encoding="utf-8") as fin:
        for line in fin:
            total += 1
            if total % 10_000_000 == 0:
                print(f"  {total/1e6:.0f}M scanned, {kept} kept", flush=True)
            if not pre.search(line):
                continue
            r = json.loads(line)
            codes = {c.get("code") for c in r.get("code", {}).get("coding", [])
                     if c.get("system") == LOINC}
            if not (codes & loincs):
                continue
            if part_bytes >= args.chunk_bytes:
                open_part()
            fout.write(line)
            part_bytes += len(line)
            kept += 1
    fout.close()
    print(f"DONE: kept {kept}/{total} rows across {part} part file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
