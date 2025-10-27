#!/usr/bin/env python
"""
Test installation method detection logic.
"""

# No unused imports
from unittest.mock import patch


def test_uvx_detection():
    """Test that uvx temporary paths are detected correctly."""
    from cicada.install import detect_installation_method

    # Mock sys.argv[0] to simulate uvx path
    uvx_paths = [
        "/Users/user/.cache/uv/builds/cicada-setup",
        "/tmp/uvx-cicada/bin/cicada-setup",
        "/var/folders/xyz/tmpdir123/cicada-setup",
    ]

    for uvx_path in uvx_paths:
        with patch("sys.argv", [uvx_path]):
            command, args, cwd, description = detect_installation_method()

            # Should use Python fallback for uvx
            assert (
                command != "cicada-server"
            ), f"uvx path {uvx_path} incorrectly detected as permanent install"
            assert (
                args is not None and len(args) > 0
            ), "Should have args for Python mode"
            assert "mcp_server.py" in str(args[0]), "Should point to mcp_server.py"
            assert (
                "uvx" in description.lower()
            ), f"Description should mention uvx: {description}"

    print("✅ All uvx detection tests passed")


def test_uv_tool_install_detection():
    """Test that uv tool install paths are detected correctly."""
    from cicada.install import detect_installation_method

    # Mock sys.argv[0] to simulate uv tool install path
    uv_paths = [
        "/Users/user/.local/share/uv/tools/cicada/bin/cicada-setup",
        "/home/user/.local/bin/cicada-setup",
    ]

    for uv_path in uv_paths:
        with patch("sys.argv", [uv_path]):
            command, args, cwd, description = detect_installation_method()

            # Should use cicada-server for permanent installs
            assert (
                command == "cicada-server"
            ), f"uv tool install path {uv_path} not detected correctly"
            assert args == [], "Should have no args for cicada-server"
            assert cwd is None, "Should have no cwd for cicada-server"

    print("✅ All uv tool install detection tests passed")


def test_direct_python_detection():
    """Test that direct Python paths are detected correctly."""
    from cicada.install import detect_installation_method

    # Mock sys.argv[0] to simulate running from source
    python_paths = [
        "/Users/user/projects/cicada/cicada/install.py",
        "/home/developer/cicada/bin/cicada-setup",
    ]

    for python_path in python_paths:
        with patch("sys.argv", [python_path]):
            with patch("shutil.which", return_value=None):  # cicada-server not in PATH
                command, args, cwd, description = detect_installation_method()

                # Should use Python fallback
                assert (
                    command != "cicada-server"
                ), f"Direct Python path {python_path} incorrectly detected"
                assert (
                    args is not None and len(args) > 0
                ), "Should have args for Python mode"
                assert "mcp_server.py" in str(args[0]), "Should point to mcp_server.py"

    print("✅ All direct Python detection tests passed")


if __name__ == "__main__":
    test_uvx_detection()
    test_uv_tool_install_detection()
    test_direct_python_detection()

    print("\n🎉 All installation detection tests passed!")
