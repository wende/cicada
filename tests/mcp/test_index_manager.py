"""
Tests for IndexManager keyword availability detection.

Ensures that IndexManager correctly detects both documentation keywords
and string keywords for enabling keyword search functionality.
"""

import pytest

from cicada.mcp.handlers.index_manager import IndexManager


class TestIndexManagerKeywordDetection:
    """Test IndexManager's keyword availability detection."""

    def test_no_keywords_at_all(self):
        """Index with no keywords should return False."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "functions": [
                        {"name": "func1", "line": 1},
                    ]
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        assert manager._check_keywords_available() is False

    def test_has_doc_keywords_only(self):
        """Index with only documentation keywords should return True."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "keywords": {"user": 0.9, "account": 0.8},
                    "functions": [
                        {"name": "func1", "line": 1},
                    ],
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        assert manager._check_keywords_available() is True

    def test_has_string_keywords_only(self):
        """Index with only string keywords should return True."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "string_keywords": {"database": 0.9, "query": 0.8},
                    "functions": [
                        {"name": "func1", "line": 1},
                    ],
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        # This should now return True after the fix
        assert manager._check_keywords_available() is True

    def test_has_both_keyword_types(self):
        """Index with both keyword types should return True."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "keywords": {"user": 0.9, "account": 0.8},
                    "string_keywords": {"database": 0.9, "query": 0.8},
                    "functions": [
                        {"name": "func1", "line": 1},
                    ],
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        assert manager._check_keywords_available() is True

    def test_function_level_doc_keywords(self):
        """Function-level documentation keywords should be detected."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "functions": [
                        {
                            "name": "func1",
                            "line": 1,
                            "keywords": {"process": 0.9, "data": 0.8},
                        },
                    ]
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        assert manager._check_keywords_available() is True

    def test_function_level_string_keywords(self):
        """Function-level string keywords should be detected."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "functions": [
                        {
                            "name": "func1",
                            "line": 1,
                            "string_keywords": {"SELECT": 0.9, "FROM": 0.8},
                        },
                    ]
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        # This should now return True after the fix
        assert manager._check_keywords_available() is True

    def test_mixed_module_and_function_keywords(self):
        """Mix of module and function-level keywords should be detected."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "Module1": {
                    "string_keywords": {"config": 0.9},
                    "functions": [
                        {"name": "func1", "line": 1},
                    ],
                },
                "Module2": {
                    "functions": [
                        {
                            "name": "func2",
                            "line": 10,
                            "keywords": {"validate": 0.8},
                        },
                    ]
                },
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        assert manager._check_keywords_available() is True

    def test_empty_keyword_dicts(self):
        """Empty keyword dictionaries should return False."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "keywords": {},
                    "string_keywords": {},
                    "functions": [
                        {
                            "name": "func1",
                            "line": 1,
                            "keywords": {},
                            "string_keywords": {},
                        },
                    ],
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        assert manager._check_keywords_available() is False
