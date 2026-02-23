"""Tests for SCIP regex-based string extractor."""

import pytest

from cicada.languages.scip.string_extractor import RegexStringExtractor


class TestRegexStringExtractorUniversal:
    """Tests for double-quoted string extraction (all languages)."""

    def test_extract_simple_string(self):
        extractor = RegexStringExtractor(language="typescript")
        result = extractor.extract_from_source('const msg = "hello world";')

        assert len(result) == 1
        assert result[0]["string"] == "hello world"
        assert result[0]["line"] == 1
        assert result[0]["function"] is None

    def test_extract_multiple_strings(self):
        extractor = RegexStringExtractor(language="go")
        source = 'fmt.Printf("%s %s", "hello", "world")'
        result = extractor.extract_from_source(source)

        assert len(result) == 3
        assert result[0]["string"] == "%s %s"
        assert result[1]["string"] == "hello"
        assert result[2]["string"] == "world"

    def test_extract_multiline_source(self):
        extractor = RegexStringExtractor(language="java")
        source = 'class Foo {\n    String a = "first";\n    String b = "second";\n}'
        result = extractor.extract_from_source(source)

        assert len(result) == 2
        assert result[0]["string"] == "first"
        assert result[0]["line"] == 2
        assert result[1]["string"] == "second"
        assert result[1]["line"] == 3

    def test_skip_short_strings(self):
        extractor = RegexStringExtractor(language="typescript", min_length=5)
        source = 'let x = "ab"; let y = "hello";'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "hello"

    def test_skip_whitespace_only_strings(self):
        extractor = RegexStringExtractor(language="typescript", min_length=1)
        source = 'let x = "   "; let y = "hello";'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "hello"

    def test_handle_escaped_quotes(self):
        extractor = RegexStringExtractor(language="typescript")
        source = r'let msg = "say \"hello\"";'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == r"say \"hello\""

    def test_skip_comment_strings(self):
        extractor = RegexStringExtractor(language="typescript")
        source = '// let x = "commented out";'
        result = extractor.extract_from_source(source)

        assert len(result) == 0

    def test_inline_comment_not_stripped(self):
        """Inline comments are not stripped to avoid truncating URLs in strings."""
        extractor = RegexStringExtractor(language="typescript")
        source = 'let x = "real"; // "fake"'
        result = extractor.extract_from_source(source)

        # Both strings are extracted since only full-line comments are stripped
        assert len(result) == 2
        assert result[0]["string"] == "real"
        assert result[1]["string"] == "fake"

    def test_empty_source(self):
        extractor = RegexStringExtractor(language="typescript")
        assert extractor.extract_from_source("") == []

    def test_no_strings(self):
        extractor = RegexStringExtractor(language="go")
        source = "func add(a int, b int) int { return a + b }"
        assert extractor.extract_from_source(source) == []

    def test_default_min_length(self):
        extractor = RegexStringExtractor(language="typescript")
        assert extractor.min_length == 3

    def test_unknown_language_uses_double_quotes(self):
        extractor = RegexStringExtractor(language="unknown_lang")
        source = 'x = "works fine"'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "works fine"


class TestRegexStringExtractorSingleQuote:
    """Tests for single-quoted string extraction (JS, TS, Ruby)."""

    def test_typescript_single_quotes(self):
        extractor = RegexStringExtractor(language="typescript")
        source = "const msg = 'hello world';"
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "hello world"

    def test_javascript_single_quotes(self):
        extractor = RegexStringExtractor(language="javascript")
        source = "var msg = 'hello world';"
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "hello world"

    def test_ruby_single_quotes(self):
        extractor = RegexStringExtractor(language="ruby")
        source = "msg = 'hello world'"
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "hello world"

    def test_go_no_single_quotes(self):
        """Go doesn't use single quotes for strings (they're rune literals)."""
        extractor = RegexStringExtractor(language="go")
        source = "x := 'a'"
        result = extractor.extract_from_source(source)

        assert len(result) == 0

    def test_java_no_single_quotes(self):
        extractor = RegexStringExtractor(language="java")
        source = "char c = 'a';"
        result = extractor.extract_from_source(source)

        assert len(result) == 0

    def test_mixed_quote_types(self):
        extractor = RegexStringExtractor(language="typescript")
        source = """const a = "double";
const b = 'single';"""
        result = extractor.extract_from_source(source)

        assert len(result) == 2
        assert result[0]["string"] == "double"
        assert result[1]["string"] == "single"


class TestRegexStringExtractorBacktick:
    """Tests for backtick/raw string extraction (Go)."""

    def test_go_backtick_string(self):
        extractor = RegexStringExtractor(language="go")
        source = "sql := `SELECT * FROM users`"
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "SELECT * FROM users"

    def test_typescript_no_backtick(self):
        """TS template literals are intentionally not extracted (multi-line)."""
        extractor = RegexStringExtractor(language="typescript")
        source = "const msg = `hello world`;"
        result = extractor.extract_from_source(source)

        assert len(result) == 0

    def test_go_mixed_string_types(self):
        extractor = RegexStringExtractor(language="go")
        source = 'a := "quoted"\nb := `raw`'
        result = extractor.extract_from_source(source)

        assert len(result) == 2
        assert result[0]["string"] == "quoted"
        assert result[1]["string"] == "raw"


