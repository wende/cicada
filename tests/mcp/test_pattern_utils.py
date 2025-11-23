"""
Comprehensive edge case tests for cicada/mcp/pattern_utils.py

Tests cover all edge cases for pattern matching utilities including:
- Wildcard detection and matching
- Pattern matching with special cases (*.Prefix patterns)
- OR pattern splitting
- Function pattern parsing
- FunctionPattern matching
"""

import pytest

from cicada.mcp.pattern_utils import (
    FunctionPattern,
    has_wildcards,
    match_any_pattern,
    match_wildcard,
    matches_pattern,
    parse_function_patterns,
    split_or_patterns,
)


class TestHasWildcards:
    """Tests for has_wildcards function"""

    def test_detects_asterisk_wildcard(self):
        """Should detect * wildcard"""
        assert has_wildcards("foo*")
        assert has_wildcards("*foo")
        assert has_wildcards("foo*bar")
        assert has_wildcards("*")

    def test_detects_pipe_or_operator(self):
        """Should detect | OR operator"""
        assert has_wildcards("foo|bar")
        assert has_wildcards("|foo")
        assert has_wildcards("foo|")
        assert has_wildcards("|")

    def test_detects_both_wildcards(self):
        """Should detect both * and | wildcards"""
        assert has_wildcards("foo*|bar")
        assert has_wildcards("*|*")
        assert has_wildcards("foo*bar|baz")

    def test_no_wildcards(self):
        """Should return False when no wildcards present"""
        assert not has_wildcards("foo")
        assert not has_wildcards("FooBar")
        assert not has_wildcards("foo.bar.baz")
        assert not has_wildcards("")

    def test_question_mark_not_wildcard(self):
        """Should not treat ? as a wildcard (only * and |)"""
        assert not has_wildcards("foo?")
        assert not has_wildcards("?foo")
        assert not has_wildcards("foo?bar")


class TestMatchWildcard:
    """Tests for match_wildcard function"""

    def test_exact_match_no_wildcard(self):
        """Should match exact strings when no wildcard present"""
        assert match_wildcard("foo", "foo")
        assert match_wildcard("FooBar", "foobar")  # case insensitive

    def test_prefix_wildcard(self):
        """Should match prefix patterns"""
        assert match_wildcard("foo*", "foobar")
        assert match_wildcard("foo*", "foo")
        assert match_wildcard("foo*", "foobarbaz")
        assert not match_wildcard("foo*", "barfoo")

    def test_suffix_wildcard(self):
        """Should match suffix patterns"""
        assert match_wildcard("*bar", "foobar")
        assert match_wildcard("*bar", "bar")
        assert match_wildcard("*bar", "bazfoobar")
        assert not match_wildcard("*bar", "barfoo")

    def test_middle_wildcard(self):
        """Should match patterns with wildcard in middle"""
        assert match_wildcard("foo*bar", "foobar")
        assert match_wildcard("foo*bar", "foobazbar")
        assert match_wildcard("foo*bar", "foo_anything_bar")
        assert not match_wildcard("foo*bar", "foobaz")

    def test_multiple_wildcards(self):
        """Should match patterns with multiple wildcards"""
        assert match_wildcard("*foo*bar*", "foobar")
        assert match_wildcard("*foo*bar*", "xfooyybarzz")
        assert match_wildcard("a*b*c*", "abc")
        assert match_wildcard("a*b*c*", "aXbYcZ")

    def test_single_asterisk_matches_everything(self):
        """Should match any string with single * pattern"""
        assert match_wildcard("*", "anything")
        assert match_wildcard("*", "")
        assert match_wildcard("*", "foo.bar.baz")

    def test_case_insensitive(self):
        """Should perform case-insensitive matching"""
        assert match_wildcard("FOO*", "foobar")
        assert match_wildcard("foo*", "FOOBAR")
        assert match_wildcard("FoO*BaR", "fooXbar")

    def test_empty_pattern_and_text(self):
        """Should handle empty strings"""
        assert match_wildcard("", "")
        assert not match_wildcard("", "foo")
        assert not match_wildcard("foo", "")

    def test_rejects_question_mark(self):
        """Should return False for patterns containing ?"""
        assert not match_wildcard("foo?", "foox")
        assert not match_wildcard("?foo", "xfoo")
        assert not match_wildcard("foo?bar", "fooxbar")

    def test_special_characters(self):
        """Should handle special characters in patterns and text"""
        assert match_wildcard("foo-*", "foo-bar")
        assert match_wildcard("foo_*", "foo_bar")
        assert match_wildcard("foo.*", "foo.bar")
        assert match_wildcard("*@*", "foo@bar")


