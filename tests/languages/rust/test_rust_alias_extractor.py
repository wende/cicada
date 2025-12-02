"""Tests for the Rust alias extractor helper."""

from cicada.languages.rust.alias_extractor import RustAliasExtractor


SOURCE = """
use crate::services::payment::Processor as PaymentProcessor;
use crate::models::user::User;
use crate::utils::{foo, bar as Baz};
use std::collections::{HashMap, HashSet};
""".strip()


def test_extracts_aliases_from_various_use_statements(tmp_path):
    rust_file = tmp_path / "lib.rs"
    rust_file.write_text(SOURCE)

    extractor = RustAliasExtractor()
    aliases = extractor.extract_aliases(rust_file)

    assert aliases == {
        "PaymentProcessor": "crate::services::payment::Processor",
        "User": "crate::models::user::User",
        "foo": "crate::utils::foo",
        "Baz": "crate::utils::bar",
        "HashMap": "std::collections::HashMap",
        "HashSet": "std::collections::HashSet",
    }


def test_handles_multiline_use_blocks(tmp_path):
    source = """
    pub use crate::logging::{
        Logger,
        formatter::Formatter as LogFormatter,
    };
    """.strip()
    rust_file = tmp_path / "logging.rs"
    rust_file.write_text(source)

    extractor = RustAliasExtractor()
    aliases = extractor.extract_aliases(rust_file)

    assert aliases == {
        "Logger": "crate::logging::Logger",
        "LogFormatter": "crate::logging::formatter::Formatter",
    }
