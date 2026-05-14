"""Audit cross-phenotype contamination: for every test case, run its gold query
against the live server and compare to the authored expected_patient_ids."""
import sys, json, glob
from pathlib import Path
sys.path.insert(0, 'backend')
from src.fhir.client import FHIRClient

c = FHIRClient(base_url='https://jaerwinllm.azurewebsites.net', fhir_version='', verify_ssl=False)
rows = []
for f in sorted(glob.glob('test-cases/phekb/*.json')):
    tc = json.load(open(f, encoding='utf-8'))
    eq = tc.get('expected_query') or {}
    url = eq.get('url')
    exp_ids = tc.get('test_data', {}).get('expected_patient_ids') or []
    if not url or not exp_ids:
        continue
    try:
        got = set(c.get_patient_ids_from_query(url))
    except Exception as e:
        rows.append((Path(f).stem, len(exp_ids), None, f"ERR {str(e)[:40]}"))
        continue
    exp = set(exp_ids)
    extra = len(got - exp)
    missing = len(exp - got)
    status = "clean" if (extra == 0 and missing == 0) else f"+{extra} -{missing}"
    rows.append((Path(f).stem, len(exp), len(got), status))

clean = sum(1 for r in rows if r[3] == "clean")
contam = [r for r in rows if r[3] not in ("clean",) and not str(r[3]).startswith("ERR")]
err = [r for r in rows if str(r[3]).startswith("ERR")]
print(f"\n=== {len(rows)} test cases audited: {clean} clean, {len(contam)} contaminated, {len(err)} errors ===\n")
print(f"{'test case':<55} {'authored':>9} {'on server':>10}  delta")
for name, e, g, s in sorted(contam, key=lambda r: -(r[2] or 0) + (r[1] or 0)):
    print(f"{name:<55} {e:>9} {str(g):>10}  {s}")
if err:
    print("\nERRORS:")
    for name, e, g, s in err:
        print(f"  {name}: {s}")
