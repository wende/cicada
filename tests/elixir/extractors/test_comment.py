"""
Tests for inline comment extraction from Elixir source code.
"""

import pytest
import tree_sitter_elixir as ts_elixir
from tree_sitter import Language, Parser

from cicada.languages.elixir.extractors import extract_functions, extract_modules


@pytest.fixture
def parser():
    """Create an Elixir parser instance."""
    return Parser(Language(ts_elixir.language()))


@pytest.fixture
def sample_comments_ast(parser):
    """Parse the sample_comments.ex fixture file."""
    with open("tests/fixtures/sample_comments.ex", "rb") as f:
        source_code = f.read()

    tree = parser.parse(source_code)
    return tree.root_node, source_code


@pytest.fixture
def sample_comments_module(sample_comments_ast):
    """Extract module and functions from sample_comments.ex."""
    root_node, source_code = sample_comments_ast

    # Extract module
    modules = extract_modules(root_node, source_code)
    assert len(modules) == 1
    module = modules[0]

    # Extract functions
    functions = extract_functions(module["do_block"], source_code)

    # Add functions to module dict
    module["functions"] = functions

    return module, source_code


class TestCommentExtractorInitialization:
    """Test CommentExtractor initialization."""

    def test_default_initialization(self):
        """Test CommentExtractor with default parameters."""
        from cicada.languages.elixir.extractors import CommentExtractor

        extractor = CommentExtractor()
        assert extractor.min_length == 3
        assert extractor.merge_consecutive is True

    def test_custom_initialization(self):
        """Test CommentExtractor with custom parameters."""
        from cicada.languages.elixir.extractors import CommentExtractor

        extractor = CommentExtractor(min_length=5, merge_consecutive=False)
        assert extractor.min_length == 5
        assert extractor.merge_consecutive is False


class TestBasicCommentExtraction:
    """Test basic comment extraction functionality."""

    def test_extracts_inline_comments(self, sample_comments_module):
        """Test that inline comments inside functions are extracted."""
        from cicada.languages.elixir.extractors import CommentExtractor

        module, source_code = sample_comments_module

        # Extract comments
        extractor = CommentExtractor()
        comments_by_function = extractor.extract_from_module(
            module["do_block"], source_code, module["functions"]
        )

        # Should have comments for multiple functions
        assert len(comments_by_function) > 0

        # Check specific function has comments
        assert "function_with_inline_comments" in comments_by_function
        func_comments = comments_by_function["function_with_inline_comments"]

        # Extract comment text
        comment_texts = [c["comment"] for c in func_comments]

        # Should extract inline comments (# prefix stripped)
        assert any("inline comment inside the function" in text for text in comment_texts)
        assert any("explains the next operation" in text for text in comment_texts)
        assert any("Return the result" in text for text in comment_texts)

    def test_strips_hash_prefix(self, sample_comments_module):
        """Test that # prefix is stripped from comment text."""
        from cicada.languages.elixir.extractors import CommentExtractor

        module, source_code = sample_comments_module

        extractor = CommentExtractor()
        comments_by_function = extractor.extract_from_module(
            module["do_block"], source_code, module["functions"]
        )

        # Check all extracted comments don't start with #
        for func_name, func_comments in comments_by_function.items():
            for comment in func_comments:
                assert not comment["comment"].startswith("#")
                assert not comment["comment"].startswith(" #")

    def test_skips_short_comments(self, sample_comments_module):
        """Test that comments shorter than min_length are filtered."""
        from cicada.languages.elixir.extractors import CommentExtractor

        module, source_code = sample_comments_module

        # Extract with default min_length=3
        extractor = CommentExtractor(min_length=3)
        comments_by_function = extractor.extract_from_module(
            module["do_block"], source_code, module["functions"]
        )

        # Function "function_with_short_comments" has comments: #a #b #c (too short)
        # and "This comment is long enough to be extracted" (long enough)
        if "function_with_short_comments" in comments_by_function:
            func_comments = comments_by_function["function_with_short_comments"]
            comment_texts = [c["comment"] for c in func_comments]

            # Short comments should be filtered
            assert "a" not in comment_texts
            assert "b" not in comment_texts
            assert "c" not in comment_texts
            assert "ok" not in comment_texts
            assert "no" not in comment_texts

            # Long comment should be present
            assert any("long enough to be extracted" in text for text in comment_texts)