class TestMatchesPattern:
    """Tests for matches_pattern function with special *.Prefix handling"""

    def test_none_pattern_matches_everything(self):
        """Should match any text when pattern is None"""
        assert matches_pattern(None, "anything")
        assert matches_pattern(None, "")
        assert matches_pattern(None, "Foo.Bar.Baz")

    def test_single_asterisk_matches_everything(self):
        """Should match any text when pattern is '*'"""
        assert matches_pattern("*", "anything")
        assert matches_pattern("*", "")
        assert matches_pattern("*", "Foo.Bar.Baz")

    def test_exact_match_no_wildcard(self):
        """Should perform exact case-insensitive match without wildcards"""
        assert matches_pattern("foo", "foo")
        assert matches_pattern("foo", "FOO")
        assert matches_pattern("FooBar", "foobar")
        assert not matches_pattern("foo", "bar")

    def test_star_prefix_exact_match(self):
        """*.Something should match 'Something' exactly"""
        assert matches_pattern("*.Something", "Something")
        assert matches_pattern("*.User", "User")
        assert matches_pattern("*.Agent", "agent")  # case insensitive

    def test_star_prefix_with_module_prefix(self):
        """*.Something should match 'X.Something' (suffix match)"""
        assert matches_pattern("*.Something", "MyApp.Something")
        assert matches_pattern("*.User", "MyProject.User")
        assert matches_pattern("*.Agent", "ThenvoiCom.Agent")

    def test_star_prefix_with_module_suffix(self):
        """*.Something should match 'Something.Other' (prefix match)"""
        assert matches_pattern("*.Something", "Something.Other")
        assert matches_pattern("*.User", "User.Handler")
        assert matches_pattern("*.Agents", "Agents.AgentExecutor")

    def test_star_prefix_component_match(self):
        """*.Something should match 'X.Something.Y' (component match)"""
        assert matches_pattern("*.Something", "MyApp.Something.Other")
        assert matches_pattern("*.User", "Project.User.Handler")
        assert matches_pattern("*.Agents", "ThenvoiCom.Agents.AgentExecutor")

    def test_star_prefix_with_wildcard_suffix(self):
        """*.Prefix* should match using fnmatch on tails"""
        assert matches_pattern("*.Agent*", "AgentExecutor")
        assert matches_pattern("*.Agent*", "ThenvoiCom.AgentService")
        assert matches_pattern("*.Agent*", "MyApp.Agents.AgentModule")

    def test_star_prefix_wildcard_multiple_components(self):
        """*.ThenvoiCom.Agents should match various module paths"""
        pattern = "*.ThenvoiCom.Agents"
        assert matches_pattern(pattern, "ThenvoiCom.Agents")
        assert matches_pattern(pattern, "MyApp.ThenvoiCom.Agents")
        assert matches_pattern(pattern, "ThenvoiCom.Agents.AgentExecutor")
        assert matches_pattern(pattern, "MyApp.ThenvoiCom.Agents.AgentExecutor")

    def test_star_prefix_does_not_match_partial(self):
        """*.Something should not match 'SomethingElse' (without wildcard)"""
        assert not matches_pattern("*.User", "UserHandler")
        assert not matches_pattern("*.Agent", "AgentService")
        assert not matches_pattern("*.Foo", "FooBar")

    def test_regular_wildcard_patterns(self):
        """Should handle regular wildcard patterns without *.prefix"""
        assert matches_pattern("create*", "create_user")
        assert matches_pattern("*user*", "create_user_account")
        assert matches_pattern("test_*", "test_foo")

    def test_case_insensitivity(self):
        """Should be case-insensitive for all patterns"""
        assert matches_pattern("*.Something", "SOMETHING")
        assert matches_pattern("*.MyModule", "myapp.mymodule")
        assert matches_pattern("FOO*", "foobar")

    def test_empty_pattern(self):
        """Should handle empty pattern (should match like None)"""
        assert matches_pattern("", "anything")

    def test_complex_module_paths(self):
        """Should handle complex nested module paths"""
        assert matches_pattern("*.Agents", "A.B.C.D.Agents")
        assert matches_pattern("*.Agents", "Agents.A.B.C")
        assert matches_pattern("*.Agents", "A.Agents.B")

    def test_single_dot_patterns(self):
        """Should handle patterns with single dot"""
        assert matches_pattern("Foo.Bar", "foo.bar")
        assert not matches_pattern("Foo.Bar", "Foo.Baz")

    def test_star_prefix_empty_suffix(self):
        """*. with empty suffix should behave like * (edge case)"""
        # This is an edge case - *. without a suffix
        assert matches_pattern("*.", "")


