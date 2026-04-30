"""Update -dx and -comprehensive test cases to query all SNOMED variants.

For each phenotype with module-level code variation, update the
``expected_query.url`` and ``metadata.required_codes`` in:
- ``phekb-<phenotype>-dx.json``
- ``phekb-<phenotype>-comprehensive.json`` (if present, only the Condition query inside expected_queries)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TC_DIR = Path(__file__).resolve().parents[1] / "test-cases" / "phekb"


PHENOTYPE_VARIANTS = {
    "type-2-diabetes": [
        ("44054006", "Type 2 diabetes mellitus"),
        ("73211009", "Diabetes mellitus"),
        ("9414007", "Impaired glucose tolerance"),
    ],
    "adhd": [
        ("406506008", "Attention deficit hyperactivity disorder"),
        ("31177006", "ADHD combined type"),
        ("192127007", "Child attention deficit disorder"),
    ],
    "appendicitis": [
        ("85189001", "Acute appendicitis"),
        ("74400008", "Appendicitis"),
    ],
    "asthma": [
        ("195967001", "Asthma"),
        ("389145006", "Allergic asthma"),
        ("233678006", "Childhood asthma"),
        ("195977004", "Mixed asthma"),
    ],
    "atopic-dermatitis": [
        ("24079001", "Atopic dermatitis"),
        ("43116000", "Eczema"),
    ],
    "atrial-fibrillation": [
        ("49436004", "Atrial fibrillation"),
        ("282825002", "Paroxysmal atrial fibrillation"),
        ("426749004", "Chronic atrial fibrillation"),
    ],
    "autism": [
        ("35919005", "Pervasive developmental disorder"),
        ("408856003", "Autistic disorder"),
        ("23560001", "Asperger's disorder"),
    ],
}


def build_code_url_param(variants: list[tuple[str, str]]) -> str:
    return ",".join(f"http://snomed.info/sct|{c}" for c, _ in variants)


def build_required_codes(variants: list[tuple[str, str]]) -> list[dict]:
    return [
        {
            "system": "http://snomed.info/sct",
            "code": code,
            "display": display,
            "source": "UMLS verified, code variation",
        }
        for code, display in variants
    ]


def update_dx(phenotype: str, variants: list[tuple[str, str]]) -> bool:
    path = TC_DIR / f"phekb-{phenotype}-dx.json"
    if not path.exists():
        print(f"NO -dx file for {phenotype}")
        return False
    with open(path, encoding="utf-8") as f:
        tc = json.load(f)
    code_param = build_code_url_param(variants)
    tc["expected_query"]["parameters"]["code"] = code_param
    tc["expected_query"]["url"] = f"Condition?code={code_param}"
    tc["metadata"]["required_codes"] = build_required_codes(variants)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Updated {path.name}")
    return True


def update_comprehensive(phenotype: str, variants: list[tuple[str, str]]) -> bool:
    path = TC_DIR / f"phekb-{phenotype}-comprehensive.json"
    if not path.exists():
        return False
    with open(path, encoding="utf-8") as f:
        tc = json.load(f)
    code_param = build_code_url_param(variants)
    new_condition_q = f"Condition?code={code_param}"
    eqs = tc.get("metadata", {}).get("expected_queries", [])
    updated = False
    for i, q in enumerate(eqs):
        if q.startswith("Condition?code="):
            eqs[i] = new_condition_q
            updated = True
    if "expected_query" in tc and tc["expected_query"].get("url", "").startswith("Condition?code="):
        tc["expected_query"]["url"] = new_condition_q
    if updated:
        # Refresh required_codes to include all variants while preserving non-SNOMED entries
        rc = tc.get("metadata", {}).get("required_codes", [])
        rc = [c for c in rc if "snomed" not in c.get("system", "").lower()]
        rc = build_required_codes(variants) + rc
        tc["metadata"]["required_codes"] = rc
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Updated {path.name}")
    return True


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for phenotype, variants in PHENOTYPE_VARIANTS.items():
        update_dx(phenotype, variants)
        update_comprehensive(phenotype, variants)


if __name__ == "__main__":
    main()
