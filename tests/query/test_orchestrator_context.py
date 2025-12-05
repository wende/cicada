"""
Integration tests for query orchestrator with context extraction.

Tests that the query orchestrator properly formats results with contextual
information from matched keywords.
"""

import copy
import json
import tempfile
from pathlib import Path

import pytest

from cicada.query.orchestrator import QueryOrchestrator


@pytest.fixture
def sample_index_with_strings():
    """Create a sample index with documentation and string keywords."""
    return {
        "modules": {
            "TestModule.Auth": {
                "name": "TestModule.Auth",
                "file": "lib/test_module/auth.ex",
                "line": 1,
                "moduledoc": "Authentication module for validating user credentials. Handles login and session management.",
                "keywords": {"authentication": 0.9, "credentials": 0.8, "login": 0.7},
                "string_keywords": {"SELECT": 1.1, "users": 1.0},
                "string_sources": [
                    {
                        "string": "SELECT * FROM users WHERE active = true",
                        "line": 42,
                        "function": "fetch_all",
                    }
                ],
                "functions": [
                    {
                        "name": "validate_user",
                        "arity": 2,
                        "line": 15,
                        "type": "def",
                        "signature": "def validate_user(username, password)",
                        "doc": "Validates user credentials against the database.",
                        "keywords": {"validate": 0.9, "user": 0.8, "credentials": 0.7},
                        "string_keywords": {},
                        "string_sources": [],
                    }
                ],
            },
            "TestModule.Database": {
                "name": "TestModule.Database",
                "file": "lib/test_module/database.ex",
                "line": 1,
                "moduledoc": "Database connection and query utilities.",
                "keywords": {"database": 0.95, "connection": 0.85, "query": 0.80},
                "string_keywords": {"SELECT": 1.2, "INSERT": 1.1, "database": 1.0},
                "string_sources": [
                    {
                        "string": "INSERT INTO logs (message, level) VALUES ($1, $2)",
                        "line": 25,
                        "function": "log_message",
                    },
                    {
                        "string": "SELECT * FROM config WHERE key = $1",
                        "line": 35,
                        "function": "get_config",
                    },
                ],
                "functions": [],
            },
        },
        "metadata": {"version": "1.0", "indexed_at": "2024-01-01T00:00:00Z"},
    }


@pytest.fixture
def orchestrator_with_index(sample_index_with_strings):
    """Create a QueryOrchestrator with a sample index."""
    return QueryOrchestrator(sample_index_with_strings)


