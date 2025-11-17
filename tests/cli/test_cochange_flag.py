"""Tests for --extract-cochange CLI flag."""

import pytest
from cicada.commands import get_argument_parser


class TestCoChangeCLIFlag:
    """Test suite for --extract-cochange CLI flag."""

    def test_argparse_accepts_extract_cochange_flag(self):
        """Test that argument parser accepts --extract-cochange flag."""
        from cicada.commands import get_argument_parser

        # Arrange
        parser = get_argument_parser()

        # Act
        args = parser.parse_args(["index", "--extract-cochange"])

        # Assert
        assert hasattr(args, "extract_cochange")
        assert args.extract_cochange is True

    def test_argparse_extract_cochange_defaults_to_false(self):
        """Test that extract_cochange defaults to False."""
        from cicada.commands import get_argument_parser

        # Arrange
        parser = get_argument_parser()

        # Act
        args = parser.parse_args(["index"])

        # Assert
        assert hasattr(args, "extract_cochange")
        assert args.extract_cochange is False