class TestRegexStringExtractorCommentStripping:
    """Tests for comment stripping across languages."""

    def test_ruby_hash_comments(self):
        extractor = RegexStringExtractor(language="ruby")
        source = '# msg = "commented out"'
        result = extractor.extract_from_source(source)

        assert len(result) == 0

    def test_ruby_inline_comment_not_stripped(self):
        """Inline # comments are not stripped to avoid truncating strings."""
        extractor = RegexStringExtractor(language="ruby")
        source = "msg = 'real' # 'fake'"
        result = extractor.extract_from_source(source)

        # Both strings extracted since only full-line comments are stripped
        assert len(result) == 2
        assert result[0]["string"] == "real"
        assert result[1]["string"] == "fake"

    def test_full_line_comment_languages(self):
        """All C-family languages strip full-line // comments."""
        for lang in ["typescript", "javascript", "go", "rust", "java", "scala", "csharp"]:
            extractor = RegexStringExtractor(language=lang)
            source = '// "commented"'
            result = extractor.extract_from_source(source)
            assert len(result) == 0, f"{lang} should strip full-line // comments"

    def test_indented_full_line_comment(self):
        """Full-line comments with leading whitespace are still stripped."""
        extractor = RegexStringExtractor(language="typescript")
        source = '    // "commented"'
        result = extractor.extract_from_source(source)
        assert len(result) == 0


class TestRegexStringExtractorURLPreservation:
    """Regression tests for comment markers inside string literals."""

    def test_url_in_double_quoted_string(self):
        """URLs with // should not be truncated."""
        extractor = RegexStringExtractor(language="typescript")
        source = 'const url = "http://example.com/api";'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "http://example.com/api"

    def test_url_in_single_quoted_string(self):
        extractor = RegexStringExtractor(language="javascript")
        source = "const url = 'https://api.example.com';"
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "https://api.example.com"

    def test_ruby_hash_in_string(self):
        """Ruby # inside a string should not cause truncation."""
        extractor = RegexStringExtractor(language="ruby")
        source = 'msg = "value #1 is important"'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "value #1 is important"

    def test_go_url_in_string(self):
        extractor = RegexStringExtractor(language="go")
        source = 'url := "http://localhost:8080/path"'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "http://localhost:8080/path"

    def test_dart_single_quote_support(self):
        """Dart uses single-quoted strings by convention."""
        extractor = RegexStringExtractor(language="dart")
        source = "var msg = 'hello world';"
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "hello world"


class TestRegexStringExtractorBlockComments:
    """Tests for /* ... */ block comment stripping."""

    def test_single_line_block_comment(self):
        extractor = RegexStringExtractor(language="java")
        source = '/* "commented out" */'
        result = extractor.extract_from_source(source)
        assert len(result) == 0

    def test_multiline_block_comment(self):
        extractor = RegexStringExtractor(language="csharp")
        source = '/*\n"first line"\n"second line"\n*/'
        result = extractor.extract_from_source(source)
        assert len(result) == 0

    def test_block_comment_preserves_code_before(self):
        extractor = RegexStringExtractor(language="java")
        source = 'String x = "real"; /* "fake" */'
        result = extractor.extract_from_source(source)
        assert len(result) == 1
        assert result[0]["string"] == "real"

    def test_block_comment_preserves_code_after(self):
        extractor = RegexStringExtractor(language="java")
        source = '/* "fake" */ String x = "real";'
        result = extractor.extract_from_source(source)
        assert len(result) == 1
        assert result[0]["string"] == "real"

    def test_block_comment_spanning_lines(self):
        extractor = RegexStringExtractor(language="go")
        source = 'x := "before"\n/* start\n"inside"\nend */\ny := "after"'
        result = extractor.extract_from_source(source)
        assert len(result) == 2
        assert result[0]["string"] == "before"
        assert result[1]["string"] == "after"

    def test_multiple_block_comments_one_line(self):
        extractor = RegexStringExtractor(language="java")
        source = '"real1" /* "fake1" */ "real2" /* "fake2" */ "real3"'
        result = extractor.extract_from_source(source)
        assert len(result) == 3
        strings = [r["string"] for r in result]
        assert strings == ["real1", "real2", "real3"]

    def test_ruby_no_block_comment_stripping(self):
        """Ruby doesn't use /* */ so these should be treated as code."""
        extractor = RegexStringExtractor(language="ruby")
        source = '/* "still extracted" */'
        result = extractor.extract_from_source(source)
        assert len(result) == 1
        assert result[0]["string"] == "still extracted"

    def test_block_comment_languages(self):
        """C-family languages should strip block comments."""
        for lang in ["go", "java", "scala", "c", "cpp", "csharp", "dart", "typescript"]:
            extractor = RegexStringExtractor(language=lang)
            source = '/* "commented" */'
            result = extractor.extract_from_source(source)
            assert len(result) == 0, f"{lang} should strip block comments"


class TestRegexStringExtractorVBComments:
    """Tests for Visual Basic comment handling."""

    def test_vb_single_quote_comment(self):
        extractor = RegexStringExtractor(language="vb")
        source = '\' Dim x As String = "commented out"'
        result = extractor.extract_from_source(source)
        assert len(result) == 0

    def test_vb_indented_comment(self):
        extractor = RegexStringExtractor(language="vb")
        source = '    \' "commented out"'
        result = extractor.extract_from_source(source)
        assert len(result) == 0

    def test_vb_code_not_stripped(self):
        extractor = RegexStringExtractor(language="vb")
        source = 'Dim msg As String = "hello world"'
        result = extractor.extract_from_source(source)
        assert len(result) == 1
        assert result[0]["string"] == "hello world"
