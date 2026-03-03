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
import signal
import sys
import time
import urllib.error
import urllib.request

# --- Interrupt handling ---

_interrupted = False


def _handle_interrupt(signum, frame):
    global _interrupted
    _interrupted = True
    print("\n⚠️  Interrupted! Writing partial results...", file=sys.stderr)


signal.signal(signal.SIGINT, _handle_interrupt)
signal.signal(signal.SIGTERM, _handle_interrupt)


# --- Time formatting ---


def format_eta(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        return f"{int(seconds // 3600)}h {int(seconds % 3600 // 60)}m"


# --- Registry checks ---


def check_registry(name: str, url_template: str) -> bool:
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
    """Run all checks on a candidate name."""
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
        "--pre-filter",
        type=str,
        default=None,
        help="Comma-separated substrings: only check candidates containing one of these",
    )
    args = parser.parse_args()

    from output import print_output_summary, resolve_output_path

    # Resolve paths
    if os.sep not in args.out and not os.path.dirname(args.out):
        args.out = resolve_output_path(args.out, args.out_dir)

    if not os.path.exists(args.input) and os.sep not in args.input:
        alt = resolve_output_path(args.input, args.out_dir)
        if os.path.exists(alt):
            args.input = alt

    tsv_out = resolve_output_path(os.path.basename(args.out).replace(".txt", "-full.tsv"), args.out_dir)

    # Load candidates
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Expected: candidates-raw.txt from the generate step.", file=sys.stderr)
        print("Run: python3 scripts/generate.py --seeds 'your,seed,words'", file=sys.stderr)
        sys.exit(1)

    with open(args.input) as f:
        candidates = [line.strip() for line in f if line.strip()]

    if not candidates:
        print("❌ Input file is empty. No candidates to filter.", file=sys.stderr)
        sys.exit(1)

    if args.pre_filter:
        keywords = [k.strip() for k in args.pre_filter.split(",")]
        before = len(candidates)
        candidates = [c for c in candidates if any(k in c for k in keywords)]
        print(f"Pre-filter: {before} → {len(candidates)} candidates (keywords: {', '.join(keywords)})", file=sys.stderr)

    if args.limit:
        candidates = candidates[: args.limit]

    # Checkpoint: load already-checked names
    already_checked = set()
    if args.resume and os.path.exists(tsv_out):
        already_checked = load_checkpoint(tsv_out)
        print(
            f"📋 Resuming: {len(already_checked)} already checked, {len(candidates) - len(already_checked)} remaining",
            file=sys.stderr,
        )
    elif os.path.exists(tsv_out) and not args.resume:
        # Starting fresh — clear old TSV
        os.remove(tsv_out)

    # Estimate time
    remaining = [c for c in candidates if c not in already_checked]
    total_remaining = len(remaining)
    est_seconds = total_remaining * args.delay * 4  # 4 API calls per candidate
    print("", file=sys.stderr)
    print(f"🔍 Checking {len(candidates)} candidates ({total_remaining} remaining)", file=sys.stderr)
    print(f"⏱️  Estimated time: {format_eta(est_seconds)}", file=sys.stderr)
    if total_remaining > 500:
        print("💡 Tip: Use --pre-filter or --limit for faster results. Use --resume if interrupted.", file=sys.stderr)
    print("", file=sys.stderr)

    # Write TSV header if new file
    if not os.path.exists(tsv_out):
        append_result_tsv(tsv_out, {}, write_header=True)
        # Remove the empty result line we'd write — just write header
        with open(tsv_out, "w") as f:
            f.write("name\tnpm\tpypi\tcrates\tgithub\tverdict\n")

    # Process
    clean = []
    results = []
    checked_count = len(already_checked)
    start_time = time.time()
    errors = 0

    for _i, name in enumerate(candidates):
        if _interrupted:
            break

        if name in already_checked:
            continue

        try:
            result = check_candidate(name, args.delay)
        except Exception as e:
            errors += 1
            print(f"  ⚠️  [{checked_count + 1}/{len(candidates)}] {name}: ERROR ({e})", file=sys.stderr)
            if errors >= 10:
                print("", file=sys.stderr)
                print(f"❌ Too many errors ({errors}). Stopping.", file=sys.stderr)
                print("   This usually means an API is rate-limiting or unreachable.", file=sys.stderr)
                print("   Try again later or increase --delay.", file=sys.stderr)
                break
            continue

        results.append(result)
        checked_count += 1

        # Incremental write to TSV (survives crashes)
        append_result_tsv(tsv_out, result)

        status = result["verdict"]
        gh = result["github"] if result["github"] is not None else "?"

        if status in ("CLEAN", "LIKELY_OK"):
            clean.append(result)

        # Progress with ETA
        elapsed = time.time() - start_time
        rate = (checked_count - len(already_checked)) / max(elapsed, 0.1)
        remaining_count = total_remaining - (checked_count - len(already_checked))
        eta = remaining_count / max(rate, 0.001)

        print(
            f"  [{checked_count}/{len(candidates)}] {name}: {status} (gh:{gh}) | ETA: {format_eta(eta)}",
            file=sys.stderr,
        )

    # Write clean candidates
    with open(args.out, "w") as f:
        for r in clean:
            f.write(f"{r['name']}\n")

    # Also include any clean results from checkpoint
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
    taken = sum(1 for r in results if r["verdict"] == "TAKEN")
    check = sum(1 for r in results if r["verdict"] == "CHECK")

    print("", file=sys.stderr)

    if _interrupted:
        print(f"⚠️  Interrupted after {checked_count}/{len(candidates)} candidates.", file=sys.stderr)
        print("   Partial results saved. Run with --resume to continue.", file=sys.stderr)
    elif errors >= 10:
        print(f"⚠️  Stopped after {errors} errors. Partial results saved.", file=sys.stderr)
        print("   Run with --resume to continue later.", file=sys.stderr)
    else:
        print(f"✅ Done! Checked {checked_count} candidates.", file=sys.stderr)

    print(f"   {len(clean)} clean, {check} needs-check, {taken} taken", file=sys.stderr)

    if errors > 0 and errors < 10:
        print(f"   {errors} errors (skipped)", file=sys.stderr)

    print("", file=sys.stderr)
    print_output_summary(
        [
            (f"{len(clean)} clean candidates", args.out),
            ("Full results (TSV)", tsv_out),
        ]
    )

    if _interrupted:
        print("▶️  Resume: python3 scripts/filter.py --resume", file=sys.stderr)


if __name__ == "__main__":
    main()
