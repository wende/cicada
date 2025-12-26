# SCIP Language Docker Tests

End-to-end tests for all SCIP languages in clean Docker environments.

## Quick Start

### Recommended: Fast All-in-One Tests

```bash
# Test all languages (builds once, runs fast)
./test-scip-languages.sh

# Test specific languages
./test-scip-languages.sh go java ruby
```

This uses a single Docker image with all SCIP indexers pre-installed but isolated.
PATH manipulation enables/disables each indexer per test.

### Legacy: Per-Language Dockerfiles

```bash
# Slower - builds separate image per language
./test-single-language.sh go
./test-all-languages.sh
```

## Test Philosophy

Each language is tested in two scenarios:

1. **Without deps** (SCIP_ENABLE unset) - Indexer hidden from PATH
   - Verifies graceful failure with helpful error message
   - Should show installation instructions

2. **With deps** (SCIP_ENABLE=<lang>) - Indexer in PATH
   - Verifies successful indexing
   - Should show "Indexed N files" message

## Architecture

### All-in-One Image (`Dockerfile.all-scip`)

Single image with everything pre-installed:
- All language runtimes (Go, Java, Ruby, Dart, .NET, C/C++ tools)
- All SCIP indexers in isolated directories:
  - `/opt/scip/go/bin/scip-go`
  - `/opt/scip/java/bin/cs` (coursier)
  - `/opt/scip/ruby/bin/scip-ruby`
  - `/opt/scip/dart/bin/scip_dart`
  - `/opt/scip/dotnet/bin/scip-dotnet`
  - `/opt/scip/clang/bin/scip-clang`

### Entrypoint (`scip-entrypoint.sh`)

Manipulates PATH based on `SCIP_ENABLE` environment variable:

```bash
# No indexers in PATH
docker run cicada-all-scip cicada claude

# Go indexer in PATH
docker run -e SCIP_ENABLE=go cicada-all-scip cicada claude

# Multiple indexers
docker run -e SCIP_ENABLE=go,java cicada-all-scip cicada claude

# All indexers
docker run -e SCIP_ENABLE=all cicada-all-scip cicada claude
```

## Language Mapping

| Language | SCIP_ENABLE | Indexer | Shared With | arm64 Support |
|----------|-------------|---------|-------------|---------------|
| Go | `go` | scip-go | - | ✅ |
| Java | `java` | coursier (cs) | Scala | ✅ |
| Scala | `scala` | coursier (cs) | Java | ✅ |
| Ruby | `ruby` | scip-ruby | - | ❌ (x86_64 only) |
| Dart | `dart` | scip_dart | - | ✅ |
| C | `c` | scip-clang | C++ | ❌ (x86_64 only) |
| C++ | `cpp` | scip-clang | C | ❌ (x86_64 only) |
| C# | `csharp` | scip-dotnet | VB | ✅ |
| VB | `vb` | scip-dotnet | C# | ✅ |

> **Note:** Ruby and C/C++ tests will fail on arm64 Linux (Docker on Apple Silicon) because
> the upstream SCIP indexers only provide x86_64-linux binaries. There is no arm64-linux
> support from Sourcegraph for these tools. Ruby has arm64-darwin (macOS native) but not
> arm64-linux. CI runs on amd64 where all languages are tested.

## Expected Results

### Without Deps (Graceful Failure)

```
$ docker run cicada-all-scip cicada claude
[scip-entrypoint] No SCIP indexers enabled (SCIP_ENABLE not set)
Go indexer not found. Install via: go install github.com/sourcegraph/scip-go@latest
```

### With Deps (Success)

```
$ docker run -e SCIP_ENABLE=go cicada-all-scip cicada claude
[scip-entrypoint] Enabled: go (PATH += /opt/scip/go/bin)
Indexed 1 files, 1 modules, 6 functions
```

## Building the Image

```bash
# Build all-in-one image
docker build -t cicada-all-scip -f Dockerfile.all-scip ../..

# Or let the test script build it
./test-scip-languages.sh
```

## Output

The test script produces a summary table:

```
═══════════════════════════════════════════
                  SUMMARY
═══════════════════════════════════════════
Language   No Deps         With Deps
──────────────────────────────────────────
go         PASS            PASS
java       PASS            PASS
ruby       PASS            PASS
...
```

## CI Integration

SCIP language tests run automatically on push and PR via GitHub Actions.

The CI workflow (`.github/workflows/test-scip-languages.yml`) installs indexers directly
on the runner (no Docker) for faster execution. Each language runs as a separate matrix job.

**Docker is for local testing** - provides clean isolated environment with PATH manipulation.
**CI uses direct installation** - faster since runners are already ephemeral.

## Files

| File | Description |
|------|-------------|
| `Dockerfile.all-scip` | All-in-one image with all SCIP indexers |
| `scip-entrypoint.sh` | PATH manipulation entrypoint |
| `test-scip-languages.sh` | Fast test runner (recommended) |
| `Dockerfile.base` | Minimal Cicada-only image |
| `Dockerfile.*` | Per-language images (legacy) |
| `test-single-language.sh` | Single language test (legacy) |
| `test-all-languages.sh` | All languages test (legacy) |
| `../../.github/workflows/test-scip-languages.yml` | CI workflow |