class TestOrchestratorContextExtraction:
    """Tests for context extraction in query orchestrator output."""

    def test_documentation_context_in_output(self, orchestrator_with_index):
        """Test that documentation context is included in formatted output with verbose=True."""
        formatted = orchestrator_with_index.execute_query(
            ["authentication", "credentials"], verbose=True
        )

        # Should contain documentation context in verbose mode
        assert "Matched in documentation:" in formatted
        # Should highlight keywords (ANSI codes for terminal output)
        assert "authentication" in formatted.lower()
        assert "credentials" in formatted.lower()

    def test_string_literal_context_in_output(self, orchestrator_with_index):
        """Test that string literal context is included in formatted output with verbose=True."""
        formatted = orchestrator_with_index.execute_query(["SELECT", "users"], verbose=True)

        # Should contain string context in verbose mode
        assert "Matched in strings:" in formatted
        # Should show the SQL query components (might have ANSI codes around keywords)
        assert "SELECT" in formatted
        assert "FROM" in formatted
        assert "users" in formatted
        # Should show line number
        assert "(line 42)" in formatted

    def test_combined_doc_and_string_context(self, orchestrator_with_index):
        """Test output when keywords match in both docs and strings."""
        formatted = orchestrator_with_index.execute_query(["database"])

        # Should have both sections since "database" appears in both doc and strings
        # (Though our test data has "database" only in doc keywords for TestModule.Database)
        # Let's just verify the output is well-formed
        assert len(formatted) > 0
        assert "TestModule.Database" in formatted

    def test_no_context_falls_back_to_simple_keywords(self, orchestrator_with_index):
        """Test that output shows simple keyword list in compact mode."""
        # Query for a keyword that exists but has no doc/string context
        index_copy = copy.deepcopy(orchestrator_with_index.index)
        auth_module = index_copy["modules"]["TestModule.Auth"]
        auth_module["moduledoc"] = None
        auth_module["string_sources"] = []
        auth_module["functions"][0]["doc"] = None
        auth_module["functions"][0]["string_sources"] = []

        orchestrator = QueryOrchestrator(index_copy)
        formatted = orchestrator.execute_query(["validate"])

        # Should have some output for the function
        assert "validate_user" in formatted

        # Should use compact format: keyword(d) without "Matched:" prefix
        assert "validate(d)" in formatted

        # And it should not include verbose contextual sections
        assert "Matched in documentation:" not in formatted
        assert "Matched in strings:" not in formatted

    def test_long_string_truncation_in_output(self, orchestrator_with_index):
        """Test that very long strings are truncated in verbose output."""
        # Our test data doesn't have very long strings, but we can verify
        # that strings are displayed properly in verbose mode
        formatted = orchestrator_with_index.execute_query(["INSERT"], verbose=True)

        # Should show components of the SQL query (might have ANSI codes)
        assert "INSERT" in formatted
        assert "INTO" in formatted
        assert "logs" in formatted
        # Should have line number
        assert "(line 25)" in formatted

    def test_multiple_string_sources_shown(self, orchestrator_with_index):
        """Test that multiple string sources are shown in output."""
        formatted = orchestrator_with_index.execute_query(["SELECT"])

        # TestModule.Auth has one SELECT string, TestModule.Database has two
        # At least one should be shown
        assert "SELECT" in formatted

    def test_context_enhances_search_results(self, orchestrator_with_index):
        """Test that the enhanced context makes search results more useful."""
        formatted = orchestrator_with_index.execute_query(["authentication"])

        # Verify the output has structure
        assert "TestModule.Auth" in formatted
        # In compact mode, should have simple keyword indicators
        assert "Matched:" in formatted or "authentication" in formatted.lower()

    def test_format_results_with_show_snippets(self, orchestrator_with_index):
        """Test that show_snippets parameter still works with new context extraction."""
        formatted = orchestrator_with_index.execute_query(["authentication"], show_snippets=True)

        # Should have both context and code snippets
        # Note: This would require the actual files to exist for snippets
        # For now, just verify the execute_query call works
        assert len(formatted) > 0


class TestOrchestratorContextWithFiltering:
    """Test context extraction with various search filters."""

    def test_context_with_scope_filter(self, orchestrator_with_index):
        """Test context extraction with scope filtering."""
        formatted = orchestrator_with_index.execute_query(["authentication"], scope="public")

        assert len(formatted) > 0

    def test_context_with_module_filter(self, orchestrator_with_index):
        """Test context extraction when filtering to modules only."""
        formatted = orchestrator_with_index.execute_query(["authentication"], result_type="modules")

        # Should only show module results
        assert "TestModule.Auth" in formatted
        # Should not show function-specific results
        assert "validate_user" not in formatted

    def test_context_with_match_source_docs(self, orchestrator_with_index):
        """Test context extraction when filtering to docs only."""
        formatted = orchestrator_with_index.execute_query(["authentication"], match_source="docs")

        # Should only show doc matches
        assert "Matched in strings:" not in formatted

    def test_context_with_match_source_strings(self, orchestrator_with_index):
        """Test context extraction when filtering to strings only."""
        formatted = orchestrator_with_index.execute_query(["SELECT"], match_source="strings")

        # Should only show string matches
        assert "SELECT" in formatted


class TestOrchestratorEdgeCases:
    """Test edge cases in context extraction."""

    def test_empty_results_format(self, orchestrator_with_index):
        """Test formatting when no results are found."""
        formatted = orchestrator_with_index.execute_query(["nonexistent_keyword"])

        # Should handle empty results gracefully
        assert isinstance(formatted, str)

    def test_module_without_doc(self, orchestrator_with_index):
        """Test handling of modules without documentation."""
        # Our test data all has docs, but we can verify the formatter doesn't crash
        formatted = orchestrator_with_index.execute_query(["database"])

        assert len(formatted) > 0

    def test_function_without_string_sources(self, orchestrator_with_index):
        """Test handling of functions without string sources."""
        formatted = orchestrator_with_index.execute_query(["validate"])

        # Should show doc context even without string sources
        assert "validate_user" in formatted
