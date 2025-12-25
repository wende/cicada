# Go + scip-go complete environment
# Includes Go runtime and scip-go indexer

FROM cicada-base

# Install Go
RUN apt-get update && apt-get install -y \
    golang-go \
    && rm -rf /var/lib/apt/lists/*

# Install scip-go
ENV GOPATH=/root/go
ENV PATH=$PATH:/root/go/bin
RUN go install github.com/sourcegraph/scip-go/cmd/scip-go@latest

# Verify scip-go is installed
RUN scip-go --help > /dev/null 2>&1 && echo "✓ scip-go installed"

WORKDIR /workspace
