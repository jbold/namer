"""
Shared output directory logic for namer scripts.

Default: ./namer-output/ relative to working directory.
Override: --out-dir flag or NAMER_OUTPUT_DIR env var.

All scripts use resolve_output_path() to get the full path for their output files.
"""

import os
import sys

DEFAULT_OUTPUT_DIR = "namer-output"
ENV_VAR = "NAMER_OUTPUT_DIR"


def get_output_dir(cli_out_dir: str | None = None) -> str:
    """Resolve output directory. Priority: CLI flag > env var > default.
    Creates the directory if it doesn't exist.
    Returns absolute path.
    """
    out_dir = cli_out_dir or os.environ.get(ENV_VAR) or DEFAULT_OUTPUT_DIR
    out_dir = os.path.abspath(out_dir)

    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
        print(f"Created output directory: {out_dir}", file=sys.stderr)

    return out_dir


def resolve_output_path(filename: str, cli_out_dir: str | None = None) -> str:
    """Get full path for an output file inside the output directory."""
    return os.path.join(get_output_dir(cli_out_dir), filename)


def print_output_summary(files: list[tuple[str, str]]) -> None:
    """Print a summary of where output files were written.
    files: list of (label, filepath) tuples.
    """
    print("", file=sys.stderr)
    print("📁 Output files:", file=sys.stderr)
    for label, filepath in files:
        print(f"  {label}: {filepath}", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"Override output location with --out-dir or {ENV_VAR} env var.", file=sys.stderr)
