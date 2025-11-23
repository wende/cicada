# CICADA Devcontainer Configuration

This directory contains the configuration for GitHub Codespaces and VS Code devcontainers.

## What it does

The `devcontainer.json` configuration creates a fully-functional development environment with:

- **Python 3.11**: Base development environment
- **Node.js LTS**: Required for SCIP-Python indexer
- **Automatic dependency installation**: Runs `pip install -e .` on container creation
- **Global SCIP-Python**: Installs `@sourcegraph/scip-python` globally
- **VS Code extensions**: Pre-configures Python and Pylance extensions

## Usage

### GitHub Codespaces
1. Go to the repository on GitHub
2. Click "Code" → "Codespaces" → "Create codespace on main"
3. Wait for the container to build and dependencies to install
4. Start coding!

### VS Code Devcontainers
1. Install the "Dev Containers" extension in VS Code
2. Open the repository in VS Code
3. Click "Reopen in Container" when prompted (or use Command Palette: "Dev Containers: Reopen in Container")
4. Wait for the container to build
5. Start coding!

## Customization

To modify the environment:
- **Add Node packages**: Update `postCreateCommand` with additional `npm install` commands
- **Add Python packages**: Update `pyproject.toml` instead of modifying this config
- **Add VS Code extensions**: Add extension IDs to the `customizations.vscode.extensions` array
- **Change Python version**: Update the `image` field (e.g., `python:3.12` instead of `python:3.11`)

## Troubleshooting

### Container fails to build
- Check the "Terminal" output in VS Code/Codespaces for error messages
- Verify all commands in `postCreateCommand` are valid
- Try rebuilding: Command Palette → "Dev Containers: Rebuild Container"

### Dependencies not installing
- The `postCreateCommand` runs after the container is created
- Check that `pyproject.toml` is present in the repository root
- Verify Node.js is available: `node --version` in the terminal

## References

- [Devcontainer specification](https://containers.dev/)
- [GitHub Codespaces documentation](https://docs.github.com/en/codespaces)
- [VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers)
