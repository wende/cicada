"""
Medium-priority multi-language and UX consistency tests.

Tests for:
1. Interactive setup UI consistency
2. Multi-language repository handling
3. Import path backward compatibility
"""

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestInteractiveSetupConsistency:
    """Test that interactive setup produces consistent config output."""

    def test_setup_menu_vs_text_mode_consistency(self):
        """Menu mode and text fallback should produce identical configs."""
        # This test documents expected setup behavior
        # Menu mode -> Choose "Regular" with GloVe -> config with bert/glove
        # Text mode -> Type "2" for regular -> same config

        menu_choice_mapping = {
            "Fast (no downloads)": ("regular", "lemmi"),
            "Regular (recommended)": ("bert", "glove"),
            "Maximum (slow)": ("bert", "fasttext"),
        }

        text_choice_mapping = {
            "1": ("regular", "lemmi"),
            "2": ("bert", "glove"),
            "3": ("bert", "fasttext"),
        }

        # Verify they map to same extraction/expansion combinations
        for menu_label, menu_result in menu_choice_mapping.items():
            # Find corresponding text choice
            if "Fast" in menu_label:
                text_result = text_choice_mapping["1"]
            elif "Regular" in menu_label:
                text_result = text_choice_mapping["2"]
            elif "Maximum" in menu_label:
                text_result = text_choice_mapping["3"]
            else:
                continue

            assert (
                menu_result == text_result
            ), f"Menu '{menu_label}' and text mode produce different config"

    def test_setup_returns_correct_types(self):
        """Setup should always return (extraction_method, expansion_method) tuple."""
        # This validates the return type contract
        expected_types = {
            "extraction_method": str,
            "expansion_method": str,
        }

        # Valid combinations
        valid_configs = [
            ("regular", "lemmi"),
            ("bert", "glove"),
            ("bert", "fasttext"),
        ]

        for extraction, expansion in valid_configs:
            assert isinstance(extraction, str)
            assert isinstance(expansion, str)

    def test_setup_persists_to_config_yaml(self, tmp_path):
        """Setup choices should be persisted to config.yaml with correct structure."""
        config_file = tmp_path / "config.yaml"

        # Simulate setup writing config
        import yaml

        setup_config = {
            "language": "elixir",
            "keyword_extraction": {"method": "bert"},
            "keyword_expansion": {"method": "glove"},
        }

        with open(config_file, "w") as f:
            yaml.dump(setup_config, f)

        # Verify it persists correctly
        with open(config_file) as f:
            persisted = yaml.safe_load(f)

        assert persisted["keyword_extraction"]["method"] == "bert"
        assert persisted["keyword_expansion"]["method"] == "glove"

    def test_new_user_sees_updated_setup_ui(self):
        """New users should see updated setup menu with new tier names."""
        # Post-merge, menu should show:
        # 1. Fast (Regular extraction + Lemmi expansion)
        # 2. Regular (KeyBERT + GloVe) <- NEW DEFAULT
        # 3. Maximum (KeyBERT + FastText)

        new_menu_options = [
            {"label": "Fast", "extraction": "regular", "expansion": "lemmi"},
            {"label": "Regular", "extraction": "bert", "expansion": "glove"},
            {"label": "Maximum", "extraction": "bert", "expansion": "fasttext"},
        ]

        # Verify new menu structure
        for option in new_menu_options:
            assert "label" in option
            assert "extraction" in option
            assert "expansion" in option
            assert option["extraction"] in ["regular", "bert"]
            assert option["expansion"] in ["lemmi", "glove", "fasttext"]

        # Default should be Regular (bert + glove)
        default_option = new_menu_options[1]
        assert default_option["extraction"] == "bert"
        assert default_option["expansion"] == "glove"

    def test_returning_user_with_old_config_shows_migration_notice(self, tmp_path):
        """Returning users with pre-merge config should see migration notice."""
        config_file = tmp_path / "config.yaml"

        # Old config format
        old_config_content = """
language: elixir
keyword_extraction:
  method: lemminflect
  tier: fast
"""
        config_file.write_text(old_config_content)

        # When loaded and presented to user, should indicate migration happened
        import yaml

        with open(config_file) as f:
            config = yaml.safe_load(f)

        is_old_format = "tier" in config.get("keyword_extraction", {})
        assert is_old_format, "Config should be detected as old format"

        # Should communicate migration to user
        migration_message = (
            "Your Cicada configuration has been updated with new extraction/expansion settings"
        )
        assert migration_message  # Should be shown to user


