FROM python:3.11-slim

WORKDIR /app

# Install uv for faster dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml ./
COPY uv.lock* ./
COPY cicada ./cicada
COPY README.md ./

# Install the package
RUN uv pip install --system --no-cache .

# The entry point will be specified by smithery.yaml's commandFunction
CMD ["cicada-mcp"]
