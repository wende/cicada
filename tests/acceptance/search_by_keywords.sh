#!/bin/bash
# Usage: ./tests/acceptance/search_by_keywords.sh keyword1 keyword2 keyword3
# Example: ./tests/acceptance/search_by_keywords.sh performance benchmark test

# Check if keywords were provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 keyword1 [keyword2] [keyword3] ..."
    echo "Example: $0 performance benchmark test"
    exit 1
fi

# Convert arguments to Python list format
KEYWORDS="["
for keyword in "$@"; do
    KEYWORDS="$KEYWORDS'$keyword', "
done
KEYWORDS="${KEYWORDS%, }]"

echo "Searching for keywords: $KEYWORDS"
echo "========================================"
echo ""

uv run python -c "
import asyncio
from cicada.mcp_server import CicadaServer

async def search():
    server = CicadaServer(config_path='tests/fixtures/elixir_project/.cicada/config.yaml')
    result = await server._search_by_keywords($KEYWORDS)
    print(result[0].text)

asyncio.run(search())
"
