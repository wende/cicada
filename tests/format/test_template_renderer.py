"""Unit tests for the TemplateRenderer class."""

import pytest
from pathlib import Path

from cicada.format.template_renderer import TemplateRenderer


class TestTemplateRenderer:
    """Test suite for TemplateRenderer."""

    def test_init_with_valid_language(self):
        """Test initialization with a valid language."""
        renderer = TemplateRenderer("python")
        assert renderer.language == "python"
        assert renderer.template_dir.exists()

    def test_init_with_uppercase_language(self):
        """Test that language is normalized to lowercase."""
        renderer = TemplateRenderer("PYTHON")
        assert renderer.language == "python"

    def test_render_signature_elixir(self):
        """Test rendering Elixir function signature."""
        renderer = TemplateRenderer("elixir")
        result = renderer.render(
            "signature",
            func_name="create_user",
            args="attrs: map, opts: keyword",
            return_annotation=" :: {:ok, User.t()}",
        )
        assert result == "create_user(attrs: map, opts: keyword) :: {:ok, User.t()}"

    def test_render_signature_python(self):
        """Test rendering Python function signature."""
        renderer = TemplateRenderer("python")
        result = renderer.render(
            "signature",
            func_name="create_user",
            args="attrs: dict, opts: dict",
            return_annotation=" -> User:",
        )
        assert result == "def create_user(attrs: dict, opts: dict) -> User:"

    def test_render_signature_no_return_type(self):
        """Test rendering signature without return type."""
        renderer = TemplateRenderer("elixir")
        result = renderer.render("signature", func_name="helper", args="x, y", return_annotation="")
        assert result == "helper(x, y)"

    def test_render_module_header_elixir(self):
        """Test rendering module header for Elixir."""
        renderer = TemplateRenderer("elixir")
        result = renderer.render(
            "module_header",
            module_name="MyApp.User",
            file="lib/my_app/user.ex",
            line=1,
            public_count=5,
            private_count=3,
        )
        expected = "MyApp.User\n\nlib/my_app/user.ex:1 • 5 public • 3 private"
        assert result == expected

    def test_render_module_header_python(self):
        """Test rendering module header for Python."""
        renderer = TemplateRenderer("python")
        result = renderer.render(
            "module_header",
            module_name="my_app.user",
            file="my_app/user.py",
            line=1,
            public_count=5,
            private_count=2,
        )
        expected = "my_app.user\n\nmy_app/user.py:1 • 5 public • 2 private"
        assert result == expected

    def test_render_missing_variable_raises_error(self):
        """Test that missing required variables raise ValueError."""
        renderer = TemplateRenderer("elixir")
        with pytest.raises(ValueError, match="requires variable 'func_name'"):
            renderer.render("signature", args="x, y")

    def test_safe_render_with_missing_variable(self):
        """Test safe_render leaves placeholders for missing variables."""
        renderer = TemplateRenderer("elixir")
        result = renderer.safe_render("signature", func_name="test")
        assert "test" in result
        assert "$args" in result or "$return_annotation" in result

    def test_template_caching(self):
        """Test that templates are cached after first load."""
        renderer = TemplateRenderer("elixir")

        # First render loads the template
        result1 = renderer.render("signature", func_name="func1", args="", return_annotation="")

        # Check cache
        assert "elixir:signature" in renderer._template_cache

        # Second render uses cache
        result2 = renderer.render("signature", func_name="func2", args="", return_annotation="")

        assert "func1" in result1
        assert "func2" in result2

    def test_clear_cache(self):
        """Test clearing the template cache."""
        renderer = TemplateRenderer("elixir")

        # Load a template
        renderer.render("signature", func_name="test", args="", return_annotation="")
        assert len(renderer._template_cache) > 0

        # Clear cache
        renderer.clear_cache()
        assert len(renderer._template_cache) == 0

    def test_template_exists(self):
        """Test checking if a template exists."""
        renderer = TemplateRenderer("elixir")
        assert renderer.template_exists("signature")
        assert not renderer.template_exists("nonexistent_template")

    def test_get_available_templates(self):
        """Test listing available templates."""
        renderer = TemplateRenderer("elixir")
        templates = renderer.get_available_templates()

        assert isinstance(templates, list)
        assert "signature" in templates
        assert "module_header" in templates
        assert "function_entry" in templates

    def test_fallback_to_elixir_template(self):
        """Test that missing template falls back to Elixir template."""
        # Create renderer for unsupported language
        renderer = TemplateRenderer("typescript")

        # Should fallback to Elixir template and log warning
        result = renderer.render(
            "signature", func_name="testFunc", args="x: number", return_annotation=""
        )

        # Should use Elixir format (no 'def' prefix)
        assert result == "testFunc(x: number)"

    def test_template_not_found_raises_error(self):
        """Test that completely missing template raises FileNotFoundError."""
        renderer = TemplateRenderer("elixir")

        with pytest.raises(FileNotFoundError, match="Template 'nonexistent' not found"):
            renderer.render("nonexistent", some_var="value")

    def test_get_template_path(self):
        """Test getting the correct template path."""
        renderer = TemplateRenderer("python")
        path = renderer._get_template_path("signature")

        assert path.suffix == ".txt"
        assert path.stem == "signature"
        assert "python" in str(path)

    def test_render_function_entry_elixir(self):
        """Test rendering function entry for Elixir."""
        renderer = TemplateRenderer("elixir")
        result = renderer.render(
            "function_entry",
            file_path="lib/my_app/user.ex",
            line=42,
            module_name="MyApp.User",
            func_name="create",
            arity=2,
            signature="create(attrs: map, opts: keyword) :: {:ok, User.t()}",
        )
        expected = "lib/my_app/user.ex:42\nMyApp.User.create/2\nType: create(attrs: map, opts: keyword) :: {:ok, User.t()}"
        assert result == expected

    def test_render_function_entry_python(self):
        """Test rendering function entry for Python."""
        renderer = TemplateRenderer("python")
        result = renderer.render(
            "function_entry",
            file_path="my_app/user.py",
            line=42,
            module_name="my_app.user",
            func_name="create",
            signature="def create(attrs: dict, opts: dict) -> User:",
        )
        expected = "my_app/user.py:42\nmy_app.user.create\nType: def create(attrs: dict, opts: dict) -> User:"
        assert result == expected
