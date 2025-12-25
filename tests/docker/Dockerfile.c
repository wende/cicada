# C/C++ + scip-clang complete environment
# Includes build tools and scip-clang indexer (shared for C and C++)

ARG BASE_IMAGE=cicada-base
FROM ${BASE_IMAGE}

# Install build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install scip-clang (download binary from GitHub releases)
RUN curl -fL "https://github.com/sourcegraph/scip-clang/releases/download/v0.3.2/scip-clang-x86_64-linux" \
    -o /usr/local/bin/scip-clang && \
    chmod +x /usr/local/bin/scip-clang

# Verify scip-clang is installed
RUN scip-clang --help > /dev/null 2>&1 && echo "✓ scip-clang installed"

WORKDIR /workspace
