#!/bin/bash
# Cicada Quick Install Script
# Usage: curl -sSL https://raw.githubusercontent.com/USERNAME/cicada/main/install.sh | bash

set -e

GITHUB_URL="${CICADA_GITHUB_URL:-https://github.com/USERNAME/cicada.git}"
INSTALL_DIR="${CICADA_INSTALL_DIR:-$HOME/.cicada}"

echo "=================================="
echo "Cicada MCP Quick Install"
echo "=================================="
echo ""
echo "Install Dir: $INSTALL_DIR"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python 3.10+ required. Found: $PYTHON_VERSION"
    exit 1
fi

# Clone or update cicada
if [ -d "$INSTALL_DIR" ]; then
    echo "Cicada already installed at $INSTALL_DIR"
    echo "Updating..."
    cd "$INSTALL_DIR"
    git fetch --tags
    LATEST_TAG=$(git describe --tags --abbrev=0)
    if [ -n "$LATEST_TAG" ]; then
        echo "Checking out latest release: $LATEST_TAG"
        git checkout "$LATEST_TAG"
    else
        echo "No tags found, staying on current branch"
    fi
else
    echo "Downloading cicada..."
    git clone "$GITHUB_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    git fetch --tags
    LATEST_TAG=$(git describe --tags --abbrev=0)
    if [ -n "$LATEST_TAG" ]; then
        echo "Checking out latest release: $LATEST_TAG"
        git checkout "$LATEST_TAG"
    else
        echo "No tags found, using main branch"
    fi
fi

# Run setup
cd "$INSTALL_DIR"
python3 setup.py

echo ""
echo "=================================="
echo "Installation complete!"
echo "=================================="
