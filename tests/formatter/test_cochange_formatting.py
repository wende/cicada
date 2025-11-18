"""Tests for co-change information in formatted search results."""

import pytest
from cicada.elixir.format.formatter import ModuleFormatter


class TestCoChangeFormatting:
    """Test suite for co-change display in search results."""

    @pytest.fixture
    def search_result_with_cochange(self):
        """Search result with co-change information."""
        return {
            "type": "function",
            "module": "ModuleA",
            "name": "ModuleA.validate_user/2",
            "file": "lib/module_a.ex",
            "line": 5,
            "score": 0.95,
            "matched_keywords": ["validate", "authentication"],
            "keyword_sources": {"validate": "docs", "authentication": "docs"},
            "doc": "Validates user credentials",
            "function": {
                "name": "validate_user",
                "arity": 2,
                "line": 5,
                "type": "def",
            },
            "cochange_info": {
                "related_files": [
                    {"file": "lib/module_b.ex", "count": 15, "module": "ModuleB"},
                    {"file": "lib/module_c.ex", "count": 3, "module": "ModuleC"},
                ],
                "related_functions": [
                    {
                        "module": "ModuleB",
                        "function": "check_credentials",
                        "arity": 2,
                        "count": 10,
                    },
                    {"module": "ModuleC", "function": "log_attempt", "arity": 1, "count": 5},
                ],
            },
        }

    @pytest.fixture
    def search_result_without_cochange(self):
        """Search result without co-change information."""
        return {
            "type": "function",
            "module": "ModuleD",
            "name": "ModuleD.isolated_func/0",
            "file": "lib/module_d.ex",
            "line": 10,
            "score": 0.85,
            "matched_keywords": ["isolated"],
            "keyword_sources": {"isolated": "docs"},
            "doc": "Isolated function",
            "function": {
                "name": "isolated_func",
                "arity": 0,
                "line": 10,
                "type": "def",
            },
        }

    @pytest.fixture
    def module_result_with_cochange(self):
        """Module-level search result with co-change information."""
        return {
            "type": "module",
            "module": "ModuleA",
            "name": "ModuleA",
            "file": "lib/module_a.ex",
            "line": 1,
            "score": 0.90,
            "matched_keywords": ["authentication", "user"],
            "keyword_sources": {"authentication": "docs", "user": "docs"},
            "doc": "Module A handles authentication",
            "cochange_info": {
                "related_files": [
                    {"file": "lib/module_b.ex", "count": 15, "module": "ModuleB"},
                    {"file": "lib/module_c.ex", "count": 3, "module": "ModuleC"},
                ],
            },
        }

    def test_format_result_displays_cochange_files(self, search_result_with_cochange):
        """Test that co-changed files are displayed in search results."""
        # Act
        output = ModuleFormatter.format_keyword_search_results_markdown(
            [search_result_with_cochange], show_scores=True
        )

        # Assert - should contain co-change file information
        assert "Often changed with:" in output
        assert "ModuleB (15 commits)" in output
        assert "ModuleC (3 commits)" in output

    def test_format_result_displays_cochange_functions(self, search_result_with_cochange):
        """Test that co-changed functions are displayed in search results."""
        # Act
        output = ModuleFormatter.format_keyword_search_results_markdown(
            [search_result_with_cochange], show_scores=True
        )

        # Assert - should contain co-change function information
        assert "Related functions:" in output
        assert "ModuleB.check_credentials/2" in output
        assert "ModuleC.log_attempt/1" in output

    def test_format_result_without_cochange_no_section(self, search_result_without_cochange):
        """Test that results without co-change data don't show co-change section."""
        # Act
        output = ModuleFormatter.format_keyword_search_results_markdown(
            [search_result_without_cochange], show_scores=True
        )

        # Assert - should NOT contain co-change sections
        assert "Often changed with:" not in output
        assert "Related functions:" not in output

    def test_format_module_result_displays_cochange(self, module_result_with_cochange):
        """Test that module-level results show co-change information."""
        # Act
        output = ModuleFormatter.format_keyword_search_results_markdown(
            [module_result_with_cochange], show_scores=True
        )

        # Assert - should contain co-change file information
        assert "Often changed with:" in output
        assert "ModuleB" in output
        assert "ModuleC" in output

    def test_cochange_section_limits_display(self, search_result_with_cochange):
        """Test that co-change section limits number of displayed items."""
        # Arrange - add many co-changed files
        search_result_with_cochange["cochange_info"]["related_files"] = [
            {"file": f"lib/module_{i}.ex", "count": 10 - i, "module": f"Module{i}"}
            for i in range(10)
        ]

        # Act
        output = ModuleFormatter.format_keyword_search_results_markdown(
            [search_result_with_cochange], show_scores=True
        )

        # Assert - should limit display (e.g., top 5) and show "... and N more"
        assert "and 5 more" in output or "Module9" not in output

    def test_cochange_sorted_by_frequency(self, search_result_with_cochange):
        """Test that co-change items are sorted by frequency (most frequent first)."""
        # Arrange - ensure specific ordering
        search_result_with_cochange["cochange_info"]["related_files"] = [
            {"file": "lib/low_freq.ex", "count": 2, "module": "LowFreq"},
            {"file": "lib/high_freq.ex", "count": 20, "module": "HighFreq"},
            {"file": "lib/mid_freq.ex", "count": 10, "module": "MidFreq"},
        ]

        # Act
        output = ModuleFormatter.format_keyword_search_results_markdown(
            [search_result_with_cochange], show_scores=True
        )

        # Assert - HighFreq should appear before MidFreq, MidFreq before LowFreq
        high_pos = output.find("HighFreq")
        mid_pos = output.find("MidFreq")
        low_pos = output.find("LowFreq")

        assert high_pos > 0, "HighFreq should be present"
        assert mid_pos > 0, "MidFreq should be present"
        assert high_pos < mid_pos, "HighFreq should appear before MidFreq"
        assert mid_pos < low_pos or low_pos == -1, "MidFreq should appear before LowFreq"

    def test_multiple_results_each_shows_own_cochange(
        self, search_result_with_cochange, search_result_without_cochange
    ):
        """Test that each result shows its own co-change information."""
        # Act
        output = ModuleFormatter.format_keyword_search_results_markdown(
            [search_result_with_cochange, search_result_without_cochange], show_scores=True
        )

        # Assert - first result has co-change, second doesn't
        # Count occurrences of "Often changed with:" - should be 1
        assert output.count("Often changed with:") == 1

    def test_cochange_formatting_is_compact(self, search_result_with_cochange):
        """Test that co-change display is compact and doesn't overwhelm the output."""
        # Act
        output = ModuleFormatter.format_keyword_search_results_markdown(
            [search_result_with_cochange], show_scores=True
        )

        # Assert - co-change section should be brief
        # Check that it doesn't add too many lines (exact number flexible)
        lines = output.split("\n")
        cochange_lines = [
            l for l in lines if "Often changed with:" in l or "Related functions:" in l
        ]

        # Should have co-change sections but not be overly verbose
        assert len(cochange_lines) <= 2  # At most header for files and functions

    def test_empty_cochange_arrays_not_displayed(self):
        """Test that empty co-change arrays don't create empty sections."""
        # Arrange
        result = {
            "type": "function",
            "module": "ModuleA",
            "name": "ModuleA.func/1",
            "file": "lib/module_a.ex",
            "line": 5,
            "score": 0.90,
            "matched_keywords": ["test"],
            "keyword_sources": {"test": "docs"},
            "doc": "Test function",
            "function": {"name": "func", "arity": 1, "line": 5, "type": "def"},
            "cochange_info": {
                "related_files": [],  # Empty
                "related_functions": [],  # Empty
            },
        }

        # Act
        output = ModuleFormatter.format_keyword_search_results_markdown([result], show_scores=True)

        # Assert - should NOT show co-change sections
        assert "Often changed with:" not in output
        assert "Related functions:" not in output

    def test_cochange_with_missing_module_names(self):
        """Test that co-change display handles missing module names gracefully."""
        # Arrange
        result = {
            "type": "function",
            "module": "ModuleA",
            "name": "ModuleA.func/1",
            "file": "lib/module_a.ex",
            "line": 5,
            "score": 0.90,
            "matched_keywords": ["test"],
            "keyword_sources": {"test": "docs"},
            "doc": "Test function",
            "function": {"name": "func", "arity": 1, "line": 5, "type": "def"},
            "cochange_info": {
                "related_files": [{"file": "lib/unknown.ex", "count": 5}],  # No module field
            },
        }

        # Act
        output = ModuleFormatter.format_keyword_search_results_markdown([result], show_scores=True)

        # Assert - should display filename (extracted from path) when module name is missing
        assert "unknown" in output  # Extracted from "lib/unknown.ex"