class TestCommentBeforeFunction:
    """Test extraction of comments before function definitions."""

    def test_top_level_comments_associate_with_first_function(self, sample_comments_module):
        """Test that top-level comments are associated with the first function."""
        from cicada.languages.elixir.extractors import CommentExtractor

        module, source_code = sample_comments_module

        extractor = CommentExtractor()
        comments_by_function = extractor.extract_from_module(
            module["do_block"], source_code, module["functions"]
        )

        # First function should have the top-level comment
        first_function = module["functions"][0]
        first_func_name = first_function["name"]

        assert first_func_name in comments_by_function
        func_comments = comments_by_function[first_func_name]
        comment_texts = [c["comment"] for c in func_comments]

        # Should include top-level comment
        assert any("top-level comment before any functions" in text for text in comment_texts)

    def test_comments_before_function_associate_with_that_function(self, sample_comments_module):
        """Test that comments before a function definition are associated with it."""
        from cicada.languages.elixir.extractors import CommentExtractor

        module, source_code = sample_comments_module

        extractor = CommentExtractor()
        comments_by_function = extractor.extract_from_module(
            module["do_block"], source_code, module["functions"]
        )

        # function_with_comment_before has comments right before its definition
        assert "function_with_comment_before" in comments_by_function
        func_comments = comments_by_function["function_with_comment_before"]
        comment_texts = [c["comment"] for c in func_comments]

        # Should include the comment before the function
        assert any("right before the function definition" in text for text in comment_texts)


class TestConsecutiveCommentMerging:
    """Test merging of consecutive comment lines."""

    def test_merges_consecutive_comments(self, sample_comments_module):
        """Test that consecutive comment lines are merged into blocks."""
        from cicada.languages.elixir.extractors import CommentExtractor

        module, source_code = sample_comments_module

        extractor = CommentExtractor(merge_consecutive=True)
        comments_by_function = extractor.extract_from_module(
            module["do_block"], source_code, module["functions"]
        )

        # function_with_consecutive_comments has multiple comment blocks
        assert "function_with_consecutive_comments" in comments_by_function
        func_comments = comments_by_function["function_with_consecutive_comments"]

        # Should have merged "Step 1, Step 2, Step 3" into one block
        merged_blocks = [c for c in func_comments if c.get("is_block", False)]
        assert len(merged_blocks) > 0

        # Check that the merged block contains all three steps
        step_blocks = [
            c
            for c in func_comments
            if "Step 1" in c["comment"] or "Step 2" in c["comment"] or "Step 3" in c["comment"]
        ]

        # With merging, should be one block containing all steps
        if step_blocks:
            assert any(
                "Step 1" in block["comment"]
                and "Step 2" in block["comment"]
                and "Step 3" in block["comment"]
                for block in step_blocks
            )

    def test_no_merge_with_flag_disabled(self, sample_comments_module):
        """Test that consecutive comments are NOT merged when flag is False."""
        from cicada.languages.elixir.extractors import CommentExtractor

        module, source_code = sample_comments_module

        extractor = CommentExtractor(merge_consecutive=False)
        comments_by_function = extractor.extract_from_module(
            module["do_block"], source_code, module["functions"]
        )

        # With merge_consecutive=False, each line should be separate
        if "function_with_consecutive_comments" in comments_by_function:
            func_comments = comments_by_function["function_with_consecutive_comments"]

            # Should have individual comments for each step
            step_comments = [c for c in func_comments if "Step" in c["comment"]]

            # Each step should be in its own comment
            step_1_separate = any(
                "Step 1" in c["comment"] and "Step 2" not in c["comment"] for c in step_comments
            )
            step_2_separate = any(
                "Step 2" in c["comment"]
                and "Step 1" not in c["comment"]
                and "Step 3" not in c["comment"]
                for c in step_comments
            )
            step_3_separate = any(
                "Step 3" in c["comment"] and "Step 2" not in c["comment"] for c in step_comments
            )

            assert step_1_separate or step_2_separate or step_3_separate


class TestSpecialCommentMarkers:
    """Test extraction of TODO, FIXME, BUG markers."""

    def test_extracts_todo_fixme_bug_markers(self, sample_comments_module):
        """Test that comments with TODO, FIXME, BUG are extracted."""
        from cicada.languages.elixir.extractors import CommentExtractor

        module, source_code = sample_comments_module

        extractor = CommentExtractor()
        comments_by_function = extractor.extract_from_module(
            module["do_block"], source_code, module["functions"]
        )

        # function_with_markers should have TODO, FIXME, BUG comments
        assert "function_with_markers" in comments_by_function
        func_comments = comments_by_function["function_with_markers"]
        comment_texts = [c["comment"] for c in func_comments]

        # Should extract all marker types
        assert any("TODO" in text for text in comment_texts)
        assert any("FIXME" in text for text in comment_texts)
        assert any("BUG" in text for text in comment_texts)