class TestMatchAnyPattern:
    """Tests for match_any_pattern function"""

    def test_matches_first_pattern(self):
        """Should return True if first pattern matches"""
        assert match_any_pattern(["foo*", "bar*"], "foobar")

    def test_matches_second_pattern(self):
        """Should return True if second pattern matches"""
        assert match_any_pattern(["foo*", "bar*"], "barbaz")

    def test_matches_any_of_multiple(self):
        """Should return True if any pattern matches"""
        patterns = ["create*", "update*", "delete*"]
        assert match_any_pattern(patterns, "create_user")
        assert match_any_pattern(patterns, "update_user")
        assert match_any_pattern(patterns, "delete_user")

    def test_no_match(self):
        """Should return False if no patterns match"""
        assert not match_any_pattern(["foo*", "bar*"], "baz")

    def test_empty_pattern_list(self):
        """Should return False for empty pattern list"""
        assert not match_any_pattern([], "anything")

    def test_strips_whitespace(self):
        """Should strip whitespace from patterns"""
        assert match_any_pattern([" foo* ", " bar* "], "foobar")

    def test_ignores_empty_patterns(self):
        """Should ignore empty/whitespace-only patterns"""
        assert match_any_pattern(["", "  ", "foo*"], "foobar")
        assert not match_any_pattern(["", "  ", "bar*"], "foobar")

    def test_with_star_prefix_patterns(self):
        """Should work with *.Prefix patterns"""
        patterns = ["*.User", "*.Agent*"]
        assert match_any_pattern(patterns, "MyApp.User")
        assert match_any_pattern(patterns, "AgentExecutor")


class TestSplitOrPatterns:
    """Tests for split_or_patterns function"""

    def test_single_pattern(self):
        """Should return single pattern in list"""
        assert split_or_patterns("foo") == ["foo"]

    def test_two_patterns(self):
        """Should split two patterns by |"""
        assert split_or_patterns("foo|bar") == ["foo", "bar"]

    def test_multiple_patterns(self):
        """Should split multiple patterns"""
        result = split_or_patterns("foo|bar|baz|qux")
        assert result == ["foo", "bar", "baz", "qux"]

    def test_strips_whitespace(self):
        """Should strip whitespace from each pattern"""
        result = split_or_patterns(" foo | bar | baz ")
        assert result == ["foo", "bar", "baz"]

    def test_empty_string(self):
        """Should handle empty string"""
        assert split_or_patterns("") == [""]

    def test_pipe_only(self):
        """Should handle pipe-only input"""
        result = split_or_patterns("|")
        assert result == ["", ""]

    def test_preserves_wildcards(self):
        """Should preserve wildcards in patterns"""
        result = split_or_patterns("foo*|*bar|baz*qux")
        assert result == ["foo*", "*bar", "baz*qux"]

    def test_multiple_pipes(self):
        """Should handle multiple consecutive pipes"""
        result = split_or_patterns("foo||bar")
        assert result == ["foo", "", "bar"]


