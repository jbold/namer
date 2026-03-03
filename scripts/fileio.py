"""
Shared I/O helpers for namer scripts.
Candidate loading, path resolution, and result writing.
"""

import os
import sys


def resolve_input(input_path: str, out_dir: str | None = None) -> str:
    """Resolve input file path — check cwd first, then output dir.
    Returns the resolved path (may not exist — caller should validate).
    """
    if os.path.exists(input_path):
        return input_path
    if os.sep not in input_path and not os.path.dirname(input_path):
        from output import resolve_output_path
        alt = resolve_output_path(input_path, out_dir)
        if os.path.exists(alt):
            return alt
    return input_path  # return original — caller handles missing file error


def resolve_output(output_path: str, out_dir: str | None = None) -> str:
    """Resolve output file path — bare filenames go into the output dir."""
    if os.sep not in output_path and not os.path.dirname(output_path):
        from output import resolve_output_path
        return resolve_output_path(output_path, out_dir)
    return output_path


def load_candidates(filepath: str, step_name: str = "previous", run_hint: str = "") -> list[str]:
    """Load candidate names from a file (one per line, tab-separated OK).
    Exits with guidance if file is missing or empty.
    """
    if not os.path.exists(filepath):
        print(f"❌ Input file not found: {filepath}", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"Expected: output from the {step_name} step.", file=sys.stderr)
        if run_hint:
            print(f"Run: {run_hint}", file=sys.stderr)
        sys.exit(1)

    with open(filepath) as f:
        candidates = [line.strip().split("\t")[0] for line in f if line.strip()]

    if not candidates:
        print(f"❌ Input file is empty: {filepath}", file=sys.stderr)
        sys.exit(1)

    return candidates


def apply_pre_filter(candidates: list[str], pre_filter: str | None) -> list[str]:
    """Filter candidates to only those containing one of the comma-separated keywords."""
    if not pre_filter:
        return candidates
    keywords = [k.strip().lower() for k in pre_filter.split(",")]
    before = len(candidates)
    filtered = [c for c in candidates if any(k in c.lower() for k in keywords)]
    print(
        f"Pre-filter: {before} → {len(filtered)} candidates (keywords: {', '.join(keywords)})",
        file=sys.stderr,
    )
    return filtered