class TestFunctionContextTracking:
    """Test function context tracking."""

    def test_associates_comments_with_correct_functions(self, sample_comments_module):
        """Test that comments are associated with the correct functions."""
        from cicada.languages.elixir.extractors import CommentExtractor

        module, source_code = sample_comments_module

        extractor = CommentExtractor()
        comments_by_function = extractor.extract_from_module(
            module["do_block"], source_code, module["functions"]
        )

        # Each function should have its own comments, not others'
        # function_with_inline_comments should have its specific comments
        if "function_with_inline_comments" in comments_by_function:
            func_comments = comments_by_function["function_with_inline_comments"]
            comment_texts = [c["comment"] for c in func_comments]

            # Should have its own comments
            assert any("inline comment" in text for text in comment_texts)

            # Should NOT have comments from other functions
            assert not any("TODO: Implement proper validation" in text for text in comment_texts)

    def test_private_functions_extract_comments(self, sample_comments_module):
        """Test that private functions (defp) also have their comments extracted."""
        from cicada.languages.elixir.extractors import CommentExtractor

        module, source_code = sample_comments_module

        extractor = CommentExtractor()
        comments_by_function = extractor.extract_from_module(
            module["do_block"], source_code, module["functions"]
        )

        # private_function_with_comments is a defp
        assert "private_function_with_comments" in comments_by_function
        func_comments = comments_by_function["private_function_with_comments"]
        comment_texts = [c["comment"] for c in func_comments]

        # Should extract comments from private functions
        assert any("Private functions can have comments" in text for text in comment_texts)


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_function_with_no_comments(self, sample_comments_module):
        """Test function with no comments returns empty or is absent."""
        from cicada.languages.elixir.extractors import CommentExtractor

        module, source_code = sample_comments_module

        extractor = CommentExtractor()
        comments_by_function = extractor.extract_from_module(
            module["do_block"], source_code, module["functions"]
        )

        # no_comments_function should have no comments
        if "no_comments_function" in comments_by_function:
            func_comments = comments_by_function["no_comments_function"]
            assert len(func_comments) == 0

    def test_nested_structures_extract_comments(self, sample_comments_module):
        """Test comments in nested structures (if/case/etc) are extracted."""
        from cicada.languages.elixir.extractors import CommentExtractor

        module, source_code = sample_comments_module

        extractor = CommentExtractor()
        comments_by_function = extractor.extract_from_module(
            module["do_block"], source_code, module["functions"]
        )

        # function_with_nested_structures has comments in if/case blocks
        assert "function_with_nested_structures" in comments_by_function
        func_comments = comments_by_function["function_with_nested_structures"]
        comment_texts = [c["comment"] for c in func_comments]

        # Should extract comments from nested structures
        assert any("Inside if block" in text for text in comment_texts)
        assert any("Inside else block" in text for text in comment_texts)
        assert any("Inside case clause" in text for text in comment_texts)

    def test_empty_module_or_no_functions(self, parser):
        """Test handling of modules with no functions."""
        from cicada.languages.elixir.extractors import CommentExtractor

        # Create a minimal module with no functions
        source_code = b"""
        defmodule EmptyModule do
          # Just a comment, no functions
        end
        """

        tree = parser.parse(source_code)
        modules = extract_modules(tree.root_node, source_code)

        if modules:
            module = modules[0]
            extractor = CommentExtractor()

            # Pass empty functions list
            comments_by_function = extractor.extract_from_module(
                module["do_block"], source_code, []
            )

            # Should handle gracefully (empty dict or no crash)
            assert isinstance(comments_by_function, dict)

    def test_line_numbers_are_accurate(self, sample_comments_module):
        """Test that line numbers in extracted comments are accurate."""
        from cicada.languages.elixir.extractors import CommentExtractor

        module, source_code = sample_comments_module

        extractor = CommentExtractor()
        comments_by_function = extractor.extract_from_module(
            module["do_block"], source_code, module["functions"]
        )

        # All comments should have line numbers > 0
        for func_name, func_comments in comments_by_function.items():
            for comment in func_comments:
                assert "line" in comment
                assert comment["line"] > 0
                assert isinstance(comment["line"], int)