class TestFunctionPatternFromString:
    """Tests for FunctionPattern.from_string parsing"""

    def test_wildcard_only(self):
        """Should parse bare wildcard as name pattern"""
        pattern = FunctionPattern.from_string("*")
        assert pattern.file is None
        assert pattern.module is None
        assert pattern.name == "*"
        assert pattern.arity is None

    def test_empty_string_defaults_to_wildcard(self):
        """Should treat empty string as wildcard"""
        pattern = FunctionPattern.from_string("")
        assert pattern.name == "*"

    def test_simple_function_name(self):
        """Should parse simple function name"""
        pattern = FunctionPattern.from_string("create_user")
        assert pattern.file is None
        assert pattern.module is None
        assert pattern.name == "create_user"
        assert pattern.arity is None

    def test_function_with_arity(self):
        """Should parse function name with arity"""
        pattern = FunctionPattern.from_string("create_user/2")
        assert pattern.name == "create_user"
        assert pattern.arity == 2

    def test_module_qualified_function(self):
        """Should parse module.function pattern"""
        pattern = FunctionPattern.from_string("User.create_user")
        assert pattern.module == "*.User"  # Auto-prefixed with *.
        assert pattern.name == "create_user"

    def test_module_qualified_with_arity(self):
        """Should parse module.function/arity pattern"""
        pattern = FunctionPattern.from_string("User.create_user/2")
        assert pattern.module == "*.User"
        assert pattern.name == "create_user"
        assert pattern.arity == 2

    def test_nested_module_path(self):
        """Should parse nested module paths"""
        pattern = FunctionPattern.from_string("MyApp.User.create_user")
        assert pattern.module == "*.MyApp.User"
        assert pattern.name == "create_user"

    def test_file_path_prefix(self):
        """Should parse file path prefix"""
        pattern = FunctionPattern.from_string("lib/user.ex:create_user")
        assert pattern.file == "lib/user.ex"
        assert pattern.name == "create_user"

    def test_file_path_with_module(self):
        """Should parse file path with module and function"""
        pattern = FunctionPattern.from_string("lib/user.ex:User.create_user")
        assert pattern.file == "lib/user.ex"
        assert pattern.module == "*.User"
        assert pattern.name == "create_user"

    def test_file_path_with_arity(self):
        """Should parse file path with arity"""
        pattern = FunctionPattern.from_string("lib/user.ex:create_user/2")
        assert pattern.file == "lib/user.ex"
        assert pattern.name == "create_user"
        assert pattern.arity == 2

    def test_complete_pattern(self):
        """Should parse complete pattern with all components"""
        pattern = FunctionPattern.from_string("lib/user.ex:MyApp.User.create_user/2")
        assert pattern.file == "lib/user.ex"
        assert pattern.module == "*.MyApp.User"
        assert pattern.name == "create_user"
        assert pattern.arity == 2

    def test_wildcard_function_with_module(self):
        """Should parse wildcard function with module"""
        pattern = FunctionPattern.from_string("User.*")
        assert pattern.module == "*.User"
        assert pattern.name == "*"

    def test_wildcard_module_not_auto_prefixed(self):
        """Should not auto-prefix if module already has wildcard"""
        pattern = FunctionPattern.from_string("*.User.create")
        assert pattern.module == "*.User"  # Already has *., don't add another

    def test_or_pattern_not_auto_prefixed(self):
        """Should not auto-prefix if module contains OR operator"""
        pattern = FunctionPattern.from_string("User|Agent.create")
        assert pattern.module == "User|Agent"  # No auto-prefix for OR

    def test_arity_with_invalid_number(self):
        """Should ignore invalid arity numbers"""
        pattern = FunctionPattern.from_string("create/abc")
        assert pattern.name == "create"
        assert pattern.arity is None  # Invalid arity ignored

    def test_arity_zero(self):
        """Should parse arity 0"""
        pattern = FunctionPattern.from_string("create/0")
        assert pattern.arity == 0

    def test_high_arity(self):
        """Should parse high arity values"""
        pattern = FunctionPattern.from_string("create/10")
        assert pattern.arity == 10

    def test_file_detection_by_extension(self):
        """Should detect file by .ex or .exs extension"""
        pattern1 = FunctionPattern.from_string("user.ex:create")
        assert pattern1.file == "user.ex"

        pattern2 = FunctionPattern.from_string("user_test.exs:test_create")
        assert pattern2.file == "user_test.exs"

    def test_file_detection_by_slash(self):
        """Should detect file by presence of / in path"""
        pattern = FunctionPattern.from_string("lib/user:create")
        assert pattern.file == "lib/user"
        assert pattern.name == "create"

    def test_colon_without_file_path(self):
        """Should not treat colon as file separator if no path indicators"""
        # If there's no / or .ex/.exs before :, it's not a file path
        # The colon stays as part of the pattern name
        pattern = FunctionPattern.from_string("User:create")
        assert pattern.file is None
        # Without / or .ex/.exs, the colon isn't treated as a separator
        # So the whole string "User:create" becomes the name
        assert pattern.name == "User:create"

    def test_whitespace_trimming(self):
        """Should trim whitespace from pattern"""
        pattern = FunctionPattern.from_string("  User.create  ")
        assert pattern.module == "*.User"
        assert pattern.name == "create"

    def test_multiple_dots_in_function_name(self):
        """Should use rightmost dot for module/function split"""
        pattern = FunctionPattern.from_string("A.B.C.D")
        assert pattern.module == "*.A.B.C"
        assert pattern.name == "D"

    def test_dot_in_file_path(self):
        """Should handle dots in file paths correctly"""
        pattern = FunctionPattern.from_string("lib/my.app/user.ex:create")
        assert pattern.file == "lib/my.app/user.ex"
        assert pattern.name == "create"


