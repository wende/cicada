#!/bin/bash
# Entrypoint script for cicada-all-scip Docker image
# Enables SCIP indexers based on SCIP_ENABLE environment variable
#
# Usage:
#   SCIP_ENABLE=go         # Enable Go indexer only
#   SCIP_ENABLE=go,java    # Enable Go and Java indexers
#   SCIP_ENABLE=all        # Enable all indexers
#   (unset)                # No indexers enabled (test graceful failure)

# Map language names to SCIP directories
declare -A SCIP_PATHS=(
    ["go"]="/opt/scip/go/bin"
    ["java"]="/opt/scip/java/bin"
    ["scala"]="/opt/scip/java/bin"  # Uses same coursier as Java
    ["ruby"]="/opt/scip/ruby/bin"
    ["dart"]="/opt/scip/dart/bin"
    ["csharp"]="/opt/scip/dotnet/bin"
    ["vb"]="/opt/scip/dotnet/bin"  # Uses same scip-dotnet as C#
    ["c"]="/opt/scip/clang/bin"
    ["cpp"]="/opt/scip/clang/bin"  # Uses same scip-clang as C
    ["dotnet"]="/opt/scip/dotnet/bin"  # Alias
    ["clang"]="/opt/scip/clang/bin"    # Alias
)

ALL_PATHS="/opt/scip/go/bin:/opt/scip/java/bin:/opt/scip/ruby/bin:/opt/scip/dart/bin:/opt/scip/dotnet/bin:/opt/scip/clang/bin"

if [ -n "$SCIP_ENABLE" ]; then
    if [ "$SCIP_ENABLE" = "all" ]; then
        export PATH="$ALL_PATHS:$PATH"
        echo "[scip-entrypoint] Enabled all SCIP indexers"
    else
        # Parse comma-separated list
        IFS=',' read -ra LANGS <<< "$SCIP_ENABLE"
        EXTRA_PATH=""
        for lang in "${LANGS[@]}"; do
            lang=$(echo "$lang" | tr '[:upper:]' '[:lower:]' | xargs)  # lowercase and trim
            if [ -n "${SCIP_PATHS[$lang]}" ]; then
                if [ -z "$EXTRA_PATH" ]; then
                    EXTRA_PATH="${SCIP_PATHS[$lang]}"
                else
                    # Avoid duplicates
                    if [[ ":$EXTRA_PATH:" != *":${SCIP_PATHS[$lang]}:"* ]]; then
                        EXTRA_PATH="$EXTRA_PATH:${SCIP_PATHS[$lang]}"
                    fi
                fi
            else
                echo "[scip-entrypoint] Warning: Unknown language '$lang'"
            fi
        done
        if [ -n "$EXTRA_PATH" ]; then
            export PATH="$EXTRA_PATH:$PATH"
            echo "[scip-entrypoint] Enabled: $SCIP_ENABLE (PATH += $EXTRA_PATH)"
        fi
    fi
else
    echo "[scip-entrypoint] No SCIP indexers enabled (SCIP_ENABLE not set)"
fi

# Execute the command
exec "$@"
