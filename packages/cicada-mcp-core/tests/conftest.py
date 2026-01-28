# DUPLICATED FROM: tests/conftest.py
# Contains only fixtures needed for cicada-core tests.
"""
Pytest configuration and fixtures for cicada-core tests.
"""

import pytest


@pytest.fixture
def mock_home_dir(tmp_path, monkeypatch):
    """Mock the home directory for storage tests"""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path