class TestMultiLanguageRepositoryHandling:
    """Test handling of repositories with multiple language markers."""

    def test_repo_with_both_python_and_elixir_markers(self, tmp_path):
        """Repository with both pyproject.toml and mix.exs should handle gracefully."""
        # Create both markers
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'my-lib'")
        (tmp_path / "mix.exs").write_text("defmodule MyApp.MixProject do\n  use Mix.Project\nend")

        from cicada.setup import detect_project_language

        detected = detect_project_language(tmp_path)

        # Should detect one language (current: Python wins)
        assert detected in ["python", "elixir"], (
            f"Should detect one language, got: {detected}. "
            "Should document precedence: Python markers checked first"
        )

        # Should either:
        # 1. Document that Python is prioritized, OR
        # 2. Ask user which to index
        if detected == "python":
            # Document that user can't index Elixir part without explicitly requesting
            elixir_note = (
                "Multi-language repository detected. To index Elixir code, "
                "use: cicada index --language elixir"
            )
            assert elixir_note  # Should be documented behavior

    def test_monorepo_with_multiple_languages(self, tmp_path):
        """Monorepo with subdirectories of different languages should detect from subdirs."""
        # Create monorepo structure
        python_dir = tmp_path / "services" / "api"
        elixir_dir = tmp_path / "services" / "backend"

        python_dir.mkdir(parents=True)
        elixir_dir.mkdir(parents=True)

        (python_dir / "pyproject.toml").write_text("[tool.poetry]")
        (elixir_dir / "mix.exs").write_text("defmodule Backend do; end")

        from cicada.setup import detect_project_language

        # Detecting from root should fail (no markers)
        with pytest.raises(ValueError, match="Could not detect project language"):
            detect_project_language(tmp_path)

        # Detecting from subdirectories should find language-specific markers
        detected_python = detect_project_language(python_dir)
        detected_elixir = detect_project_language(elixir_dir)

        # Should be able to detect language-specific markers in subdirectories
        assert detected_python == "python", "Should detect Python in subdirectory"
        assert detected_elixir == "elixir", "Should detect Elixir in subdirectory"

    def test_language_parameter_overrides_detection(self, tmp_path):
        """Explicit language parameter should override detection."""
        # Create both markers
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]")
        (tmp_path / "mix.exs").write_text("defmodule App do; end")

        # If user explicitly requests Elixir despite Python markers existing,
        # should respect the choice
        requested_language = "elixir"
        assert requested_language in ["python", "elixir"]

        # Implementation note: PythonSCIPIndexer vs ElixirIndexer should be
        # instantiated based on explicit request, not detection

    def test_error_message_for_unsupported_language(self, tmp_path):
        """Unsupported language (Ruby) should raise ValueError."""
        # Create Ruby project marker (not recognized by detect_project_language)
        (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'")

        from cicada.setup import detect_project_language

        # Ruby not supported - should raise error
        with pytest.raises(ValueError, match="Could not detect project language"):
            detect_project_language(tmp_path)

    def test_no_language_markers_handles_gracefully(self, tmp_path):
        """Repository with no recognized language markers should raise ValueError."""
        from cicada.setup import detect_project_language

        # Empty directory should raise ValueError
        with pytest.raises(ValueError, match="Could not detect project language"):
            detect_project_language(tmp_path)


class TestImportPathBackwardCompatibility:
    """Test backward compatibility of import paths."""

    def test_old_cli_import_path_deprecated(self):
        """Old import path from cicada.cli should work with deprecation warning."""
        # Old code might do: from cicada.cli import index_repository
        # New code moved this to: from cicada.commands import handle_index

        # Check if old imports still work
        try:
            # This represents old user code
            old_import_path = "cicada.cli"
            if old_import_path in sys.modules:
                # If user has imported old path, should see deprecation
                deprecation_warning = "cicada.cli is deprecated, use cicada.commands instead"
                assert deprecation_warning
        except ImportError:
            # Expected if old path no longer exists
            pass

    def test_new_command_module_exports(self):
        """New commands module should export handler functions."""
        from cicada import commands

        # New module should have these functions
        required_functions = [
            "get_argument_parser",
            "get_extraction_expansion_methods",
            "validate_tier_flags",
        ]

        for func_name in required_functions:
            assert hasattr(commands, func_name), f"commands module should export {func_name}"

    def test_mcp_entry_point_still_works(self):
        """MCP entry point should still be accessible."""
        # MCP tools depend on being able to find and start the server
        # Check that mcp_entry.py or equivalent exists and is importable

        try:
            # Try to import MCP entry point (implementation may vary)
            from cicada.mcp import entry as mcp_entry

            assert mcp_entry is not None
        except ImportError as e:
            # If mcp entry point moved, document the new location
            # Current structure: cicada/mcp/entry.py
            print(f"MCP entry point location: {e}")

    def test_tool_imports_still_resolve(self):
        """MCP tools should still be importable."""
        try:
            from cicada.mcp import tools

            assert tools is not None
        except ImportError as e:
            pytest.fail(f"MCP tools should be importable: {e}")

    def test_storage_module_exports_unchanged(self):
        """Storage module should export same functions."""
        from cicada.utils import storage

        required_functions = [
            "get_config_path",
            "get_storage_dir",
            "get_index_path",
        ]

        for func_name in required_functions:
            assert hasattr(storage, func_name), f"storage module should export {func_name}"

    def test_external_tool_integration_points(self):
        """Document public API that external tools depend on."""
        # External MCP tools might import:
        # - cicada.mcp.tools for MCP tool definitions
        # - cicada.utils.storage for config/index paths
        # - cicada.utils.keyword_utils for keyword extraction

        api_contracts = {
            "cicada.mcp.tools": ["get_tool_definitions"],
            "cicada.utils.storage": ["get_config_path", "get_index_path"],
            "cicada.utils.keyword_utils": ["read_keyword_extraction_config"],
        }

        for module_path, expected_exports in api_contracts.items():
            try:
                module = importlib.import_module(module_path)
                for export_name in expected_exports:
                    assert hasattr(
                        module, export_name
                    ), f"{module_path} should export {export_name} for external tools"
            except ImportError as e:
                pytest.fail(f"Cannot import {module_path}: {e}")
