"""
Custom setuptools configuration for cicada-mcp.

This setup.py provides a custom build step to generate SCIP protobuf files
before building the package. This ensures that scip_pb2.py and scip_pb2.pyi
are available at runtime without requiring manual generation.
"""

import os
import subprocess
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithProtobuf(build_py):
    """Custom build command that generates protobuf files before building."""

    def run(self):
        """Run protobuf generation, then normal build."""
        self.generate_protobuf()
        super().run()

    def generate_protobuf(self):
        """Generate SCIP protobuf files using protoc or grpcio-tools."""
        scip_dir = Path(__file__).parent / "cicada" / "languages" / "scip"
        proto_file = scip_dir / "scip.proto"
        pb2_file = scip_dir / "scip_pb2.py"
        pyi_file = scip_dir / "scip_pb2.pyi"

        # Skip if files already exist and are up to date
        if pb2_file.exists() and pyi_file.exists():
            if pb2_file.stat().st_mtime > proto_file.stat().st_mtime:
                print("SCIP protobuf files are up to date, skipping generation")
                return

        print("Generating SCIP protobuf files...")

        # Try grpcio-tools first (guaranteed compatible version as build dependency)
        try:
            # Import grpc_tools here to avoid build-time dependency issues
            from grpc_tools import protoc as grpc_protoc

            # Run protoc via grpc_tools with absolute paths
            result = grpc_protoc.main(
                [
                    "grpc_tools.protoc",
                    f"-I{scip_dir}",
                    f"--python_out={scip_dir}",
                    f"--pyi_out={scip_dir}",
                    str(proto_file),
                ],
            )

            if result != 0:
                raise RuntimeError(f"grpc_tools.protoc failed with code {result}")

            print("✓ Generated SCIP protobuf files (via grpcio-tools)")
            return
        except Exception as e:
            print(f"Warning: Could not generate protobuf files via grpcio-tools: {e}")

        # Fallback to system protoc (if available)
        try:
            subprocess.run(
                [
                    "protoc",
                    "-I.",
                    "--python_out=.",
                    "--pyi_out=.",
                    "scip.proto",
                ],
                cwd=scip_dir,
                check=True,
                capture_output=True,
            )
            print("✓ Generated SCIP protobuf files (via system protoc)")
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # If all methods failed, raise an error
        print(
            "\n" + "=" * 70,
            file=sys.stderr,
        )
        print(
            "ERROR: Failed to generate SCIP protobuf files",
            file=sys.stderr,
        )
        print("=" * 70, file=sys.stderr)
        print(
            "\nCicada requires protobuf code generation for SCIP support.",
            file=sys.stderr,
        )
        print("Please install one of the following:", file=sys.stderr)
        print("  1. protoc (Protocol Buffer Compiler)", file=sys.stderr)
        print("  2. grpcio-tools (pip install grpcio-tools)", file=sys.stderr)
        print("\nOr run: make generate-scip-proto", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        sys.exit(1)


# Use setup() from pyproject.toml but with custom build command
setup(
    cmdclass={
        "build_py": BuildWithProtobuf,
    },
)
