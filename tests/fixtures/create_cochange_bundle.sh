#!/bin/bash
# Create a git bundle with known co-change patterns for testing
# This script generates cochange_test_repo.bundle with strategic commits

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_PATH="$SCRIPT_DIR/cochange_test_repo.bundle"
TEMP_REPO=$(mktemp -d)

cleanup() {
    rm -rf "$TEMP_REPO"
}
trap cleanup EXIT

echo "Creating test repository in $TEMP_REPO..."
cd "$TEMP_REPO"

# Initialize git repo with test user
git init
git config user.name "Test User"
git config user.email "test@example.com"
git config commit.gpgsign false

mkdir -p lib

# Commit 1: Add auth.ex and credentials.ex together (co-change 1)
cat > lib/auth.ex << 'EOF'
defmodule Auth do
  def login(username, password) do
    {:ok, "token"}
  end

  def logout(token) do
    :ok
  end
end
EOF

cat > lib/credentials.ex << 'EOF'
defmodule Credentials do
  def validate(username, password) do
    true
  end

  def hash(password) do
    "hashed"
  end
end
EOF

git add .
git commit -m "Initial: Add auth and credentials modules"

# Commit 2: Update both together (co-change 2)
cat > lib/auth.ex << 'EOF'
defmodule Auth do
  def login(username, password) do
    case Credentials.validate(username, password) do
      true -> {:ok, "token"}
      false -> {:error, "invalid"}
    end
  end

  def logout(token) do
    :ok
  end

  def refresh(token) do
    {:ok, "new_token"}
  end
end
EOF

cat > lib/credentials.ex << 'EOF'
defmodule Credentials do
  def validate(username, password) do
    password != ""
  end

  def hash(password) do
    "hashed_#{password}"
  end

  def compare(plain, hashed) do
    plain == hashed
  end
end
EOF

git add .
git commit -m "Update auth and credentials with validation logic"

# Commit 3: Update auth and credentials again (co-change 3)
cat > lib/auth.ex << 'EOF'
defmodule Auth do
  def login(username, password) do
    case Credentials.validate(username, password) do
      true -> {:ok, generate_token()}
      false -> {:error, "invalid"}
    end
  end

  def logout(token) do
    :ok
  end

  def refresh(token) do
    {:ok, generate_token()}
  end

  defp generate_token() do
    "token_#{System.monotonic_time()}"
  end
end
EOF

cat > lib/credentials.ex << 'EOF'
defmodule Credentials do
  def validate(username, password) do
    password != "" and String.length(password) >= 8
  end

  def hash(password) do
    "hashed_#{password}"
  end

  def compare(plain, hashed) do
    plain == hashed
  end

  def requirements() do
    [min_length: 8, special_chars: true]
  end
end
EOF

git add .
git commit -m "Add token generation and password requirements"

# Commit 4: Add logger alone (single-file commit for edge case testing)
cat > lib/logger.ex << 'EOF'
defmodule Logger do
  def log(level, message) do
    IO.puts("[#{level}] #{message}")
  end

  def error(message) do
    log(:error, message)
  end

  def info(message) do
    log(:info, message)
  end
end
EOF

git add .
git commit -m "Add logger module"

# Commit 5: Update auth and logger together (new co-change pair)
cat > lib/auth.ex << 'EOF'
defmodule Auth do
  def login(username, password) do
    Logger.info("Login attempt for #{username}")

    case Credentials.validate(username, password) do
      true ->
        Logger.info("Login successful")
        {:ok, generate_token()}
      false ->
        Logger.error("Login failed for #{username}")
        {:error, "invalid"}
    end
  end

  def logout(token) do
    Logger.info("Logout")
    :ok
  end

  def refresh(token) do
    {:ok, generate_token()}
  end

  defp generate_token() do
    "token_#{System.monotonic_time()}"
  end
end
EOF

cat > lib/logger.ex << 'EOF'
defmodule Logger do
  def log(level, message) do
    IO.puts("[#{level}] #{message}")
  end

  def error(message) do
    log(:error, message)
  end

  def info(message) do
    log(:info, message)
  end

  def debug(message) do
    log(:debug, message)
  end
end
EOF

git add .
git commit -m "Integrate logging into auth module"

# Commit 6: Old-dated commit (for date filtering tests - 60 days ago)
OLD_DATE=$(date -d "60 days ago" "+%Y-%m-%dT%H:%M:%S" 2>/dev/null || date -v-60d "+%Y-%m-%dT%H:%M:%S")
GIT_AUTHOR_DATE="$OLD_DATE" GIT_COMMITTER_DATE="$OLD_DATE" \
git commit --allow-empty -m "Historical: Old auth and credentials state"

# Commit 7: Rename scenario (old_name.ex -> new_name.ex)
cat > lib/old_name.ex << 'EOF'
defmodule OldName do
  def old_function() do
    :result
  end
end
EOF

cat > lib/companion.ex << 'EOF'
defmodule Companion do
  def helper() do
    OldName.old_function()
  end
end
EOF

git add .
git commit -m "Add old_name and companion modules"

# Commit 8: Rename old_name.ex to new_name.ex and update companion
git mv lib/old_name.ex lib/new_name.ex

cat > lib/companion.ex << 'EOF'
defmodule Companion do
  def helper() do
    NewName.new_function()
  end
end
EOF

git add .
git commit -m "Rename old_name to new_name and update companion"

# Commit 9: Add modules with functions for function-level co-change testing
cat > lib/module_a.ex << 'EOF'
defmodule ModuleA do
  def func_one(x) do
    x + 1
  end

  def func_two(x) do
    x + 2
  end
end
EOF

cat > lib/module_b.ex << 'EOF'
defmodule ModuleB do
  def func_three(x) do
    x + 3
  end
end
EOF

git add .
git commit -m "Initial: Add ModuleA and ModuleB with functions"

# Commit 10: Update both modules' functions together
cat > lib/module_a.ex << 'EOF'
defmodule ModuleA do
  def func_one(x) do
    x + 10
  end

  def func_two(x) do
    x + 2
  end
end
EOF

cat > lib/module_b.ex << 'EOF'
defmodule ModuleB do
  def func_three(x) do
    x + 30
  end
end
EOF

git add .
git commit -m "Update ModuleA.func_one and ModuleB.func_three"

# Commit 11: Update both modules again
cat > lib/module_a.ex << 'EOF'
defmodule ModuleA do
  def func_one(x) do
    x + 100
  end

  def func_two(x) do
    x + 2
  end
end
EOF

cat > lib/module_b.ex << 'EOF'
defmodule ModuleB do
  def func_three(x) do
    x + 300
  end
end
EOF

git add .
git commit -m "Update ModuleA.func_one and ModuleB.func_three again"

# Create the bundle
echo "Creating bundle..."
git bundle create "$BUNDLE_PATH" --all

# Verify the bundle
echo "Verifying bundle..."
git bundle verify "$BUNDLE_PATH" > /dev/null

BUNDLE_SIZE=$(du -h "$BUNDLE_PATH" | cut -f1)
echo "✅ Bundle created successfully: $BUNDLE_PATH ($BUNDLE_SIZE)"
echo ""
echo "Bundle contents:"
echo "  - 11 commits total"
echo "  - lib/auth.ex + lib/credentials.ex: 4 co-changes"
echo "  - lib/auth.ex + lib/logger.ex: 2 co-changes"
echo "  - lib/old_name.ex → lib/new_name.ex: rename scenario"
echo "  - ModuleA.func_one + ModuleB.func_three: function-level co-changes"
echo ""
echo "Test with:"
echo "  git clone $BUNDLE_PATH /tmp/test_cochange"
