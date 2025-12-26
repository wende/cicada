"""Tests for the embeddings text_builder module."""

import pytest

from cicada.embeddings.text_builder import (
    build_document_id,
    build_function_text,
    build_metadata,
    build_module_text,
)


class TestBuildModuleText:
    """Tests for build_module_text function."""

    def test_basic_module_text(self):
        """Test building text for a simple module."""
        module_name = "MyApp.User"
        module_data = {
            "moduledoc": "User management module.",
            "file": "lib/my_app/user.ex",
            "line": 1,
        }

        result = build_module_text(module_name, module_data)

        assert "MyApp User module" in result
        assert "User management module." in result

    def test_module_text_without_doc(self):
        """Test building text for a module without documentation."""
        module_name = "MyApp.Repo"
        module_data = {
            "file": "lib/my_app/repo.ex",
            "line": 1,
        }

        result = build_module_text(module_name, module_data)

        assert "MyApp Repo module" in result

    def test_module_text_with_string_keywords(self):
        """Test building text with string keywords."""
        module_name = "MyApp.Query"
        module_data = {
            "moduledoc": "Query builder.",
            "string_keywords": {"SELECT": 0.9, "INSERT": 0.8, "UPDATE": 0.7},
        }

        result = build_module_text(module_name, module_data)

        assert "Contains:" in result


class TestBuildFunctionText:
    """Tests for build_function_text function."""

    def test_basic_function_text(self):
        """Test building text for a simple function."""
        module_name = "MyApp.User"
        func_data = {
            "name": "create",
            "arity": 1,
            "args": ["attrs"],
            "signature": "def create(attrs) do",
            "doc": "Creates a new user.",
            "type": "def",
        }

        result = build_function_text(module_name, func_data)

        assert "MyApp.User" in result
        assert "create" in result
        assert "Creates a new user." in result
        assert "attrs" in result

    def test_function_text_without_doc(self):
        """Test building text for a function without documentation."""
        module_name = "MyApp.User"
        func_data = {
            "name": "get",
            "arity": 1,
            "type": "def",
        }

        result = build_function_text(module_name, func_data)

        assert "MyApp.User" in result
        assert "get/1" in result

    def test_private_function_text(self):
        """Test building text for a private function."""
        module_name = "MyApp.User"
        func_data = {
            "name": "validate",
            "arity": 1,
            "type": "defp",
        }

        result = build_function_text(module_name, func_data)

        assert "(private function)" in result


class TestBuildDocumentId:
    """Tests for build_document_id function."""

    def test_module_document_id(self):
        """Test building document ID for a module."""
        result = build_document_id("module", "MyApp.User")

        assert result == "module:MyApp.User"

    def test_function_document_id(self):
        """Test building document ID for a function."""
        func_data = {"name": "create", "arity": 2}

        result = build_document_id("function", "MyApp.User", func_data)

        assert result == "function:MyApp.User.create/2"

    def test_invalid_doc_type(self):
        """Test that invalid doc_type raises ValueError."""
        with pytest.raises(ValueError):
            build_document_id("invalid", "MyApp.User")


class TestBuildMetadata:
    """Tests for build_metadata function."""

    def test_module_metadata(self):
        """Test building metadata for a module."""
        result = build_metadata(
            doc_type="module",
            module_name="MyApp.User",
            file_path="lib/my_app/user.ex",
            line=10,
        )

        assert result["type"] == "module"
        assert result["module"] == "MyApp.User"
        assert result["file"] == "lib/my_app/user.ex"
        assert result["line"] == 10
        assert result["name"] == "MyApp.User"

    def test_function_metadata(self):
        """Test building metadata for a function."""
        func_data = {
            "name": "create",
            "arity": 1,
            "type": "def",
        }

        result = build_metadata(
            doc_type="function",
            module_name="MyApp.User",
            file_path="lib/my_app/user.ex",
            line=25,
            func_data=func_data,
        )

        assert result["type"] == "function"
        assert result["module"] == "MyApp.User"
        assert result["function"] == "create"
        assert result["arity"] == 1
        assert result["visibility"] == "def"
        assert result["name"] == "MyApp.User.create/1"
