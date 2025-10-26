#!/bin/bash
# Create minimal test fixture for CI and local testing

set -e

FIXTURE_DIR="tests/fixtures/test_project"

echo "Creating test fixture project..."

# Create directory structure
mkdir -p "$FIXTURE_DIR/lib/test_app"

# Create mix.exs
cat > "$FIXTURE_DIR/mix.exs" << 'EOF'
defmodule TestApp.MixProject do
  use Mix.Project

  def project do
    [
      app: :test_app,
      version: "0.1.0",
      elixir: "~> 1.14"
    ]
  end
end
EOF

# Create main module
cat > "$FIXTURE_DIR/lib/test_app.ex" << 'EOF'
defmodule TestApp do
  @moduledoc """
  A test application for Cicada acceptance tests.
  """

  @doc """
  Returns a greeting message.

  ## Examples

      iex> TestApp.hello()
      "Hello, World!"

  """
  @spec hello() :: String.t()
  def hello do
    "Hello, World!"
  end

  @doc """
  Adds two numbers together.

  ## Examples

      iex> TestApp.add_numbers(2, 3)
      5

  """
  @spec add_numbers(integer(), integer()) :: integer()
  def add_numbers(a, b), do: a + b

  @doc """
  Processes a value.
  Used for testing history tracking.
  """
  @spec process_value(any()) :: any()
  def process_value(value), do: value
end
EOF

# Create math module
cat > "$FIXTURE_DIR/lib/test_app/math.ex" << 'EOF'
defmodule TestApp.Math do
  @moduledoc """
  Math utilities for testing.
  """

  @doc """
  Multiplies two numbers.
  """
  @spec multiply(number(), number()) :: number()
  def multiply(a, b), do: a * b

  @doc """
  Divides two numbers.
  """
  @spec divide(number(), number()) :: float()
  def divide(a, b) when b != 0, do: a / b
end
EOF

echo "✓ Test fixture project created at $FIXTURE_DIR"