class TestFunctionPatternMatches:
    """Tests for FunctionPattern.matches method"""

    @pytest.fixture
    def sample_function(self):
        """Sample function dict for testing"""
        return {"name": "create_user", "arity": 2, "line": 10}

    def test_matches_any_pattern(self, sample_function):
        """Default pattern should match anything"""
        pattern = FunctionPattern()  # Defaults to name="*"
        assert pattern.matches("Any.Module", "any/file.ex", sample_function)

    def test_matches_function_name(self, sample_function):
        """Should match by function name"""
        pattern = FunctionPattern(name="create_user")
        assert pattern.matches("Any.Module", "any/file.ex", sample_function)

        pattern = FunctionPattern(name="update_user")
        assert not pattern.matches("Any.Module", "any/file.ex", sample_function)

    def test_matches_function_name_wildcard(self, sample_function):
        """Should match function name with wildcards"""
        pattern = FunctionPattern(name="create*")
        assert pattern.matches("Any.Module", "any/file.ex", sample_function)

        pattern = FunctionPattern(name="*user")
        assert pattern.matches("Any.Module", "any/file.ex", sample_function)

    def test_matches_arity(self, sample_function):
        """Should match by arity"""
        pattern = FunctionPattern(name="create_user", arity=2)
        assert pattern.matches("Any.Module", "any/file.ex", sample_function)

        pattern = FunctionPattern(name="create_user", arity=1)
        assert not pattern.matches("Any.Module", "any/file.ex", sample_function)

    def test_none_arity_matches_any(self, sample_function):
        """None arity should match any arity"""
        pattern = FunctionPattern(name="create_user", arity=None)
        assert pattern.matches("Any.Module", "any/file.ex", sample_function)

    def test_matches_module(self, sample_function):
        """Should match by module name"""
        pattern = FunctionPattern(module="*.User", name="create_user")
        assert pattern.matches("MyApp.User", "any/file.ex", sample_function)
        assert not pattern.matches("MyApp.Account", "any/file.ex", sample_function)

    def test_matches_module_with_wildcard(self, sample_function):
        """Should match module with wildcards"""
        pattern = FunctionPattern(module="*.User*", name="create_user")
        assert pattern.matches("MyApp.UserService", "any/file.ex", sample_function)
        assert pattern.matches("User", "any/file.ex", sample_function)

    def test_matches_file_path(self, sample_function):
        """Should match by file path"""
        pattern = FunctionPattern(file="lib/user.ex", name="create_user")
        assert pattern.matches("Any.Module", "lib/user.ex", sample_function)
        assert not pattern.matches("Any.Module", "lib/account.ex", sample_function)

    def test_matches_file_path_wildcard(self, sample_function):
        """Should match file path with wildcards"""
        pattern = FunctionPattern(file="lib/*.ex", name="create_user")
        assert pattern.matches("Any.Module", "lib/user.ex", sample_function)
        assert pattern.matches("Any.Module", "lib/account.ex", sample_function)
        assert not pattern.matches("Any.Module", "test/user.ex", sample_function)

    def test_matches_all_criteria(self, sample_function):
        """Should match only when all criteria match"""
        pattern = FunctionPattern(
            file="lib/user.ex", module="*.User", name="create_user", arity=2
        )
        # All match
        assert pattern.matches("MyApp.User", "lib/user.ex", sample_function)

        # Wrong file
        assert not pattern.matches("MyApp.User", "lib/account.ex", sample_function)

        # Wrong module
        assert not pattern.matches("MyApp.Account", "lib/user.ex", sample_function)

        # Wrong arity
        wrong_arity_func = {"name": "create_user", "arity": 1, "line": 10}
        assert not pattern.matches("MyApp.User", "lib/user.ex", wrong_arity_func)


