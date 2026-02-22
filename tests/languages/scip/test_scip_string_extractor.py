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

    def test_partial_comment_line(self):
        extractor = RegexStringExtractor(language="typescript")
        source = 'let x = "real"; // "fake"'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "real"

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

    def test_ruby_partial_comment(self):
        extractor = RegexStringExtractor(language="ruby")
        source = "msg = 'real' # 'fake'"
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "real"

    def test_slash_comment_languages(self):
        """All C-family languages use // comments."""
        for lang in ["typescript", "javascript", "go", "rust", "java", "scala", "csharp"]:
            extractor = RegexStringExtractor(language=lang)
            source = '// "commented"'
            result = extractor.extract_from_source(source)
            assert len(result) == 0, f"{lang} should strip // comments"
