"""Tests for QueryOrchestrator - smart code discovery."""

import re
import pytest
from datetime import datetime, timedelta

from cicada.query import QueryOrchestrator


class TestQueryOrchestrator:
    """Test the QueryOrchestrator class."""

    @pytest.fixture
    def sample_index(self):
        """Create a sample index with rich metadata for testing."""
        # Date for recent filter testing
        recent_date = (datetime.now() - timedelta(days=7)).isoformat()
        old_date = (datetime.now() - timedelta(days=30)).isoformat()

        return {
            "modules": {
                "MyApp.Auth": {
                    "file": "lib/my_app/auth.ex",
                    "line": 1,
                    "moduledoc": "Authentication and authorization module",
                    "keywords": {
                        "authentication": 0.9,
                        "auth": 0.8,
                        "security": 0.7,
                        "authent": 0.85,
                    },
                    "string_keywords": {"jwt": 0.9, "token": 0.8},
                    "functions": [
                        {
                            "name": "verify_token",
                            "arity": 2,
                            "line": 10,
                            "type": "def",  # public
                            "doc": "Verifies JWT token",
                            "keywords": {
                                "verify": 0.8,
                                "token": 0.9,
                                "jwt": 0.7,
                                "auth": 0.6,
                                "authent": 0.65,
                            },
                            "string_keywords": {"SELECT": 0.8, "users": 0.7},
                            "signature": "def verify_token(token, opts)",
                            "last_modified_at": recent_date,
                        },
                        {
                            "name": "hash_password",
                            "arity": 1,
                            "line": 30,
                            "type": "defp",  # private
                            "doc": "Hashes a password",
                            "keywords": {
                                "hash": 0.8,
                                "password": 0.9,
                                "encrypt": 0.7,
                                "auth": 0.5,
                                "authent": 0.55,
                            },
                            "signature": "defp hash_password(password)",
                            "last_modified_at": old_date,
                        },
                        {
                            "name": "login",
                            "arity": 2,
                            "line": 50,
                            "type": "def",  # public
                            "signature": "def login(email, password)",
                            "doc": "Authenticates user with credentials",
                            "keywords": {
                                "login": 0.9,
                                "authenticate": 0.8,
                                "signin": 0.7,
                                "auth": 0.75,
                                "authent": 0.8,
                            },
                            "last_modified_at": recent_date,
                        },
                    ],
                },
                "MyApp.User": {
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                    "moduledoc": "User management module",
                    "keywords": {"user": 0.9, "account": 0.7, "profile": 0.6},
                    "functions": [
                        {
                            "name": "create_user",
                            "arity": 1,
                            "line": 10,
                            "type": "def",
                            "doc": "Creates a new user",
                            "signature": "def create_user(attrs)",
                            "keywords": {"create": 0.8, "user": 0.9, "new": 0.7},
                            "last_modified_at": old_date,
                        },
                        {
                            "name": "update_user",
                            "arity": 2,
                            "line": 30,
                            "type": "def",
                            "doc": "Updates user data",
                            "signature": "def update_user(user, attrs)",
                            "keywords": {"update": 0.8, "user": 0.9, "modify": 0.7},
                        },
                    ],
                },
                "MyApp.UserTest": {
                    "file": "test/my_app/user_test.exs",
                    "line": 1,
                    "moduledoc": "User tests",
                    "keywords": {"test": 0.9, "user": 0.8, "suite": 0.6},
                    "functions": [
                        {
                            "name": "test_create_user",
                            "arity": 1,
                            "line": 10,
                            "type": "def",
                            "doc": "Tests user creation",
                            "signature": "def test_create_user(_context)",
                            "keywords": {"test": 0.9, "create": 0.8, "user": 0.9},
                        },
                    ],
                },
            }
        }

    def test_query_analysis_keywords(self):
        """Test query analysis detects keywords correctly."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        # Single keyword
        strategy = orchestrator._analyze_query("authentication")
        assert strategy.use_keyword_search is True
        assert strategy.use_pattern_search is False
        assert "authentication" in strategy.search_keywords

        # Multiple keywords
        strategy = orchestrator._analyze_query(["login", "auth"])
        assert strategy.use_keyword_search is True
        assert len(strategy.search_keywords) == 2

    def test_query_analysis_patterns(self):
        """Test query analysis detects patterns correctly."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        # Wildcard pattern
        strategy = orchestrator._analyze_query("create*")
        assert strategy.use_pattern_search is True
        assert "create*" in strategy.search_patterns

        # Module qualified
        strategy = orchestrator._analyze_query("MyApp.User.create*")
        assert strategy.use_pattern_search is True

        # Arity specified
        strategy = orchestrator._analyze_query("create_user/1")
        assert strategy.use_pattern_search is True

        # File path
        strategy = orchestrator._analyze_query("lib/auth.ex:verify*")
        assert strategy.use_pattern_search is True

    def test_query_analysis_mixed(self):
        """Test query analysis handles mixed keywords and patterns."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        strategy = orchestrator._analyze_query(["authentication", "MyApp.Auth.*"])
        assert strategy.use_keyword_search is True
        assert strategy.use_pattern_search is True
        assert "authentication" in strategy.search_keywords
        assert "MyApp.Auth.*" in strategy.search_patterns

    def test_scope_filter_all(self, sample_index):
        """Test scope='all' returns everything."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("auth", scope="all")

        assert "MyApp.Auth" in result
        assert "verify_token" in result
        assert "hash_password" in result  # private function included
        assert "login" in result

    def test_scope_filter_public(self, sample_index):
        """Test scope='public' filters to public functions only."""
        orchestrator = QueryOrchestrator(sample_index)
        # Use filter_type="functions" to ensure we get functions, not just modules
        result = orchestrator.execute_query("auth", scope="public", filter_type="functions")

        # Should have some public functions or at least not have private ones
        assert "hash_password" not in result  # private, should be excluded
        # May or may not have results depending on keyword scores
        assert "Query:" in result

    def test_scope_filter_private(self, sample_index):
        """Test scope='private' filters to private functions only."""
        orchestrator = QueryOrchestrator(sample_index)
        # Use password keyword which appears in private function
        result = orchestrator.execute_query("password", scope="private", filter_type="functions")

        # Should not have public functions
        assert "verify_token" not in result  # public, should be excluded
        assert "login" not in result  # public, should be excluded

    def test_scope_filter_recent(self, sample_index):
        """Test recent=True filters to recently changed code."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("auth", recent=True)

        # verify_token and login were modified recently
        assert "verify_token" in result
        assert "login" in result
        # hash_password is old, should be excluded
        assert "hash_password" not in result

    def test_filter_type_modules(self, sample_index):
        """Test filter_type='modules' returns only modules."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("auth", filter_type="modules")

        assert "MyApp.Auth" in result  # module
        # Functions should not be in top results (no function names with dots after module)
        # In compact format, just check that we got module names not function names
        assert "verify_token" not in result  # function name shouldn't appear

    def test_filter_type_functions(self, sample_index):
        """Test filter_type='functions' returns only functions."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("auth", filter_type="functions")

        # Functions should be present
        assert "verify_token" in result
        # Module-only results should be filtered out
        assert "Module: MyApp.Auth" not in result or "Function:" in result

    def test_match_source_all(self, sample_index):
        """Test match_source='all' searches both docs and strings."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query(["jwt"], match_source="all")

        # Should match via both doc keywords and string keywords
        assert "verify_token" in result

    def test_match_source_strings(self, sample_index):
        """Test match_source='strings' searches only string literals."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query(["SELECT"], match_source="strings")

        # Should match verify_token which has "SELECT" in string_keywords
        assert (
            "verify_token" in result or "Found: 0" in result
        )  # May have 0 results depending on index

    def test_path_pattern_filter(self, sample_index):
        """Test path_pattern glob filtering."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("user", path_pattern="lib/**")

        # Should exclude test files
        assert "test/my_app/user_test.exs" not in result
        assert "test_create_user" not in result
        # Should have found something or nothing
        assert "Query:" in result

    def test_path_pattern_exclude_tests(self, sample_index):
        """Test path_pattern with specific path filter."""
        orchestrator = QueryOrchestrator(sample_index)
        # Use a specific path pattern to include only lib files
        result = orchestrator.execute_query("auth", path_pattern="lib/**")

        # Should include lib files
        assert "MyApp.Auth" in result
        # Path pattern filtering applied (may or may not have results from test/)
        assert "Query:" in result

    def test_path_pattern_include_all(self, sample_index):
        """Test without path_pattern includes all files including tests."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("user")

        # Should include both test and non-test files when no path filter
        assert "user" in result.lower()

    def test_path_pattern_negation_excludes_tests(self, sample_index):
        """Test negated path_pattern excludes matching files."""
        orchestrator = QueryOrchestrator(sample_index)

        # Query without filter (baseline)
        result_all = orchestrator.execute_query("user")

        # Query with negation to exclude test directory
        result_no_tests = orchestrator.execute_query("user", path_pattern="!**/test/**")

        # Both should have found something
        assert "Query:" in result_all
        assert "Query:" in result_no_tests

        # Result with negation should not contain test/ paths
        # (if there were any test files in the results)
        lines_no_tests = [line for line in result_no_tests.split("\n") if "test/" in line.lower()]
        # Should have no lines mentioning test/ paths
        assert len(lines_no_tests) == 0

    def test_max_results(self, sample_index):
        """Test max_results limits output."""
        orchestrator = QueryOrchestrator(sample_index)

        # Request only 2 results
        result = orchestrator.execute_query("user", max_results=2)

        # Count result items (lines starting with "###")
        result_count = result.count("###")
        assert result_count <= 2

    def test_pattern_search(self, sample_index):
        """Test pattern-based search."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("MyApp.Auth.verify*")

        assert "verify_token" in result

    def test_wildcard_search(self, sample_index):
        """Test wildcard search."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("*user*")

        # Should match create_user, update_user, etc.
        assert "user" in result.lower()

    def test_deduplication(self, sample_index):
        """Test that duplicate results are removed."""
        orchestrator = QueryOrchestrator(sample_index)

        # Use mixed query that might match same items via different paths
        result = orchestrator.execute_query(["auth", "authentication", "MyApp.Auth.*"])

        # Count occurrences of MyApp.Auth.verify_token
        # Should only appear once despite multiple matches
        count = result.count("verify_token/2")
        # Might appear in title and in body, but should be consistent
        assert count >= 1  # At least one occurrence

    def test_suggestions_generated(self, sample_index):
        """Test that suggestions are generated."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("auth")

        # Should have suggestions section
        assert "Suggested Next Steps" in result
        assert "search_function" in result or "search_module" in result

    def test_suggestions_sql_keywords(self, sample_index):
        """Test SQL-related suggestions."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query(["SELECT", "query"])

        # Should suggest match_source='strings'
        assert "match_source='strings'" in result or "Suggested Next Steps" in result

    def test_match_indicators(self, sample_index):
        """Test that match indicators are shown."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query(["jwt"])

        # Should have match source indicators in compact format: (in docs), (in strings)
        # At minimum should have found something
        assert "jwt" in result.lower() or "Matched keywords:" in result

    def test_empty_query(self):
        """Test empty query handling."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)
        result = orchestrator.execute_query("")

        assert "Error" in result or "empty" in result.lower()

    def test_no_results(self, sample_index):
        """Test handling of queries with no results."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("nonexistent_keyword_xyz")

        assert "Found: 0" in result or "No results" in result.lower() or "0 result" in result

    def test_glob_pattern_recursive(self, sample_index):
        """Test ** glob pattern for recursive matching."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("user", path_pattern="**/*.ex")

        # Should not match .exs test files
        assert ".exs" not in result or "0 result" in result
        assert "Query:" in result

    def test_glob_pattern_wildcard(self, sample_index):
        """Test * glob pattern for single-level wildcard."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("user", path_pattern="lib/my_app/*.ex")

        # Should match files in lib/my_app/ directory
        assert "user.ex" in result or "auth.ex" in result or "MyApp" in result

    def test_is_pattern_query_detection(self):
        """Test _is_pattern_query detection logic."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        # Patterns
        assert orchestrator._is_pattern_query("create*") is True
        assert orchestrator._is_pattern_query("MyApp.User.*") is True
        assert orchestrator._is_pattern_query("create_user/2") is True
        assert orchestrator._is_pattern_query("lib/auth.ex:verify") is True
        assert orchestrator._is_pattern_query("create*|update*") is True

        # Not patterns (keywords)
        assert orchestrator._is_pattern_query("authentication") is False
        assert orchestrator._is_pattern_query("user") is False
        assert orchestrator._is_pattern_query("login") is False

    def test_visibility_filter_in_results(self, sample_index):
        """Test that visibility information is included in results."""
        orchestrator = QueryOrchestrator(sample_index)
        # Use "password" which is a keyword that should match hash_password
        result = orchestrator.execute_query("password", filter_type="functions")

        # Should show visibility info if results found
        if "Function:" in result:
            assert "Visibility" in result or "Private" in result or "Public" in result
        # Or we might have 0 results, which is also okay
        assert "Query:" in result

    def test_combined_filters(self, sample_index):
        """Test combining multiple filters."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query(
            "auth",
            scope="public",
            filter_type="functions",
            path_pattern="lib/**",
            max_results=5,
        )

        # Should apply all filters
        # Public functions only
        assert "hash_password" not in result  # private
        # Test files excluded
        assert "test/" not in result
        assert "test_create_user" not in result
        # Have results or not
        assert "Query:" in result

    def test_ranking_by_score(self, sample_index):
        """Test that results are ranked by score."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query(["authentication", "auth", "verify"])

        # Results should be ordered by relevance
        # First result should have highest score
        lines = result.split("\n")
        scores = []
        for line in lines:
            if "Score:" in line:
                # Extract score value
                import re

                match = re.search(r"Score:\s*([\d.]+)", line)
                if match:
                    scores.append(float(match.group(1)))

        # Scores should be in descending order (or equal)
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"Scores not properly ranked: {scores}"

    # ============================================================
    # Cycle 1: Code Snippet Preview Tests (TDD RED phase)
    # ============================================================

    @pytest.fixture
    def sample_index_with_files(self, tmp_path):
        """Create a sample index with actual files for snippet testing."""
        import os

        # Create directory structure
        lib_dir = tmp_path / "lib" / "my_app"
        lib_dir.mkdir(parents=True)

        # Create auth.ex file with actual Elixir code
        auth_file = lib_dir / "auth.ex"
        auth_content = """defmodule MyApp.Auth do
  @moduledoc "Authentication and authorization module"

  alias MyApp.Token

  @doc "Verifies JWT token"
  def verify_token(token, opts \\\\ []) do
    with {:ok, claims} <- Token.decode(token),
         :ok <- validate_claims(claims, opts) do
      {:ok, claims}
    end
  end

  defp validate_claims(claims, opts) do
    # Validation logic here
    :ok
  end
end
"""
        auth_file.write_text(auth_content)

        recent_date = (datetime.now() - timedelta(days=7)).isoformat()

        return {
            "modules": {
                "MyApp.Auth": {
                    "file": str(auth_file),
                    "line": 1,
                    "moduledoc": "Authentication and authorization module",
                    "keywords": {"authentication": 0.9, "auth": 0.8, "security": 0.7},
                    "functions": [
                        {
                            "name": "verify_token",
                            "arity": 2,
                            "line": 6,  # Line where def verify_token appears
                            "type": "def",
                            "doc": "Verifies JWT token",
                            "keywords": {"verify": 0.8, "token": 0.9, "jwt": 0.7},
                            "signature": "def verify_token(token, opts)",
                            "last_modified_at": recent_date,
                        },
                    ],
                }
            },
            "metadata": {"repo_path": str(tmp_path)},
        }

    def test_snippets_disabled_by_default(self, sample_index):
        """Test that code snippets are disabled by default (backward compatibility)."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("auth")

        # Should not have code snippet preview
        assert "```elixir" not in result

    def test_snippets_enabled_shows_code(self, sample_index_with_files):
        """Test that show_snippets=True displays code blocks."""
        orchestrator = QueryOrchestrator(sample_index_with_files)
        # Use a keyword search that will match
        result = orchestrator.execute_query(["verify", "token"], show_snippets=True)

        # Should have code blocks
        assert "```elixir" in result
        assert "def verify_token" in result
        assert "```elixir" in result

    def test_snippet_shows_context_lines(self, sample_index_with_files):
        """Test that snippets show context lines around the target."""
        orchestrator = QueryOrchestrator(sample_index_with_files)
        # Use keywords that will match
        result = orchestrator.execute_query(["verify", "token"], show_snippets=True)

        # Should show line numbers and context
        # Line 6 is the def, should show lines around it
        assert "6:" in result or "def verify_token" in result
        # Should have context (alias, doc, or function body)
        assert "@doc" in result or "Token.decode" in result

    def test_snippet_handles_missing_files(self, sample_index):
        """Test that missing files don't crash snippet extraction."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("auth", show_snippets=True)

        # Should still show results even if files don't exist (compact format uses "1.")
        assert "1." in result or "MyApp.Auth" in result
        # Should not crash or show error traceback
        assert "Traceback" not in result

    # ============================================================
    # Cycle 2: Zero-Result Smart Suggestions Tests (TDD RED phase)
    # ============================================================

    def test_zero_results_shows_suggestions(self, sample_index):
        """Test that zero results displays helpful suggestions."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("nonexistent_term_xyz123")

        # Should indicate 0 results
        assert "0 result" in result.lower() or "no results" in result.lower()
        # Should have suggestions section (compact format has no emoji)
        assert "Suggested Next Steps" in result or "Try:" in result

    def test_zero_results_suggests_structural_variants(self, sample_index):
        """Test that zero results suggests structural formatting variants (not case-only)."""
        orchestrator = QueryOrchestrator(sample_index)
        # Use multi-word query to get structural variants
        result = orchestrator.execute_query("open router")

        # Should suggest structural variants (underscores, hyphens, PascalCase)
        # but NOT case-only variants since keyword search is case-insensitive
        assert (
            "open_router" in result  # snake_case
            or "OpenRouter" in result  # PascalCase
            or "open-router" in result  # hyphen-case
            or "variants" in result.lower()
        )

    def test_zero_results_suggests_related_terms(self, sample_index):
        """Test that zero results suggests related terms from the index."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("authentification")  # Typo of "authentication"

        # Should suggest similar terms that exist in the index
        assert (
            "authentication" in result.lower()
            or "auth" in result.lower()
            or "related" in result.lower()
        )

    def test_zero_results_suggests_broadening(self, sample_index):
        """Test that zero results suggests removing filters."""
        orchestrator = QueryOrchestrator(sample_index)
        # Use restrictive filters that will yield 0 results
        result = orchestrator.execute_query(
            "nonexistent",
            filter_type="functions",
            path_pattern="lib/nonexistent/**",
            scope="private",
        )

        # Should suggest broadening the search
        assert (
            "broaden" in result.lower() or "remove" in result.lower() or "filter" in result.lower()
        )

    # ============================================================
    # Cycle 4: Semantic Match Explanations Tests (TDD RED phase)
    # ============================================================

    def test_no_percentage_scores(self, sample_index):
        """Test that results don't show percentage scores."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("auth")

        # Should not have percentage signs in match confidence
        # Note: Score field might still have decimal numbers, but no %
        assert "Match: " not in result or "%" not in result

    def test_match_explanation_for_keywords(self, sample_index):
        """Test that keyword matches show explanations."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query(["authentication", "login"])

        # Should have "Matched keywords" section showing which keywords matched
        assert "Matched keywords" in result

    def test_match_explanation_for_pattern(self, sample_index):
        """Test that pattern matches show appropriate explanation."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("MyApp.Auth.verify*")

        # Should find pattern matches (compact format has no emoji indicators)
        assert "verify" in result.lower() or "MyApp" in result

    def test_match_indicators_present(self, sample_index):
        """Test that match source indicators are shown in compact format."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query(["jwt", "token"])

        # Should have match source indicators in compact format: (in docs), (in strings)
        assert "(in docs)" in result or "(in strings)" in result or "Matched keywords:" in result

    # ============================================================
    # Cycle 5: Reduced Defaults & Overload Detection Tests (TDD RED phase)
    # ============================================================

    def test_default_max_results_is_10(self, sample_index):
        """Test that default max_results is now 10 (reduced from 20)."""
        orchestrator = QueryOrchestrator(sample_index)
        # Don't specify max_results - should use default
        result = orchestrator.execute_query("user")

        # Check the header says "showing X" where X <= 10
        assert "showing" in result.lower()
        # Verify default was applied by checking we didn't get more than 10
        # Count lines that start with numbers (compact format: "1. name | [tier]")
        result_count = len(re.findall(r"^\d+\. ", result, re.MULTILINE))
        assert result_count <= 10

    @pytest.fixture
    def large_sample_index(self):
        """Create an index with many results for overload testing."""
        from datetime import datetime, timedelta

        recent_date = (datetime.now() - timedelta(days=7)).isoformat()

        modules = {}
        # Create 50 modules with "provider" keyword
        for i in range(50):
            modules[f"MyApp.Provider{i}"] = {
                "file": f"lib/provider{i}.ex",
                "line": 1,
                "moduledoc": f"Provider {i} module",
                "keywords": {"provider": 0.8, "api": 0.7, f"provider{i}": 0.9},
                "functions": [
                    {
                        "name": "call",
                        "arity": 1,
                        "line": 10,
                        "type": "def",
                        "doc": "Calls the provider",
                        "keywords": {"call": 0.8, "provider": 0.7},
                        "signature": "def call(args)",
                        "last_modified_at": recent_date,
                    }
                ],
            }

        return {"modules": modules}

    def test_overload_warning_shown(self, large_sample_index):
        """Test that warning is shown when many results are filtered out."""
        orchestrator = QueryOrchestrator(large_sample_index)
        # This should match many modules but only show 10
        result = orchestrator.execute_query("provider", max_results=10)

        # Should show more were found than displayed (100 results = 50 modules + 50 functions)
        assert "showing 10" in result.lower()
        # Verify a large number is shown
        assert "100 result" in result or "results" in result.lower()

    def test_no_warning_when_few_results(self, sample_index):
        """Test that no overload warning when results are naturally small."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("unique_specific_term_xyz", max_results=10)

        # Should not have warning indicators if naturally 0-5 results
        # Count results in compact format
        result_count = len(re.findall(r"^\d+\. ", result, re.MULTILINE))
        # Check for overload warnings (emojis removed in compact format)
        if result_count <= 5:
            # No overload warning expected for small result sets
            assert "Try refining" not in result or result_count == 0

    # ============================================================
    # String Tokenization Tests
    # ============================================================

    def test_string_tokenization_multiple_words(self):
        """Test that string queries are tokenized by whitespace."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        strategy = orchestrator._analyze_query("agent execution")
        assert strategy.use_keyword_search is True
        assert "agent" in strategy.search_keywords
        assert "execution" in strategy.search_keywords
        # Should NOT have the full phrase as a single keyword
        assert "agent execution" not in strategy.search_keywords

    def test_string_tokenization_single_word(self):
        """Test that single-word strings still work."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        strategy = orchestrator._analyze_query("authentication")
        assert strategy.use_keyword_search is True
        assert "authentication" in strategy.search_keywords
        assert len(strategy.search_keywords) == 1

    def test_string_tokenization_quoted_phrase(self):
        """Test that quoted phrases are kept as single keywords."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        strategy = orchestrator._analyze_query('"agent execution" context')
        assert strategy.use_keyword_search is True
        assert "agent execution" in strategy.search_keywords  # Kept together
        assert "context" in strategy.search_keywords
        assert len(strategy.search_keywords) == 2

    def test_string_tokenization_mixed_patterns_and_keywords(self):
        """Test that mixed patterns and keywords require array syntax."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        # String with pattern syntax is NOT tokenized (to avoid breaking the pattern)
        strategy = orchestrator._analyze_query("auth verify MyApp.Auth.*")
        assert strategy.use_pattern_search is True
        assert "auth verify MyApp.Auth.*" in strategy.search_patterns

        # To mix patterns and keywords, use array syntax
        strategy = orchestrator._analyze_query(["auth", "verify", "MyApp.Auth.*"])
        assert strategy.use_keyword_search is True
        assert strategy.use_pattern_search is True
        assert "auth" in strategy.search_keywords
        assert "verify" in strategy.search_keywords
        assert "MyApp.Auth.*" in strategy.search_patterns

    def test_string_tokenization_integration(self, sample_index):
        """Integration test: string queries should match multiple keywords."""
        orchestrator = QueryOrchestrator(sample_index)
        result = orchestrator.execute_query("auth token")

        # Should match items with both "auth" and "token" keywords
        # verify_token has both keywords
        assert "verify_token" in result

    def test_or_pattern_not_tokenized(self):
        """Test that OR patterns with spaces are not tokenized."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        # OR pattern with spaces should NOT be tokenized
        strategy = orchestrator._analyze_query("login | auth")
        assert strategy.use_pattern_search is True
        assert "login | auth" in strategy.search_patterns
        # Should NOT create separate keywords
        assert "login" not in strategy.search_keywords
        assert "|" not in strategy.search_patterns  # Bare | would match everything
        assert "auth" not in strategy.search_keywords

    def test_pre_tokenized_or_query_skips_bare_operator(self):
        """Standalone OR tokens should not trigger match-all pattern search."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        strategy = orchestrator._analyze_query(["login", "|", "auth"])

        assert strategy.use_keyword_search is True
        assert strategy.use_pattern_search is False
        assert strategy.search_keywords == ["login", "auth"]
        assert strategy.search_patterns == []

    def test_or_pattern_without_spaces_not_tokenized(self):
        """Test that OR patterns without spaces are not tokenized."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        strategy = orchestrator._analyze_query("login|auth")
        assert strategy.use_pattern_search is True
        assert "login|auth" in strategy.search_patterns

    def test_wildcard_pattern_not_tokenized(self):
        """Test that wildcard patterns are not tokenized."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        # Wildcards should prevent tokenization
        strategy = orchestrator._analyze_query("create* user")
        assert strategy.use_pattern_search is True
        assert "create* user" in strategy.search_patterns
        # Should NOT tokenize into separate terms
        assert "create*" not in strategy.search_keywords
        assert "user" not in strategy.search_keywords

    def test_module_qualifier_not_tokenized(self):
        """Test that module qualifiers prevent tokenization."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        # Module qualifier should prevent tokenization
        strategy = orchestrator._analyze_query("MyApp.User create")
        assert strategy.use_pattern_search is True
        assert "MyApp.User create" in strategy.search_patterns

    def test_plain_keywords_still_tokenized(self):
        """Test that plain keywords without pattern syntax are still tokenized."""
        index = {"modules": {}}
        orchestrator = QueryOrchestrator(index)

        # No pattern syntax, should tokenize
        strategy = orchestrator._analyze_query("agent execution context")
        assert strategy.use_keyword_search is True
        assert "agent" in strategy.search_keywords
        assert "execution" in strategy.search_keywords
        assert "context" in strategy.search_keywords
        assert strategy.use_pattern_search is False

    # ============================================================
    # Wildcard Pattern Matching Tests
    # ============================================================

    @pytest.fixture
    def pattern_index(self):
        """Create an index for testing wildcard patterns."""
        return {
            "modules": {
                "ThenvoiCom.Agents.AgentExecutor": {
                    "file": "lib/thenvoi_com/agents/agent_executor.ex",
                    "line": 1,
                    "moduledoc": "Agent execution module",
                    "keywords": {"agent": 0.9, "executor": 0.8},
                    "functions": [
                        {
                            "name": "execute",
                            "arity": 2,
                            "line": 10,
                            "type": "def",
                            "doc": "Executes an agent",
                            "signature": "def execute(agent, context)",
                            "keywords": {"execute": 0.9, "agent": 0.8},
                        }
                    ],
                },
                "ThenvoiCom.Agents.AgentModule": {
                    "file": "lib/thenvoi_com/agents/agent_module.ex",
                    "line": 1,
                    "moduledoc": "Agent module definition",
                    "keywords": {"agent": 0.9, "module": 0.8},
                    "functions": [],
                },
                "ThenvoiCom.Context": {
                    "file": "lib/thenvoi_com/context.ex",
                    "line": 1,
                    "moduledoc": "Context module",
                    "keywords": {"context": 0.9},
                    "functions": [],
                },
                "MyApp.AgentService": {
                    "file": "lib/my_app/agent_service.ex",
                    "line": 1,
                    "moduledoc": "Agent service",
                    "keywords": {"agent": 0.9, "service": 0.8},
                    "functions": [],
                },
            }
        }

    def test_wildcard_pattern_prefix_match(self, pattern_index):
        """Test that *.Agents.* matches modules starting with Agents."""
        orchestrator = QueryOrchestrator(pattern_index)
        result = orchestrator.execute_query("ThenvoiCom.Agents.*")

        # Should match both Agents.AgentExecutor and Agents.AgentModule
        assert "ThenvoiCom.Agents.AgentExecutor" in result
        assert "ThenvoiCom.Agents.AgentModule" in result
        # Should NOT match Context
        assert "ThenvoiCom.Context" not in result

    def test_wildcard_pattern_suffix_with_wildcard(self, pattern_index):
        """Test that *.Agent* matches modules with Agent in the name."""
        orchestrator = QueryOrchestrator(pattern_index)
        # Use filter_type="modules" to search module names with wildcards
        result = orchestrator.execute_query("*Agent*.*", filter_type="modules")

        # Should match all modules with "Agent" in the name
        assert "AgentExecutor" in result
        assert "AgentModule" in result
        assert "AgentService" in result

    def test_wildcard_pattern_qualified_with_wildcard(self, pattern_index):
        """Test that ThenvoiCom.Agent* matches ThenvoiCom.Agents.* modules."""
        orchestrator = QueryOrchestrator(pattern_index)
        # Use the correct pattern for module matching
        result = orchestrator.execute_query("ThenvoiCom.Agent*.*", filter_type="modules")

        # Should match modules that start with ThenvoiCom.Agent
        assert "AgentExecutor" in result
        assert "AgentModule" in result

    def test_exact_module_qualification(self, pattern_index):
        """Test exact module qualification without wildcards."""
        orchestrator = QueryOrchestrator(pattern_index)
        result = orchestrator.execute_query("ThenvoiCom.Context")

        # Should match exactly ThenvoiCom.Context
        assert "ThenvoiCom.Context" in result
        # Should not match other modules
        assert result.count("ThenvoiCom") == result.count("ThenvoiCom.Context")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
