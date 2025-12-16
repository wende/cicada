
import argparse
from unittest.mock import patch, MagicMock
import pytest
from cicada.commands import handle_install

@pytest.fixture
def mock_setup():
    with patch("cicada.setup.setup") as mock:
        yield mock

@pytest.fixture
def mock_detect_language():
    with patch("cicada.commands._validate_project_language") as mock:
        yield mock

@pytest.fixture
def mock_tier_flags():
    with patch("cicada.commands.validate_tier_flags") as mock:
        yield mock

@pytest.fixture
def mock_index_exists():
    with patch("cicada.utils.get_config_path") as mock_config, \
         patch("cicada.utils.get_index_path") as mock_index:
        mock_config.return_value.exists.return_value = False
        mock_index.return_value.exists.return_value = False
        yield

def test_install_yes_flag(mock_setup, mock_detect_language, mock_tier_flags, mock_index_exists):
    args = MagicMock()
    args.repo = "."
    args.yes = True
    args.claude = True # Editor required for --yes
    args.cursor = False
    args.vs = False
    args.gemini = False
    args.codex = False
    args.index_prs = False
    args.no_index_prs = False
    args.skip_optional = False
    args.default = False
    args.command = "install"
    
    # Mock get_extraction_expansion_methods to return None (default)
    with patch("cicada.commands.get_extraction_expansion_methods", return_value=(None, None)):
        handle_install(args)
    
    # Verify setup called with defaults
    mock_setup.assert_called_once()
    pos_args, kw_args = mock_setup.call_args
    assert pos_args[0] == "claude"
    assert kw_args["extraction_method"] is None # Default handled by setup
    assert kw_args["index_prs"] is True # --yes enables PR indexing
    assert kw_args["add_to_claude_md"] is True # --yes enables Claude docs

def test_install_index_prs_flag(mock_setup, mock_detect_language, mock_tier_flags, mock_index_exists):
    args = MagicMock()
    args.repo = "."
    args.yes = True
    args.claude = True
    args.cursor = False
    args.vs = False
    args.gemini = False
    args.codex = False
    args.index_prs = True
    args.no_index_prs = False
    args.skip_optional = False
    args.default = False
    args.command = "install"

    with patch("cicada.commands.get_extraction_expansion_methods", return_value=(None, None)):
        handle_install(args)
    
    call_args = mock_setup.call_args[1]
    assert call_args["index_prs"] is True

def test_install_skip_optional_flag(mock_setup, mock_detect_language, mock_tier_flags, mock_index_exists):
    args = MagicMock()
    args.repo = "."
    args.yes = True
    args.claude = True
    args.cursor = False
    args.vs = False
    args.gemini = False
    args.codex = False
    args.index_prs = False
    args.no_index_prs = False
    args.skip_optional = True
    args.default = False
    args.command = "install"

    with patch("cicada.commands.get_extraction_expansion_methods", return_value=(None, None)):
        handle_install(args)
    
    call_args = mock_setup.call_args[1]
    assert call_args["index_prs"] is False
    assert call_args["add_to_claude_md"] is False

