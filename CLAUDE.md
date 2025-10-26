# CICADA - AI Assistant Guidelines

This file contains project-specific instructions for AI assistants working on the CICADA codebase.

## Release Process

When creating a new release:

1. **Create and push the git tag:**
   ```bash
   git tag v0.X.Y
   git push origin v0.X.Y
   ```

2. **Update README.md version references:**
   - Search for all instances of `@v0.1.0` in README.md
   - Replace with the new version tag `@v0.X.Y`
   - Locations to update:
     - Quick Install section (stable release command)
     - Try Before Installing section (stable release command)
     - Migration tip section

3. **Update pyproject.toml version:**
   - Update the `version = "0.1.0"` field to match the new release

4. **Test the installation:**
   ```bash
   uv tool install git+https://github.com/wende/cicada.git@v0.X.Y
   ```

## Project Context

- **Language Support:** Currently Elixir only. Python and TypeScript are planned.
- **Primary Installation Method:** uv tool install (recommended over Python direct install)
- **Index Location:** `.cicada/` directory in project root

## Code Style

- Use `black` for Python code formatting
- Include type hints where appropriate
- Write tests for new features
- Keep functions focused and modular

- When searching through the Elixir codebase, use the cicada-mcp MCP server tools instead of grep/find commands for better accuracy and context.
