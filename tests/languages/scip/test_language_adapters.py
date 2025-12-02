"""Tests for language adapter selection used by SCIP converter."""

from types import SimpleNamespace

import pytest

from cicada.languages.scip.language_adapters import get_language_adapter


class TestAdapterRegistry:
    def test_python_adapter_uses_python_alias_extractor(self, tmp_path, monkeypatch):
        called = {}

        class DummyExtractor:
            def extract_aliases(self, path):
                called["path"] = path
                return {"alias": "module.symbol"}

        monkeypatch.setattr(
            "cicada.languages.python.alias_extractor.PythonAliasExtractor",
            DummyExtractor,
        )

        python_file = tmp_path / "module.py"
        python_file.write_text("import math")
        doc = SimpleNamespace(relative_path="module.py")

        adapter = get_language_adapter("python")
        result = adapter.extract_aliases(doc, tmp_path)

        assert result == {"alias": "module.symbol"}
        assert called["path"] == python_file

    def test_rust_adapter_uses_rust_alias_extractor(self, tmp_path):
        rust_source = """
        use crate::services::payment::Processor as PaymentProcessor;
        """.strip()
        rust_file = tmp_path / "src" / "lib.rs"
        rust_file.parent.mkdir(parents=True, exist_ok=True)
        rust_file.write_text(rust_source)
        doc = SimpleNamespace(relative_path="src/lib.rs")

        adapter = get_language_adapter("rust")
        result = adapter.extract_aliases(doc, tmp_path)

        assert result == {"PaymentProcessor": "crate::services::payment::Processor"}

    def test_unknown_language_raises(self):
        with pytest.raises(KeyError):
            get_language_adapter("go")
