"""
Comprehensive tests for cicada/parser.py
"""

from cicada.parser import ElixirParser


class TestElixirParserErrorHandling:
    """Tests for error handling in ElixirParser"""

    def test_parse_file_with_parse_error(self, tmp_path, capsys):
        """Test parsing file with syntax errors"""
        parser = ElixirParser()

        # Create file with invalid Elixir syntax
        bad_file = tmp_path / "bad.ex"
        bad_file.write_text("defmodule Broken do\n  def incomplete(")

        result = parser.parse_file(str(bad_file))

        # Should return None for parse errors
        assert result is None

        # Should print error message
        captured = capsys.readouterr()
        assert "Parse error" in captured.out

    def test_parse_file_with_exception(self, tmp_path, capsys):
        """Test parsing file that raises exception"""
        parser = ElixirParser()

        # Try to parse a non-existent file (will raise exception)
        result = parser.parse_file("/nonexistent/file.ex")

        # Should return None
        assert result is None

        # Should print error with traceback
        captured = capsys.readouterr()
        assert "Error parsing" in captured.out


class TestElixirParserMainBlock:
    """Tests for the main block CLI functionality"""

    def test_main_block_with_valid_file(self, tmp_path, monkeypatch, capsys):
        """Test running parser as main with valid file"""
        # Create a valid Elixir file
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
end
"""
        )

        # Mock sys.argv
        import runpy
        import sys

        monkeypatch.setattr(sys, "argv", ["parser.py", str(test_file)])

        # Clear module from cache to avoid import order warning
        if "cicada.parser" in sys.modules:
            del sys.modules["cicada.parser"]

        # Execute the main block by running the module
        try:
            runpy.run_module("cicada.parser", run_name="__main__")
        except SystemExit:
            pass  # main() may call sys.exit()

        captured = capsys.readouterr()
        # Should output JSON with TestModule
        assert "TestModule" in captured.out

    def test_main_block_no_arguments(self, monkeypatch, capsys):
        """Test running parser as main without arguments"""
        import runpy
        import sys

        monkeypatch.setattr(sys, "argv", ["parser.py"])

        # Clear module from cache to avoid import order warning
        if "cicada.parser" in sys.modules:
            del sys.modules["cicada.parser"]

        # Execute the main block
        try:
            runpy.run_module("cicada.parser", run_name="__main__")
        except SystemExit:
            pass

        captured = capsys.readouterr()
        # Should print usage message
        assert "Usage" in captured.out

    def test_main_block_with_invalid_file(self, monkeypatch, capsys):
        """Test running parser as main with file that fails to parse"""
        import runpy
        import sys

        monkeypatch.setattr(sys, "argv", ["parser.py", "/nonexistent/file.ex"])

        # Clear module from cache to avoid import order warning
        if "cicada.parser" in sys.modules:
            del sys.modules["cicada.parser"]

        # Execute the main block
        try:
            runpy.run_module("cicada.parser", run_name="__main__")
        except SystemExit:
            pass

        captured = capsys.readouterr()
        # Should print failure message
        assert "Failed to parse" in captured.out or "Error parsing" in captured.out
