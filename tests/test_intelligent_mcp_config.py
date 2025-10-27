#!/usr/bin/env python
"""
Demonstrate intelligent .mcp.json generation based on installation method.
"""

import json
from cicada.install import detect_installation_method


def test_detection():
    """Test installation method detection."""
    print("=" * 60)
    print("Intelligent MCP Configuration Test")
    print("=" * 60)

    command, args, cwd, description = detect_installation_method()

    print("\n📋 Detection Results:")
    print(f"   Method: {description}")
    print(f"   Command: {command}")
    print(f"   Args: {args if args else '(none)'}")
    print(f"   CWD: {cwd if cwd else '(none)'}")

    # Show what .mcp.json would look like
    print("\n📝 Generated .mcp.json would be:")
    print("-" * 60)

    server_config = {"command": command}
    if args:
        server_config["args"] = args
    if cwd:
        server_config["cwd"] = cwd
    server_config["env"] = {"CICADA_REPO_PATH": "/path/to/project"}

    mcp_config = {"mcpServers": {"cicada": server_config}}

    print(json.dumps(mcp_config, indent=2))
    print("-" * 60)

    # Explain what it means
    print("\n💡 What this means:")

    if command == "cicada-server":
        print("   ✅ OPTIMAL: Using 'cicada-server' command")
        print("   • Installed via: uv tool install")
        print("   • Startup: Fast (~100ms)")
        print("   • Portability: Works on any machine")
        print("   • No hardcoded paths needed")
        print("\n   This is the recommended setup!")

    else:
        print("   ⚠️  FALLBACK: Using Python directly")
        print("   • Running from: Source directory")
        print("   • Startup: Slower (~500ms)")
        print("   • Portability: Paths hardcoded")
        print("\n   💡 Recommendation: Install permanently for better performance:")
        print("      cd /path/to/cicada")
        print("      uv tool install .")

    # Test scenarios
    print("\n" + "=" * 60)
    print("Installation Scenarios")
    print("=" * 60)

    scenarios = [
        {
            "name": "✨ Scenario 1: After 'uv tool install .'",
            "check": "cicada-server in PATH",
            "result": "Command: cicada-server (optimal)",
            "config": {"command": "cicada-server"},
        },
        {
            "name": "📦 Scenario 2: Running from source",
            "check": "Python directly",
            "result": "Command: python /path/to/cicada/...",
            "config": {
                "command": "python",
                "args": ["/path/to/cicada/cicada/mcp_server.py"],
                "cwd": "/path/to/cicada",
            },
        },
        {
            "name": "⚡ Scenario 3: After 'uvx cicada-setup'",
            "check": "Temporary uvx environment",
            "result": "Falls back to Python (one-time run)",
            "config": {"command": "python", "args": ["..."], "cwd": "..."},
        },
    ]

    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print(f"   Check: {scenario['check']}")
        print(f"   Result: {scenario['result']}")

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print("\nFor the best experience:")
    print("1. Install once: uv tool install .")
    print("2. Run setup per project: cicada-setup")
    print("3. MCP config is auto-generated optimally")
    print("\nBenefit: Fast MCP server startup, no path dependencies! 🚀")


if __name__ == "__main__":
    test_detection()
