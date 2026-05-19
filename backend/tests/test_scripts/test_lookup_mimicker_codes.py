"""Unit tests for the UMLS mimicker-code resolver. UMLS lookups are mocked;
the real MCP call happens during actual runs, not in tests."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from lookup_mimicker_codes import resolve_one, build_codes_map  # noqa: E402


# Mock UMLS responses keyed by search term.
FAKE_UMLS = {
    "Chronic obstructive lung disease": {
        "system": "http://snomed.info/sct",
        "code": "13645005",
        "display": "Chronic obstructive lung disease (disorder)",
    },
    "Bronchiectasis": {
        "system": "http://snomed.info/sct",
        "code": "12295008",
        "display": "Bronchiectasis (disorder)",
    },
}


def _fake_resolver(term: str):
    return FAKE_UMLS.get(term)


def test_resolve_one_returns_code_for_known_term():
    result = resolve_one("Chronic obstructive lung disease", _fake_resolver)
    assert result["code"] == "13645005"
    assert result["system"] == "http://snomed.info/sct"


def test_resolve_one_returns_none_for_unknown_term():
    result = resolve_one("Nonexistent disease", _fake_resolver)
    assert result is None


def test_build_codes_map_dedupes_and_caches(tmp_path):
    packs = {
        "asthma": [
            {"display": "Chronic obstructive lung disease", "prevalence": 0.2},
        ],
        "copd": [
            {"display": "Chronic obstructive lung disease", "prevalence": 0.2},
            {"display": "Bronchiectasis", "prevalence": 0.05},
        ],
    }
    cache_path = tmp_path / "codes.json"
    result = build_codes_map(packs, _fake_resolver, cache_path)
    # Only 2 unique terms despite appearing in 2 phenotypes
    assert set(result) == {"Chronic obstructive lung disease", "Bronchiectasis"}
    assert result["Bronchiectasis"]["code"] == "12295008"
    # Cache file written
    assert json.loads(cache_path.read_text()) == result


def test_build_codes_map_preserves_cached_entries(tmp_path):
    """Pre-existing cache entries are kept even if the resolver fails now."""
    cache_path = tmp_path / "codes.json"
    cache_path.write_text(json.dumps({
        "Pre-cached condition": {"system": "x", "code": "999", "display": "Pre-cached"}
    }))
    packs = {"asthma": [{"display": "Pre-cached condition", "prevalence": 0.1}]}
    # Resolver returns None for everything; cache should still be honored
    result = build_codes_map(packs, lambda t: None, cache_path)
    assert result["Pre-cached condition"]["code"] == "999"