class TestParseFunctionPatterns:
    """Tests for parse_function_patterns function"""

    def test_none_returns_default_pattern(self):
        """Should return default wildcard pattern for None"""
        patterns = parse_function_patterns(None)
        assert len(patterns) == 1
        assert patterns[0].name == "*"

    def test_empty_string_returns_default_pattern(self):
        """Should return default wildcard pattern for empty string"""
        patterns = parse_function_patterns("")
        assert len(patterns) == 1
        assert patterns[0].name == "*"

    def test_single_pattern(self):
        """Should parse single pattern"""
        patterns = parse_function_patterns("create_user")
        assert len(patterns) == 1
        assert patterns[0].name == "create_user"

    def test_or_pattern_two_alternatives(self):
        """Should parse OR pattern with two alternatives"""
        patterns = parse_function_patterns("create_user|update_user")
        assert len(patterns) == 2
        assert patterns[0].name == "create_user"
        assert patterns[1].name == "update_user"

    def test_or_pattern_multiple_alternatives(self):
        """Should parse OR pattern with multiple alternatives"""
        patterns = parse_function_patterns("create*|update*|delete*")
        assert len(patterns) == 3
        assert patterns[0].name == "create*"
        assert patterns[1].name == "update*"
        assert patterns[2].name == "delete*"

    def test_strips_whitespace(self):
        """Should strip whitespace from OR alternatives"""
        patterns = parse_function_patterns(" create | update | delete ")
        assert len(patterns) == 3
        assert patterns[0].name == "create"
        assert patterns[1].name == "update"
        assert patterns[2].name == "delete"

    def test_complex_patterns_with_or(self):
        """Should parse complex patterns with OR"""
        patterns = parse_function_patterns("User.create*|Account.update*/2")
        assert len(patterns) == 2
        assert patterns[0].module == "*.User"
        assert patterns[0].name == "create*"
        assert patterns[1].module == "*.Account"
        assert patterns[1].name == "update*"
        assert patterns[1].arity == 2

    def test_empty_alternatives_filtered(self):
        """Should filter out empty alternatives from OR pattern"""
        patterns = parse_function_patterns("create||update")
        assert len(patterns) == 2
        assert patterns[0].name == "create"
        assert patterns[1].name == "update"

    def test_all_empty_alternatives_returns_default(self):
        """Should return default pattern if all alternatives are empty"""
        patterns = parse_function_patterns("  |  |  ")
        assert len(patterns) == 1
        assert patterns[0].name == "*"


class TestEdgeCases:
    """Edge case tests for pattern utilities"""

    def test_match_wildcard_with_backslashes(self):
        """Should handle backslashes in patterns (Windows paths)"""
        # fnmatch should handle this, but good to verify
        assert match_wildcard("*\\test\\*", "lib\\test\\foo.ex")

    def test_matches_pattern_with_numbers(self):
        """Should handle numbers in module names"""
        assert matches_pattern("*.Module2", "MyApp.Module2")
        assert matches_pattern("*.V1.API", "MyApp.V1.API")

    def test_matches_pattern_with_underscores(self):
        """Should handle underscores in module names"""
        assert matches_pattern("*.My_Module", "MyApp.My_Module")
        assert matches_pattern("*.Agent_Executor", "ThenvoiCom.Agent_Executor")

    def test_function_pattern_with_empty_arity(self):
        """Should handle arity parsing edge cases"""
        pattern = FunctionPattern.from_string("create/")
        assert pattern.name == "create"
        assert pattern.arity is None

    def test_function_pattern_with_negative_arity(self):
        """Should parse negative arity (even though it's unusual)"""
        pattern = FunctionPattern.from_string("create/-1")
        assert pattern.arity == -1

    def test_match_any_pattern_with_duplicates(self):
        """Should handle duplicate patterns in list"""
        assert match_any_pattern(["foo*", "foo*", "bar*"], "foobar")

    def test_split_or_patterns_with_unicode(self):
        """Should handle unicode in OR patterns"""
        result = split_or_patterns("функция|función|function")
        assert len(result) == 3
        assert "функция" in result
        assert "función" in result

    def test_matches_pattern_deeply_nested(self):
        """Should handle very deeply nested module paths"""
        pattern = "*.Z"
        text = "A.B.C.D.E.F.G.H.I.J.K.L.M.N.O.P.Q.R.S.T.U.V.W.X.Y.Z"
        assert matches_pattern(pattern, text)

    def test_function_pattern_matches_case_insensitive(self):
        """FunctionPattern matching should be case-insensitive"""
        pattern = FunctionPattern(module="*.USER", name="CREATE_USER")
        func = {"name": "create_user", "arity": 2, "line": 10}
        assert pattern.matches("MyApp.User", "lib/user.ex", func)
