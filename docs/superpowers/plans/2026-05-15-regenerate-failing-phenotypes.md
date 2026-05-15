# Regenerate Failing Phenotypes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get all 37 FAIL phenotypes back to PASS in the contamination triage by regenerating their Synthea data with adequate patient counts and refreshing each test case's `expected_patient_ids` from the new generation.

**Architecture:** A per-phenotype cycle — generate → augment → build minimal bundle → load to clean FHIR → re-derive `expected_patient_ids` → final triage verify — wrapped in a batch driver. Most modules are structurally fine (the 3-path A/B/C/D + WithDx/NoDx design is intact in all 37); the dominant issue is that the current `synthea/output/<pheno>/` was generated with too few `--patients`, so each test case's `expected_patient_ids` (captured from a larger original generation) references patients that no longer exist locally. A small subset (heart-failure at 14% yield, the lowest) may need module audit if even a generous raw count doesn't reach the cohort target.

**Tech Stack:** Python, Synthea (Java/Gradle), the existing `scripts/augment_fhir_codes.py` + `scripts/build_minimal_bundles.py` + `scripts/reload_phenotype.py` + `synthea/generate_test_data.py`, the Microsoft Health FHIR Server on Azure for verification.

**The 37 FAIL phenotypes** (from the 2026-05-14 triage, in `bykphfac8.output`):
depression, type-2-diabetes, coronary-heart-disease, breast-cancer, sickle-cell-disease, gerd, hepatitis-c, heart-failure, peripheral-arterial-disease, multiple-sclerosis, atrial-fibrillation, familial-hypercholesterolemia, pneumonia, epilepsy, hypertension, rheumatoid-arthritis, hypothyroidism, venous-thromboembolism, carotid-atherosclerosis, ckd, stroke, type-1-diabetes, crohns-disease, systemic-lupus-erythematosus, dementia, cervical-cancer, atopic-dermatitis, ovarian-cancer, bipolar-disorder, nafld, lyme-disease, clopidogrel-poor-metabolizers, ulcerative-colitis, steroid-induced-avn, sepsis, drug-induced-liver-injury, neonatal-abstinence-syndrome.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `scripts/rederive_expected_patients.py` | NEW — for each test case of a phenotype, run gold queries against the currently-loaded FHIR server (same single/multi-union/negation logic as `reload_phenotype.py`'s `_expected_patient_set`), capture patient IDs, write them back to the test case JSON's `test_data.expected_patient_ids` and `test_data.expected_result_count`. |
| `scripts/regenerate_phenotype.py` | NEW — orchestrates the per-phenotype cycle: compute target patient count from the test cases → call `synthea/generate_test_data.py` → call `scripts/augment_fhir_codes.py` → call `scripts/build_minimal_bundles.py <pheno>` → call `scripts/reload_phenotype.py <pheno>` (wipe+load) → call `scripts/rederive_expected_patients.py <pheno>` → final `scripts/reload_phenotype.py <pheno> --no-wipe` to confirm verify now passes. |
| `scripts/regenerate_batch.py` | NEW — runs `regenerate_phenotype.py` over a list of phenotypes (or all 37) with progress logging, per-phenotype fail-fast, and a final PASS/FAIL summary. |
| `synthea/generate_test_data.py` | EXISTING — accepts `--phenotype <name>`, `--patients <N>`, `--controls <N>`. Reused. |
| `scripts/augment_fhir_codes.py` | EXISTING — post-Synthea multi-coding pipeline; uses `data/code_augmentations.json`. Reused. |
| `scripts/build_minimal_bundles.py` | EXISTING — accepts phenotype names; reused to rebuild the minimal bundle. |
| `scripts/reload_phenotype.py` | EXISTING — wipe/load/verify cycle; reused. |
| `backend/tests/test_scripts/test_rederive_expected_patients.py` | NEW — unit tests for re-derive (mocked FHIR client). |
| `backend/tests/test_scripts/__init__.py` | NEW — empty package marker if directory doesn't exist. |
| `docs/superpowers/plans/2026-05-15-regenerate-failing-phenotypes.md` | This plan. |

### Patient count formula

For each phenotype, compute the raw patient count to generate:

```
expected_max = max(len(tc["test_data"]["expected_patient_ids"])
                   for tc in <that phenotype's test cases>
                   if tc["test_data"].get("expected_patient_ids"))

raw_patients = max(200, min(3000, ceil(expected_max / 0.15)))
controls     = max(30, raw_patients // 5)
```

`0.15` is a conservative-floor yield (HF measured 14%, CHD 26%, asthma 67%); the formula gives ~7× safety on `expected_max`. Floor 200 / cap 3000 to bound Synthea wall-clock. Controls at 20% of positive matches the existing 80/30, 200/100 convention seen in current outputs.

For phenotypes that fail verify even after this generous count (yield < 15%), Task 5 audits the module.

---

## Task 1: Re-derive script + tests

**Files:**
- Create: `scripts/rederive_expected_patients.py`
- Create: `backend/tests/test_scripts/__init__.py`
- Create: `backend/tests/test_scripts/test_rederive_expected_patients.py`

- [ ] **Step 1: Create the test package marker (if needed)**

```bash
mkdir -p backend/tests/test_scripts
touch backend/tests/test_scripts/__init__.py
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_scripts/test_rederive_expected_patients.py
"""Unit tests for the re-derive script: given a mocked FHIR client + a test
case file, the script overwrites expected_patient_ids with the IDs the gold
queries currently return, and updates expected_result_count to match."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from rederive_expected_patients import rederive_test_case  # noqa: E402


def _make_client(query_to_patients):
    client = MagicMock()
    client.get_patient_ids_from_query.side_effect = (
        lambda url: sorted(query_to_patients.get(url, set()))
    )
    return client


def test_rederive_single_query(tmp_path):
    tc_file = tmp_path / "phekb-x-dx.json"
    tc_file.write_text(json.dumps({
        "id": "phekb-x-dx",
        "expected_query": {"url": "Condition?code=snomed|1"},
        "metadata": {},
        "test_data": {"expected_patient_ids": ["stale1", "stale2"],
                      "expected_result_count": 2},
    }))
    client = _make_client({"Condition?code=snomed|1": {"new1", "new2", "new3"}})
    changed = rederive_test_case(client, tc_file)
    assert changed is True
    new = json.loads(tc_file.read_text())
    assert sorted(new["test_data"]["expected_patient_ids"]) == ["new1", "new2", "new3"]
    assert new["test_data"]["expected_result_count"] == 3


def test_rederive_multi_query_union(tmp_path):
    tc_file = tmp_path / "phekb-x-comp.json"
    tc_file.write_text(json.dumps({
        "id": "phekb-x-comp",
        "expected_query": {"url": "Condition?code=snomed|1"},
        "metadata": {"multi_query": True,
                     "expected_queries": ["Condition?code=A", "MedicationRequest?code=B"]},
        "test_data": {"expected_patient_ids": [], "expected_result_count": 0},
    }))
    client = _make_client({"Condition?code=A": {"p1", "p2"},
                           "MedicationRequest?code=B": {"p2", "p3"}})
    rederive_test_case(client, tc_file)
    new = json.loads(tc_file.read_text())
    assert sorted(new["test_data"]["expected_patient_ids"]) == ["p1", "p2", "p3"]


def test_rederive_negation(tmp_path):
    tc_file = tmp_path / "phekb-x-neg.json"
    tc_file.write_text(json.dumps({
        "id": "phekb-x-neg",
        "expected_query": {"url": "MedicationRequest?code=A"},
        "metadata": {"multi_query": True, "negation": True,
                     "negation_operation": "query[0]_patients - query[1]_patients",
                     "expected_queries": ["MedicationRequest?code=A", "Condition?code=B"]},
        "test_data": {"expected_patient_ids": [], "expected_result_count": 0},
    }))
    client = _make_client({"MedicationRequest?code=A": {"p1", "p2", "p3"},
                           "Condition?code=B": {"p2"}})
    rederive_test_case(client, tc_file)
    new = json.loads(tc_file.read_text())
    assert sorted(new["test_data"]["expected_patient_ids"]) == ["p1", "p3"]


def test_rederive_no_change_returns_false(tmp_path):
    tc_file = tmp_path / "phekb-x-dx.json"
    tc_file.write_text(json.dumps({
        "id": "phekb-x-dx",
        "expected_query": {"url": "Condition?code=snomed|1"},
        "metadata": {},
        "test_data": {"expected_patient_ids": ["p1", "p2"], "expected_result_count": 2},
    }))
    client = _make_client({"Condition?code=snomed|1": {"p1", "p2"}})
    assert rederive_test_case(client, tc_file) is False  # no diff -> no rewrite
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_scripts/test_rederive_expected_patients.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rederive_expected_patients'`.

- [ ] **Step 4: Write minimal implementation**

```python
# scripts/rederive_expected_patients.py
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_scripts/test_rederive_expected_patients.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add scripts/rederive_expected_patients.py backend/tests/test_scripts/
git commit -m "feat: add re-derive script for refreshing expected_patient_ids"
```

---

## Task 2: Per-phenotype regenerate script

**Files:**
- Create: `scripts/regenerate_phenotype.py`

- [ ] **Step 1: Verify the existing helper interfaces**

Run these to confirm the args each existing script accepts (the regenerate script subprocesses them):

```bash
python synthea/generate_test_data.py --help
python scripts/augment_fhir_codes.py --help
python scripts/build_minimal_bundles.py asthma   # already known: positional
python scripts/reload_phenotype.py --help
```

Note any deviations from the assumptions in Step 2 below; if `augment_fhir_codes.py` doesn't accept a `--phenotype` filter, document running it with no args (whole-tree augmentation) instead.

- [ ] **Step 2: Write the regenerate orchestrator**

```python
# scripts/regenerate_phenotype.py
"""Per-phenotype regeneration cycle: produces fresh Synthea data sized to the
phenotype's test cases, refreshes expected_patient_ids, rebuilds the minimal
bundle, and verifies the resulting setup loads cleanly.

Cycle:
  1. compute_target()      -- read test cases, derive raw patient count
  2. synthea generate      -- python synthea/generate_test_data.py ...
  3. augment_fhir_codes    -- python scripts/augment_fhir_codes.py
  4. build_minimal_bundles -- python scripts/build_minimal_bundles.py <pheno>
  5. reload_phenotype      -- python scripts/reload_phenotype.py <pheno>
                              (wipe + load; the loaded server is what the next step queries)
  6. rederive              -- python scripts/rederive_expected_patients.py <pheno>
  7. final verify          -- python scripts/reload_phenotype.py <pheno> --no-wipe
                              (re-runs verify; should now PASS)

Usage:
    python scripts/regenerate_phenotype.py coronary-heart-disease
    python scripts/regenerate_phenotype.py heart-failure --dry-run-counts
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from reload_phenotype import _test_cases_for  # noqa: E402

PY = sys.executable
SCRIPTS = REPO / "scripts"
TEST_CASES = REPO / "test-cases" / "phekb"
SYNTHEA_GEN = REPO / "synthea" / "generate_test_data.py"

YIELD_FLOOR = 0.15
RAW_FLOOR = 200
RAW_CAP = 3000


def compute_target(phenotype: str) -> tuple[int, int, int]:
    """Return (max_expected_pids, raw_patients, controls)."""
    expected_max = 0
    for f in _test_cases_for(phenotype):
        tc = json.loads(f.read_text(encoding="utf-8"))
        pids = tc.get("test_data", {}).get("expected_patient_ids") or []
        expected_max = max(expected_max, len(pids))
    raw = max(RAW_FLOOR, min(RAW_CAP, math.ceil(expected_max / YIELD_FLOOR)))
    controls = max(30, raw // 5)
    return expected_max, raw, controls


def _run(label: str, cmd: list[str]) -> int:
    print(f"\n--- {label} ---", flush=True)
    print(f"$ {' '.join(cmd)}", flush=True)
    t0 = time.time()
    rc = subprocess.run(cmd).returncode
    print(f"--- {label}: rc={rc} ({int(time.time() - t0)}s) ---", flush=True)
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phenotype")
    ap.add_argument("--dry-run-counts", action="store_true",
                    help="print computed patient count and exit")
    ap.add_argument("--skip-generate", action="store_true",
                    help="skip Synthea generation (re-derive only on existing data)")
    args = ap.parse_args()

    expected_max, raw, controls = compute_target(args.phenotype)
    print(f"[{args.phenotype}] expected_max={expected_max} -> "
          f"generate {raw} positive + {controls} control patients", flush=True)
    if args.dry_run_counts:
        return 0

    t0 = time.time()
    if not args.skip_generate:
        rc = _run("synthea generate",
                  [PY, str(SYNTHEA_GEN), "--phenotype", args.phenotype,
                   "--patients", str(raw), "--controls", str(controls)])
        if rc != 0:
            return rc
        rc = _run("augment_fhir_codes",
                  [PY, str(SCRIPTS / "augment_fhir_codes.py")])
        if rc != 0:
            return rc

    rc = _run("build_minimal_bundles",
              [PY, str(SCRIPTS / "build_minimal_bundles.py"), args.phenotype])
    if rc != 0:
        return rc
    rc = _run("reload (wipe + load)",
              [PY, str(SCRIPTS / "reload_phenotype.py"), args.phenotype])
    # reload returns 1 if verify fails; that's expected here -- we haven't
    # re-derived yet. Fail only on hard error (rc not in {0, 1}).
    if rc not in (0, 1):
        return rc
    rc = _run("rederive expected_patient_ids",
              [PY, str(SCRIPTS / "rederive_expected_patients.py"), args.phenotype])
    if rc != 0:
        return rc
    rc = _run("final verify (no wipe)",
              [PY, str(SCRIPTS / "reload_phenotype.py"), args.phenotype, "--no-wipe"])
    print(f"\n[{args.phenotype}] regeneration cycle "
          f"{'PASS' if rc == 0 else 'FAIL'} in {int(time.time() - t0)}s", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Smoke-test the dry-run path**

Run: `python scripts/regenerate_phenotype.py coronary-heart-disease --dry-run-counts`
Expected output (something like): `[coronary-heart-disease] expected_max=310 -> generate 2067 positive + 413 control patients`. No errors.

- [ ] **Step 4: Commit**

```bash
git add scripts/regenerate_phenotype.py
git commit -m "feat: per-phenotype regeneration cycle (generate->augment->rederive->verify)"
```

---

## Task 3: Pilot — coronary-heart-disease

This validates the full cycle on the worst-case-by-cohort-size FAIL phenotype (CHD: expected 310, currently has 13).

- [ ] **Step 1: Run the cycle**

```bash
set -a && source .env && set +a
python scripts/regenerate_phenotype.py coronary-heart-disease 2>&1 | tee /tmp/regen-chd.log
```

Expected: each stage prints `rc=0`, the final line prints `[coronary-heart-disease] regeneration cycle PASS`. Wall-clock: minutes (Synthea generation dominates; ~1500-2000 patients).

- [ ] **Step 2: Inspect the result**

```bash
python -c "
import json
for tc in ['phekb-coronary-heart-disease-chd', 'phekb-coronary-heart-disease-comprehensive', 'phekb-coronary-heart-disease-meds']:
    d = json.load(open(f'test-cases/phekb/{tc}.json'))
    print(f'  {tc}: expected_patient_ids={len(d[\"test_data\"][\"expected_patient_ids\"])}')
"
```

Expected: counts are now plausible (cohort sizes consistent with each other; e.g. comprehensive >= meds >= dx). The exact numbers will differ from the old `expected_patient_ids` — that's the point.

- [ ] **Step 3: Confirm minimal bundle + triage**

```bash
ls -la data/minimal-bundles/coronary-heart-disease*.json.gz
set -a && source .env && set +a
python scripts/reload_phenotype.py coronary-heart-disease 2>&1 | tail -10
```

Expected: bundle file(s) exist; reload reports `PASS` with every CHD test case showing `OK`.

- [ ] **Step 4: Commit the regenerated data**

```bash
git add data/minimal-bundles/coronary-heart-disease*.json.gz \
        test-cases/phekb/phekb-coronary-heart-disease*.json
git commit -m "data: regenerate coronary-heart-disease (refreshes expected_patient_ids)"
```

(Note: `synthea/output/` is not tracked by git, so the raw Synthea data isn't committed — only the minimal bundle and the updated test cases are.)

---

## Task 4: Pilot — heart-failure (lowest yield)

Heart-failure had the lowest measured yield (14%). This validates the formula handles low-yield cases.

- [ ] **Step 1: Confirm the computed count is generous enough**

```bash
python scripts/regenerate_phenotype.py heart-failure --dry-run-counts
```

Expected output: `[heart-failure] expected_max=67 -> generate 447 positive + 89 control patients`. With the previously-observed 14% yield, 447 raw patients should produce ~63 with HF — close to the 67 target. If this looks too tight, manually bump `--patients` in the next step.

- [ ] **Step 2: Run the cycle**

```bash
set -a && source .env && set +a
python scripts/regenerate_phenotype.py heart-failure 2>&1 | tee /tmp/regen-hf.log
```

- [ ] **Step 3: Check the outcome**

If the final verify reports PASS — proceed to Step 4 (commit).

If the final verify reports `MISMATCH +0 -N` even after re-derive (this would be unexpected — re-derive sets expected_patient_ids from the live server, so verify should always pass tautologically), it indicates a bug in `rederive_expected_patients.py`. Fix the bug before committing.

If specific test cases now have very few patients (e.g. `heart-failure-comprehensive` ends up with 5 patients when it used to expect 67), that's the yield problem — proceed to Task 5 to audit the module. Don't commit yet.

- [ ] **Step 4 (only if PASS): Commit**

```bash
git add data/minimal-bundles/heart-failure*.json.gz \
        test-cases/phekb/phekb-heart-failure*.json
git commit -m "data: regenerate heart-failure (refreshes expected_patient_ids)"
```

---

## Task 5: (Conditional) Audit heart-failure module yield

**Run this ONLY if Task 4 produced an unacceptably small heart-failure cohort.** Otherwise skip to Task 6.

The hypothesis is that `Age_Guard` rejects most patients OR the `Wellness_Encounter` / `Followup_Delay` timing means many "positive" patients never reach `Set_HF_Flag` → diagnosis before the simulation ends.

**Files:**
- Read: `synthea/modules/custom/phekb_heart_failure.json`

- [ ] **Step 1: Inspect the module's gating states**

```bash
python -c "
import json
m = json.load(open('synthea/modules/custom/phekb_heart_failure.json'))
states = m.get('states', {})
for name in ['Age_Guard', 'Choose_Patient_Path', 'Wellness_Encounter']:
    if name in states:
        print('===', name, '===')
        print(json.dumps(states[name], indent=2)[:600])
"
```

Look for: minimum age in `Age_Guard` (e.g. `>= 65` is restrictive), how `Wellness_Encounter` is reached (delays, conditional transitions), and any `distributed_transition` weights that under-weight the path that emits the diagnosis.

- [ ] **Step 2: Compare against a high-yield reference (asthma, 67%)**

```bash
python -c "
import json
m = json.load(open('synthea/modules/custom/phekb_asthma.json'))
states = m.get('states', {})
print('asthma Age_Guard:', json.dumps(states.get('Age_Guard'), indent=2)[:300])
"
```

- [ ] **Step 3: Decide and act**

If the gating states have a clear over-restrictive condition (e.g. `Age_Guard` requires age >= 65 when the test case isn't age-restricted) — relax the condition (e.g. >= 40), commit the module change, then re-run Task 4 from Step 2.

If the module looks reasonable and the issue is just statistical — bump the per-phenotype patient count for HF in `regenerate_phenotype.py` by adding an override map at the top of the file:

```python
# Per-phenotype overrides for raw patient count (low-yield modules).
RAW_OVERRIDES = {
    "heart-failure": 1500,  # 14% yield: 1500 -> ~210 with HF
}
```

…and use it in `compute_target`:

```python
def compute_target(phenotype: str) -> tuple[int, int, int]:
    ...
    raw = RAW_OVERRIDES.get(
        phenotype,
        max(RAW_FLOOR, min(RAW_CAP, math.ceil(expected_max / YIELD_FLOOR))),
    )
    controls = max(30, raw // 5)
    return expected_max, raw, controls
```

Re-run Task 4 from Step 2.

- [ ] **Step 4: Commit (only if module changed)**

```bash
git add synthea/modules/custom/phekb_heart_failure.json scripts/regenerate_phenotype.py
git commit -m "fix(synthea): relax heart-failure module gating to improve yield"
```

---

## Task 6: Batch driver

**Files:**
- Create: `scripts/regenerate_batch.py`

- [ ] **Step 1: Write the batch driver**

```python
# scripts/regenerate_batch.py
"""Run regenerate_phenotype.py over a list of phenotypes (or the full FAIL
list from the 2026-05-14 triage). Per-phenotype fail-fast: a failure logs
and continues to the next phenotype rather than aborting the whole batch.

Usage:
    python scripts/regenerate_batch.py                 # full 37-phenotype FAIL list
    python scripts/regenerate_batch.py stroke ckd      # specific phenotypes
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
REGEN = str(REPO / "scripts" / "regenerate_phenotype.py")

# 37 FAIL phenotypes from the 2026-05-14 contamination triage
# (bykphfac8.output -- TRIAGE SUMMARY block).
DEFAULT_PHENOTYPES = [
    "atopic-dermatitis", "atrial-fibrillation", "bipolar-disorder",
    "breast-cancer", "carotid-atherosclerosis", "cervical-cancer",
    "ckd", "clopidogrel-poor-metabolizers", "coronary-heart-disease",
    "crohns-disease", "dementia", "depression", "drug-induced-liver-injury",
    "epilepsy", "familial-hypercholesterolemia", "gerd", "heart-failure",
    "hepatitis-c", "hypertension", "hypothyroidism", "lyme-disease",
    "multiple-sclerosis", "nafld", "neonatal-abstinence-syndrome",
    "ovarian-cancer", "peripheral-arterial-disease", "pneumonia",
    "rheumatoid-arthritis", "sepsis", "sickle-cell-disease",
    "steroid-induced-avn", "stroke", "systemic-lupus-erythematosus",
    "type-1-diabetes", "type-2-diabetes", "ulcerative-colitis",
    "venous-thromboembolism",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phenotypes", nargs="*", help="empty = full FAIL list")
    args = ap.parse_args()
    phenos = args.phenotypes or DEFAULT_PHENOTYPES

    results = []
    suite_t0 = time.time()
    for i, p in enumerate(phenos, 1):
        print(f"\n{'#' * 72}\n# [{i}/{len(phenos)}] {p}\n{'#' * 72}", flush=True)
        t0 = time.time()
        rc = subprocess.run([PY, REGEN, p]).returncode
        results.append((p, rc, int(time.time() - t0)))

    print(f"\n{'#' * 72}\n# BATCH SUMMARY ({int(time.time() - suite_t0)}s)\n{'#' * 72}")
    npass = sum(1 for _, rc, _ in results if rc == 0)
    print(f"{len(results)} phenotypes: {npass} PASS, {len(results) - npass} FAIL\n")
    for p, rc, secs in sorted(results, key=lambda r: (r[1], r[0])):
        print(f"  {p:42} {'PASS' if rc == 0 else 'FAIL'}  ({secs}s)")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Sanity-check the script parses + lists 37**

Run: `python -c "import ast; ast.parse(open('scripts/regenerate_batch.py').read()); from scripts.regenerate_batch import DEFAULT_PHENOTYPES; assert len(DEFAULT_PHENOTYPES) == 37, DEFAULT_PHENOTYPES" 2>/dev/null || python -c "ns={}; exec(open('scripts/regenerate_batch.py').read(), ns); assert len(ns['DEFAULT_PHENOTYPES']) == 37"`
Expected: no error.

- [ ] **Step 3: Commit**

```bash
git add scripts/regenerate_batch.py
git commit -m "feat: batch driver for regenerating the 37 FAIL phenotypes"
```

---

## Task 7: Run the batch

This is the long-running execution. Estimated wall-clock: hours (Synthea generation × 35 phenotypes after the 2 pilots).

- [ ] **Step 1: Drop the 2 already-done pilots from the run list**

Run: `python scripts/regenerate_batch.py $(python -c "from scripts.regenerate_batch import DEFAULT_PHENOTYPES; print(' '.join(p for p in DEFAULT_PHENOTYPES if p not in ('coronary-heart-disease','heart-failure')))")`

(Or just rely on the cycle being idempotent and re-run all 37 — each per-phenotype cycle will repeat work but produce the same end state. The selective form above saves hours.)

Run as a background task; output goes to `/tmp/regen-batch.log`:

```bash
set -a && source .env && set +a
nohup python scripts/regenerate_batch.py [phenotypes from above] > /tmp/regen-batch.log 2>&1 &
```

- [ ] **Step 2: Monitor**

```bash
tail -f /tmp/regen-batch.log
```

Expected: each phenotype prints its 7-stage cycle, ending with `regeneration cycle PASS` or `FAIL`. The final `BATCH SUMMARY` block shows the per-phenotype roll-up.

- [ ] **Step 3: Triage any individual failures**

For any phenotype that ended `FAIL` in the batch summary: re-read its section of the log to locate the failing stage (`synthea generate`, `augment`, `build_minimal_bundles`, `reload`, `rederive`, `final verify`). Fix the specific issue (likely either a per-phenotype `RAW_OVERRIDES` bump or a module gating issue per Task 5) and re-run that single phenotype: `python scripts/regenerate_phenotype.py <pheno>`.

- [ ] **Step 4: Commit the batch's data updates**

```bash
git add data/minimal-bundles/ test-cases/phekb/
git commit -m "data: regenerate 35 remaining FAIL phenotypes"
```

---

## Task 8: Final whole-suite triage + push

- [ ] **Step 1: Run the contamination triage across all 108 phenotypes**

```bash
set -a && source .env && set +a
python scripts/reload_phenotype.py 2>&1 | tee /tmp/triage-final.log
```

Expected: `108 phenotypes: 108 PASS, 0 FAIL, 0 ERROR` in the TRIAGE SUMMARY block. If any FAIL remain, return to Task 7 Step 3 for those.

- [ ] **Step 2: Smoke-test the isolated suite on one regenerated phenotype**

This confirms scoring still works end-to-end after the data refresh:

```bash
set -a && source .env && set +a
python scripts/run_isolated_suite.py coronary-heart-disease --tiers 2 --prompt-variants naive 2>&1 | tail -20
```

Expected: reload PASSes, the matrix runs, a P/R/F1 line for the cell. The exact score depends on the model and isn't the point — the point is no errors and `expected != 0`.

- [ ] **Step 3: Push**

```bash
git push origin main
```

- [ ] **Step 4: Save a project-memory note about the regeneration**

Write `C:\Users\jaerwin\.claude\projects\C--repos-llm-fhir-query-eval\memory\project_phenotype_regeneration_2026_05_15.md`:

```markdown
---
name: project-phenotype-regeneration
description: 2026-05-15 regeneration of 37 phenotypes' Synthea data and refreshed expected_patient_ids
metadata:
  type: project
---

The 2026-05-14 contamination triage found 37 phenotypes' local synthea/output
was too small to satisfy their test cases' expected_patient_ids (e.g. CHD had
50 patients but expected 105 / 310). Modules and the augmentation pipeline
were structurally fine; the cause was a prior regeneration with too few
--patients. Fix on 2026-05-15: scripts/regenerate_phenotype.py +
scripts/regenerate_batch.py drove a per-phenotype generate -> augment ->
build_minimal_bundles -> reload -> rederive_expected_patients -> verify
cycle for the 37. Patient count formula: max(200, min(3000,
ceil(max_expected / 0.15))).

Notable: heart-failure required <module-fix-or-RAW_OVERRIDE-decision-from-Task-5>.

Ongoing: any future Synthea module changes need a regenerate_phenotype.py
re-run for that phenotype to refresh expected_patient_ids.

Related: [[project-fhir-server-contamination]]
```

Then add a one-line pointer in `MEMORY.md` under "Infrastructure Findings".

```bash
git add C:/Users/jaerwin/.claude/projects/C--repos-llm-fhir-query-eval/memory/
git commit -m "memory: note 2026-05-15 phenotype regeneration"
```

---

## Self-Review Notes

- **Spec coverage:** 37-phenotype regen (Tasks 1–4 build the per-phenotype tooling, 5 handles low-yield outliers, 6–7 batch the rest, 8 verifies the whole suite + persists). Updates to `expected_patient_ids` (Task 1's re-derive, applied per-phenotype in Task 2 step 6). Augmentation reuse (Task 2 step 2 stage 3). Minimal-bundle rebuild (Task 2 step 2 stage 4). Triage re-verification (Task 8 step 1). All workstream items covered.
- **Placeholder scan:** No `TBD` / `implement later` / "appropriate handling" items. The two conditional bits — Task 4 step 3's "if low yield then go to Task 5" and Task 5 itself — describe exact diagnostic commands and exact code edits, not vague action items.
- **Type consistency:** `rederive_test_case(client, tc_file: Path) -> bool` is the same shape used in Task 1's tests and Task 2's subprocess call. `_test_cases_for(phenotype)` and `_expected_patient_set(client, tc)` are imported from the existing `reload_phenotype.py` (already in the codebase), not redefined.
- **Out of scope:** the 71 currently-passing phenotypes are NOT touched by this plan. They can be evaluated against the regenerated server in parallel via `run_isolated_suite.py`.
