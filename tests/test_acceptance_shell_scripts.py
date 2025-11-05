"""
Test that acceptance shell scripts are executable and work correctly.

These tests verify that the shell scripts in tests/acceptance/ can actually run,
ensuring they don't break when dependencies or paths change.
"""

import subprocess
from pathlib import Path

import pytest


class TestAcceptanceShellScripts:
    """Tests to verify acceptance shell scripts work"""

    @pytest.fixture
    def scripts_dir(self):
        """Get the acceptance scripts directory"""
        return Path(__file__).parent / "acceptance"

    def test_check_moduledoc_script_runs(self, scripts_dir):
        """Test that check_moduledoc.sh can execute without errors"""
        script = scripts_dir / "check_moduledoc.sh"
        assert script.exists(), f"Script not found: {script}"

        result = subprocess.run(
            [str(script), "TestApp"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Script should complete successfully
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        # Should output something
        assert len(result.stdout) > 0, "Script produced no output"
        # Should contain the module name
        assert "TestApp" in result.stdout

    def test_check_functiondoc_script_runs(self, scripts_dir):
        """Test that check_functiondoc.sh can execute without errors"""
        script = scripts_dir / "check_functiondoc.sh"
        assert script.exists(), f"Script not found: {script}"

        result = subprocess.run(
            [str(script), "add_numbers"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Script should complete successfully
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        # Should output something
        assert len(result.stdout) > 0, "Script produced no output"
        # Should contain function info
        assert "add_numbers" in result.stdout

    def test_search_module_script_runs(self, scripts_dir):
        """Test that search_module.sh can execute without errors"""
        script = scripts_dir / "search_module.sh"
        assert script.exists(), f"Script not found: {script}"

        result = subprocess.run(
            [str(script), "TestApp"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Script should complete successfully
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert len(result.stdout) > 0
        assert "TestApp" in result.stdout

    def test_search_function_script_runs(self, scripts_dir):
        """Test that search_function.sh can execute without errors"""
        script = scripts_dir / "search_function.sh"
        assert script.exists(), f"Script not found: {script}"

        result = subprocess.run(
            [str(script), "add_numbers"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Script should complete successfully
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert len(result.stdout) > 0
        assert "add_numbers" in result.stdout

    def test_search_by_features_script_runs(self, scripts_dir):
        """Test that search_by_features.sh can execute without errors"""
        script = scripts_dir / "search_by_features.sh"
        assert script.exists(), f"Script not found: {script}"

        result = subprocess.run(
            [str(script), "test"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Script should complete successfully
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert len(result.stdout) > 0
        # Should either find results or say no results
        assert "test" in result.stdout.lower() or "no results" in result.stdout.lower()

    def test_all_shell_scripts_are_executable(self, scripts_dir):
        """Verify all .sh files have executable permissions"""
        scripts = list(scripts_dir.glob("*.sh"))
        assert len(scripts) > 0, "No shell scripts found"

        non_executable = []
        for script in scripts:
            if not script.stat().st_mode & 0o111:  # Check if any execute bit is set
                non_executable.append(script.name)

        assert len(non_executable) == 0, f"Non-executable scripts found: {non_executable}"

    def test_all_shell_scripts_use_uv_run(self, scripts_dir):
        """Verify all .sh scripts that invoke python use 'uv run python'"""
        scripts = list(scripts_dir.glob("*.sh"))

        for script in scripts:
            content = script.read_text()

            # Skip if script doesn't invoke python
            if "python" not in content:
                continue

            # Check that it uses 'uv run python' not just 'python'
            if "python -c" in content or "python3 -c" in content:
                assert (
                    "uv run python" in content
                ), f"{script.name} uses 'python' instead of 'uv run python'"
