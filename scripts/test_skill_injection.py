"""Tests for closed-book skill injection (Anthropic FHIR skill baseline).

Run: python -m pytest scripts/test_skill_injection.py -q
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from src.llm.copilot_provider import compose_system_message


def test_no_prefix_returns_base_unchanged():
    assert compose_system_message("", "BASE PROMPT") == "BASE PROMPT"


def test_prefix_is_prepended_with_separator():
    assert compose_system_message("SKILL TEXT", "BASE PROMPT") == "SKILL TEXT\n\n---\n\nBASE PROMPT"


def test_none_prefix_treated_as_empty():
    assert compose_system_message(None, "BASE PROMPT") == "BASE PROMPT"


from run_sanity_matrix import _strip_frontmatter  # noqa: E402


def test_strip_frontmatter_removes_leading_yaml_block():
    text = "---\nname: x\ndescription: y\n---\n\n# Body\ncontent"
    assert _strip_frontmatter(text) == "# Body\ncontent"


def test_strip_frontmatter_noop_without_frontmatter():
    text = "# Body\ncontent"
    assert _strip_frontmatter(text) == text
