"""
Tests for keyword expansion using lemminflect.
"""

import pytest

from cicada.keyword_expander import KeywordExpander


class TestKeywordExpanderInitialization:
    """Tests for KeywordExpander initialization."""

    def test_invalid_expansion_type(self):
        """Invalid expansion_type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported expansion_type: invalid"):
            KeywordExpander(expansion_type="invalid")

    def test_lemmi_initialization(self):
        """Lemminflect-only initialization works."""
        expander = KeywordExpander(expansion_type="lemmi", verbose=False)
        assert expander.expansion_type == "lemmi"
        assert expander.verbose is False


class TestKeywordExpansion:
    """Tests for keyword expansion behavior."""

    def test_expand_keywords_includes_inflections(self, monkeypatch):
        expander = KeywordExpander(expansion_type="lemmi", verbose=False)
        monkeypatch.setattr(
            expander,
            "_get_inflections",
            lambda word: {word.lower(), f"{word.lower()}s"},
        )

        result = expander.expand_keywords(["database"])

        assert "database" in result["simple"]
        assert "databases" in result["simple"]

    def test_expand_keywords_skips_code_identifiers(self, monkeypatch):
        expander = KeywordExpander(expansion_type="lemmi", verbose=False)
        monkeypatch.setattr(
            expander,
            "_get_inflections",
            lambda word: {word.lower(), f"{word.lower()}s"},
        )

        result = expander.expand_keywords(["run"], code_identifiers=["run"])

        assert "run" in result["simple"]
        assert "runs" not in result["simple"]

    def test_min_score_filters_inflections(self, monkeypatch):
        expander = KeywordExpander(expansion_type="lemmi", verbose=False)
        monkeypatch.setattr(
            expander,
            "_get_inflections",
            lambda word: {word.lower(), f"{word.lower()}s"},
        )

        result = expander.expand_keywords(
            ["cache"],
            keyword_scores={"cache": 1.0},
            min_score=0.8,
        )

        assert "cache" in result["simple"]
        assert "caches" not in result["simple"]

    def test_get_expansion_info(self):
        expander = KeywordExpander(expansion_type="lemmi", verbose=False)
        info = expander.get_expansion_info()

        assert info["type"] == "lemmi"
