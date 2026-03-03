#!/usr/bin/env python3
"""
Name filtering pipeline — Step 2: Automated namespace collision checking.
Zero LLM tokens. Pure API checks.

Affordances:
  - Progress bar with ETA
  - Incremental writes (partial results survive crashes)
  - Checkpoint/resume (--resume to pick up where you left off)
  - Graceful interrupt (Ctrl+C writes partial results before exit)
  - Clear success/failure output with next steps

Usage:
    python3 filter.py [--input candidates-raw.txt] [--out candidates-filtered.txt] [--delay 0.3]
    python3 filter.py --resume   # resume from last checkpoint
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

from fileio import apply_pre_filter, load_candidates, resolve_input, resolve_output
from output import print_output_summary, resolve_output_path
from progress import InterruptHandler, ProgressTracker, format_eta

# --- Registry checks ---


def check_registry(name: str, url_template: str) -> bool | None:
    """Check if a name exists on a package registry. Returns True if TAKEN."""
    url = url_template.format(name=name)
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "namer-skill/1.0")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        return None
    except Exception:
        return None


def check_github_count(name: str) -> int | None:
    """Get GitHub repo count for a name."""
    url = f"https://api.github.com/search/repositories?q={name}&per_page=1"
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "namer-skill/1.0")
        req.add_header("Accept", "application/vnd.github.v3+json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("total_count", 0)
    except Exception:
        return None


def check_candidate(name: str, delay: float) -> dict:
    """Run all registry checks on a candidate name."""
    result = {"name": name}

    result["npm"] = check_registry(name, "https://registry.npmjs.org/{name}")
    time.sleep(delay)

    result["pypi"] = check_registry(name, "https://pypi.org/pypi/{name}/json")
    time.sleep(delay)

    result["crates"] = check_registry(name, "https://crates.io/api/v1/crates/{name}")
    time.sleep(delay)

    result["github"] = check_github_count(name)
    time.sleep(delay)

    # Verdict
    registry_hits = sum(1 for k in ["npm", "pypi", "crates"] if result[k] is True)
    gh = result["github"] or 0

    if registry_hits == 0 and gh < 5:
        result["verdict"] = "CLEAN"
    elif registry_hits == 0 and gh < 20:
        result["verdict"] = "LIKELY_OK"
    elif registry_hits <= 1 and gh < 50:
        result["verdict"] = "CHECK"
    else:
        result["verdict"] = "TAKEN"

    return result


# --- Checkpoint ---


def load_checkpoint(checkpoint_path: str) -> set:
    """Load already-checked names from checkpoint file."""
    checked = set()
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path) as f:
            f.readline()  # skip header
            for line in f:
                parts = line.strip().split("\t")
                if parts:
                    checked.add(parts[0])
    return checked


def append_result_tsv(filepath: str, result: dict, write_header: bool = False):
    """Append a single result to the TSV file."""
    with open(filepath, "a") as f:
        if write_header:
            f.write("name\tnpm\tpypi\tcrates\tgithub\tverdict\n")
        f.write(
            f"{result['name']}\t{result['npm']}\t{result['pypi']}\t"
            f"{result['crates']}\t{result['github']}\t{result['verdict']}\n"
        )


def main():
    parser = argparse.ArgumentParser(description="Filter naming candidates by namespace availability")
    parser.add_argument("--input", type=str, default="candidates-raw.txt")
    parser.add_argument("--out", type=str, default="candidates-filtered.txt")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory (default: ./namer-output/)")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between API calls (seconds)")
    parser.add_argument("--limit", type=int, default=None, help="Max candidates to check (for testing)")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument(
        "--pre-filter", type=str, default=None,
        help="Comma-separated substrings: only check candidates containing one of these",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show per-item progress (default: summary only)")
    args = parser.parse_args()

    # Resolve paths
    args.out = resolve_output(args.out, args.out_dir)
    args.input = resolve_input(args.input, args.out_dir)
    tsv_out = resolve_output_path(os.path.basename(args.out).replace(".txt", "-full.tsv"), args.out_dir)

    # Load and filter candidates
    candidates = load_candidates(
        args.input, step_name="generate",
        run_hint="python3 scripts/generate.py --seeds 'your,seed,words'",
    )
    candidates = apply_pre_filter(candidates, args.pre_filter)

    if args.limit:
        candidates = candidates[: args.limit]

    # Checkpoint: load already-checked names
    already_checked = set()
    if args.resume and os.path.exists(tsv_out):
        already_checked = load_checkpoint(tsv_out)
        print(
            f"📋 Resuming: {len(already_checked)} already checked, "
            f"{len(candidates) - len(already_checked)} remaining",
            file=sys.stderr,
        )
    elif os.path.exists(tsv_out) and not args.resume:
        os.remove(tsv_out)

    # Estimate time
    remaining_names = [c for c in candidates if c not in already_checked]
    total_remaining = len(remaining_names)
    est_seconds = total_remaining * args.delay * 4  # 4 API calls per candidate

    print("", file=sys.stderr)
    print(f"🔍 Checking {len(candidates)} candidates ({total_remaining} remaining)", file=sys.stderr)
    print(f"⏱️  Estimated time: {format_eta(est_seconds)}", file=sys.stderr)
    if total_remaining > 500:
        print("💡 Tip: Use --pre-filter or --limit for faster results. Use --resume if interrupted.", file=sys.stderr)
    print("", file=sys.stderr)

    # Write TSV header if new file
    if not os.path.exists(tsv_out):
        with open(tsv_out, "w") as f:
            f.write("name\tnpm\tpypi\tcrates\tgithub\tverdict\n")

    # Process with shared progress tracker
    interrupt = InterruptHandler()
    tracker = ProgressTracker(
        total=len(candidates), already_done=len(already_checked),
        max_errors=10, interrupt=interrupt, verbose=args.verbose,
    )

    clean = []
    results = []

    for name in candidates:
        if tracker.should_stop():
            break
        if name in already_checked:
            continue

        try:
            result = check_candidate(name, args.delay)
        except Exception as e:
            if not tracker.record_error(f"{name}: ERROR ({e})"):
                break
            continue

        results.append(result)
        append_result_tsv(tsv_out, result)  # incremental write

        if result["verdict"] in ("CLEAN", "LIKELY_OK"):
            clean.append(result)

        gh = result["github"] if result["github"] is not None else "?"
        tracker.tick(f"{name}: {result['verdict']} (gh:{gh})")

    # Write clean candidates
    with open(args.out, "w") as f:
        for r in clean:
            f.write(f"{r['name']}\n")

    # Include clean results from checkpoint
    if already_checked and os.path.exists(tsv_out):
        with open(tsv_out) as f:
            f.readline()  # skip header
            for line in f:
                parts = line.strip().split("\t")
                if (
                    len(parts) >= 6
                    and parts[5] in ("CLEAN", "LIKELY_OK")
                    and parts[0] not in {r["name"] for r in clean}
                ):
                    with open(args.out, "a") as out:
                        out.write(f"{parts[0]}\n")

    # Summary
    tracker.finish_line()
    taken = sum(1 for r in results if r["verdict"] == "TAKEN")
    check = sum(1 for r in results if r["verdict"] == "CHECK")

    if tracker.was_interrupted:
        print(f"⚠️  Interrupted after {tracker.done}/{len(candidates)} candidates.", file=sys.stderr)
        print("   Partial results saved. Run with --resume to continue.", file=sys.stderr)
    elif tracker.hit_error_limit:
        print(f"⚠️  Stopped after {tracker.errors} errors. Partial results saved.", file=sys.stderr)
        print("   Run with --resume to continue later.", file=sys.stderr)
    else:
        print(f"✅ Done! Checked {tracker.done} candidates.", file=sys.stderr)

    print(f"   {len(clean)} clean, {check} needs-check, {taken} taken", file=sys.stderr)

    if tracker.errors > 0 and not tracker.hit_error_limit:
        print(f"   {tracker.errors} errors (skipped)", file=sys.stderr)

    print("", file=sys.stderr)
    print_output_summary([
        (f"{len(clean)} clean candidates", args.out),
        ("Full results (TSV)", tsv_out),
    ])

    if tracker.was_interrupted:
        print("▶️  Resume: python3 scripts/filter.py --resume", file=sys.stderr)


if __name__ == "__main__":
    main()
