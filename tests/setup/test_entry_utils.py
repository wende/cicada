from __future__ import annotations

from cicada.entry_utils import prepare_argv


def test_prepare_argv_inserts_install_for_unknown_token():
    normalized = prepare_argv(
        ["cicada", "/tmp/project"],
        default_on_unknown="install",
        default_on_none="install",
    )
    assert normalized[1:3] == ["install", "/tmp/project"]


def test_prepare_argv_appends_default_and_extras_when_no_args():
    normalized = prepare_argv(
        ["cicada-mcp"],
        default_on_unknown="server",
        default_on_none="server",
        default_on_unknown_args=["--keywords"],
        default_on_none_args=["--keywords"],
    )
    assert normalized == ["cicada-mcp", "server", "--keywords"]


def test_prepare_argv_inserts_extra_args_for_unknown_token():
    normalized = prepare_argv(
        ["cicada-mcp", "/repo"],
        default_on_unknown="server",
        default_on_none="server",
        default_on_unknown_args=["--keywords"],
        default_on_none_args=["--keywords"],
    )
    assert normalized[1:4] == ["server", "--keywords", "/repo"]


def test_prepare_argv_uses_callable_for_default(monkeypatch):
    calls = {"count": 0}

    def resolver():
        calls["count"] += 1
        return "server"

    normalized = prepare_argv(
        ["cicada-mcp"],
        default_on_unknown="server",
        default_on_none=resolver,
        default_on_unknown_args=["--keywords"],
        default_on_none_args=["--keywords"],
    )
    assert calls["count"] == 1
    assert normalized == ["cicada-mcp", "server", "--keywords"]
