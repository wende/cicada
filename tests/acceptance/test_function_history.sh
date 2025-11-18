#!/bin/bash
# Usage: ./tests/acceptance/test_function_history.sh [file_path] [function_name] [OPTIONS]
# Options:
#   -f, --function NAME      Function name to track (default: get_pr_info)
#   -e, --evolution          Include evolution metadata
#   -n, --limit N            Maximum commits to show (default: 5)
#   -l, --line-mode          Use line-based tracking instead of function tracking
#   --start LINE             Starting line for line-based mode
#   --end LINE               Ending line for line-based mode
#
# Examples:
#   # Track function across file (even as it moves)
#   ./tests/acceptance/test_function_history.sh cicada/git_helper.py get_pr_info
#
#   # With evolution metadata
#   ./tests/acceptance/test_function_history.sh cicada/git_helper.py get_pr_info --evolution
#
#   # Line-based tracking
#   ./tests/acceptance/test_function_history.sh cicada/git_helper.py --line-mode --start 40 --end 80
#
#   # Limit commits
#   ./tests/acceptance/test_function_history.sh README.md --line-mode --start 1 --end 50 -n 3

# Default values
FILE_PATH="${1:-cicada/git_helper.py}"
FUNCTION_NAME="get_pr_info"
WITH_EVOLUTION="False"
MAX_COMMITS=5
LINE_MODE="False"
START_LINE=""
END_LINE=""

# Shift first argument (file_path)
shift 2>/dev/null || true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--function)
            FUNCTION_NAME="$2"
            shift 2
            ;;
        -e|--evolution)
            WITH_EVOLUTION="True"
            shift
            ;;
        -n|--limit)
            if [[ $2 =~ ^[0-9]+$ ]]; then
                MAX_COMMITS=$2
                shift 2
            else
                echo "Error: --limit requires a numeric argument"
                exit 1
            fi
            ;;
        -l|--line-mode)
            LINE_MODE="True"
            shift
            ;;
        --start)
            if [[ $2 =~ ^[0-9]+$ ]]; then
                START_LINE=$2
                shift 2
            else
                echo "Error: --start requires a numeric argument"
                exit 1
            fi
            ;;
        --end)
            if [[ $2 =~ ^[0-9]+$ ]]; then
                END_LINE=$2
                shift 2
            else
                echo "Error: --end requires a numeric argument"
                exit 1
            fi
            ;;
        *)
            # Treat non-option as function name
            FUNCTION_NAME="$1"
            shift
            ;;
    esac
done

# Determine config path from centralized storage
if [[ -d "tests/fixtures/test_project" ]]; then
    FIXTURE_DIR="$(cd tests/fixtures/test_project && pwd)"
elif [[ -d "tests/fixtures/elixir_project" ]]; then
    FIXTURE_DIR="$(cd tests/fixtures/elixir_project && pwd)"
else
    FIXTURE_DIR="$(pwd)"
fi

if command -v uv >/dev/null 2>&1; then
    CONFIG_PATH=$(uv run python3 -c "
from cicada.utils.storage import get_config_path
print(get_config_path('$FIXTURE_DIR'))
")
else
    CONFIG_PATH=$(python3 -c "
from cicada.utils.storage import get_config_path
print(get_config_path('$FIXTURE_DIR'))
")
fi

# Build arguments for runner
RUNNER_ARGS=("file_history" "$FILE_PATH")

if [[ "$LINE_MODE" == "True" ]]; then
    # Line-based tracking (requires both start and end)
    if [[ -z "$START_LINE" || -z "$END_LINE" ]]; then
        echo "Error: Line mode requires --start and --end parameters"
        exit 1
    fi
    RUNNER_ARGS+=("--line-mode" "--start" "$START_LINE" "--end" "$END_LINE")
else
    # Function-based tracking
    if [[ -n "$FUNCTION_NAME" ]]; then
        RUNNER_ARGS+=("--function" "$FUNCTION_NAME")
    fi

    if [[ -n "$START_LINE" && -n "$END_LINE" ]]; then
        # Function tracking with fallback line numbers
        RUNNER_ARGS+=("--start" "$START_LINE" "--end" "$END_LINE")
    fi
fi

if [[ "$WITH_EVOLUTION" == "True" ]]; then
    RUNNER_ARGS+=("--evolution")
fi

if [[ "$MAX_COMMITS" != "5" ]]; then
    RUNNER_ARGS+=("--limit" "$MAX_COMMITS")
fi

uv run python tests/acceptance/runner.py "${RUNNER_ARGS[@]}"
