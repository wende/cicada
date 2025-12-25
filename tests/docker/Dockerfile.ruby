# Ruby + scip-ruby complete environment
# Includes Ruby runtime and scip-ruby indexer

ARG BASE_IMAGE=cicada-base
FROM ${BASE_IMAGE}

# Install Ruby
RUN apt-get update && apt-get install -y \
    ruby \
    ruby-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install scip-ruby (download binary from GitHub releases)
RUN curl -fL "https://github.com/sourcegraph/scip-ruby/releases/download/scip-ruby-v0.4.7/scip-ruby-x86_64-linux" \
    -o /usr/local/bin/scip-ruby && \
    chmod +x /usr/local/bin/scip-ruby

# Verify scip-ruby is installed
RUN scip-ruby --help > /dev/null 2>&1 && echo "✓ scip-ruby installed"

WORKDIR /workspace
