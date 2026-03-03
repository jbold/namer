#!/usr/bin/env python3
"""
Name web search gate — Check if candidates have existing product/service presence.

Uses the search/ package for environment detection, provider discovery, and
product signal analysis. This file is just the CLI entry point.

Usage:
    python3 websearch_gate.py --input candidates-filtered.txt --out candidates-gated.txt
    python3 websearch_gate.py --input candidates-filtered.txt --provider brave --api-key KEY
    python3 websearch_gate.py --detect  # just print what's available and exit
"""

import argparse
import os
import shutil
import sys
import time

from fileio import load_candidates, resolve_input, resolve_output
from output import print_output_summary, resolve_output_path
from progress import InterruptHandler, ProgressTracker, format_eta
from search.detect import detect_environment
from search.providers import PROVIDERS, discover_provider
from search.signals import check_product_presence


def _run_detect() -> None:
    """Detect-only mode: print environment and available providers."""
    env_info = detect_environment()
    print(f"Environment: {env_info['env_label']}")
    if env_info["mcp_search_tools"]:
        print("MCP search tools:")
        for t in env_info["mcp_search_tools"]:
            print(f"  - {t['name']} (from {t['config_path']})")
    else:
        print("MCP search tools: none found")
    print()
    for _name, info in PROVIDERS.items():
        vals = {var: os.environ.get(var) for var in info["env"]}
        if all(vals.values()):
            print(f"Env var provider: {info['name']} ✓")
        else:
            missing = [k for k, v in vals.items() if not v]
            print(f"Env var provider: {info['name']} ✗ (missing: {', '.join(missing)})")
    for cmd, label in {"ddgr": "DuckDuckGo", "googler": "Google", "s": "Surfraw"}.items():
        found = "✓" if shutil.which(cmd) else "✗"
        print(f"CLI tool: {label} ({cmd}) {found}")


def _resolve_provider(args) -> tuple[str, dict]:
    """Resolve provider from CLI args or auto-detect."""
    if args.provider and args.api_key:
        provider = args.provider
        if provider == "google":
            cse_id = os.environ.get("GOOGLE_CSE_ID", "")
            return provider, {"GOOGLE_API_KEY": args.api_key, "GOOGLE_CSE_ID": cse_id}
        elif provider == "searxng":
            return provider, {"SEARXNG_URL": args.api_key}
        else:
            env_key = PROVIDERS[provider]["env"][0]
            return provider, {env_key: args.api_key}
    elif args.provider:
        info = PROVIDERS[args.provider]
        env_vals = {}
        for var in info["env"]:
            val = os.environ.get(var)
            if not val:
                print(f"Error: --provider {args.provider} requires {var} env var", file=sys.stderr)
                sys.exit(1)
            env_vals[var] = val
        return args.provider, env_vals
    else:
        return discover_provider()


def _write_report(report_path: str, provider: str, clear: list, caution: list, bumped: list) -> None:
    """Write the full markdown report."""
    with open(report_path, "w") as f:
        f.write("# Web Search Gate Results\n\n")
        f.write(f"Provider: {PROVIDERS[provider]['name']}\n\n")

        f.write(f"## CLEAR ({len(clear)})\n")
        for r in clear:
            f.write(f"- **{r['name']}** — no product signals\n")

        f.write(f"\n## CAUTION ({len(caution)})\n")
        for r in caution:
            f.write(f"- **{r['name']}** — weak signal: {', '.join(set(r['signals']))}\n")
            for tr in r["top_results"][:2]:
                f.write(f"  - {tr['title']}: {tr['url']}\n")

        f.write(f"\n## BUMPED ({len(bumped)})\n")
        for r in bumped:
            f.write(f"- **{r['name']}** — product signals: {', '.join(set(r['signals']))}\n")
            for tr in r["top_results"][:2]:
                f.write(f"  - {tr['title']}: {tr['url']}\n")


def main():
    parser = argparse.ArgumentParser(description="Web search gate for naming candidates")
    parser.add_argument("--input", type=str, help="Input candidates file")
    parser.add_argument("--out", type=str, default="candidates-gated.txt", help="Output filename")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory (default: ./namer-output/)")
    parser.add_argument(
        "--provider", type=str, default=None,
        choices=["brave", "serper", "google", "searxng"],
        help="Search provider (auto-detected if omitted)",
    )
    parser.add_argument("--api-key", type=str, default=None, help="API key (overrides env var)")
    parser.add_argument("--delay", type=float, default=1.1, help="Delay between searches (seconds)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show per-item progress (default: summary only)")
    parser.add_argument("--detect", action="store_true", help="Detect environment and exit")
    args = parser.parse_args()

    if args.detect:
        _run_detect()
        return

    if not args.input:
        parser.error("--input is required (or use --detect)")

    # Resolve paths
    args.out = resolve_output(args.out, args.out_dir)
    args.input = resolve_input(args.input, args.out_dir)
    report_out = resolve_output_path(os.path.basename(args.out).replace(".txt", "-report.md"), args.out_dir)

    # Resolve provider
    provider, env_vals = _resolve_provider(args)
    print(f"🔎 Using search provider: {PROVIDERS[provider]['name']}", file=sys.stderr)

    # Load candidates
    candidates = load_candidates(
        args.input, step_name="filter",
        run_hint="python3 scripts/filter.py",
    )

    # Estimate
    est_seconds = len(candidates) * args.delay
    print("", file=sys.stderr)
    print(f"🔍 Web search gate: {len(candidates)} candidates", file=sys.stderr)
    print(f"⏱️  Estimated time: {format_eta(est_seconds)}", file=sys.stderr)
    print("", file=sys.stderr)

    # Process with shared progress tracker
    interrupt = InterruptHandler()
    tracker = ProgressTracker(total=len(candidates), max_errors=10, interrupt=interrupt, verbose=args.verbose)

    clear = []
    caution = []
    bumped = []

    for name in candidates:
        if tracker.should_stop():
            break

        try:
            result = check_product_presence(provider, env_vals, name)
        except Exception as e:
            if not tracker.record_error(f"{name}: ERROR ({e})"):
                break
            continue

        signals = ", ".join(list(set(result["signals"]))[:3]) if result["signals"] else "none"
        tracker.tick(f"{name}: {result['verdict']} (signals: {signals})")

        if result["verdict"] == "CLEAR":
            clear.append(result)
        elif result["verdict"] == "CAUTION":
            caution.append(result)
        else:
            bumped.append(result)

        time.sleep(args.delay)

    # Write outputs
    with open(args.out, "w") as f:
        for r in clear + caution:
            f.write(f"{r['name']}\t{r['verdict']}\n")

    _write_report(report_out, provider, clear, caution, bumped)

    # Summary
    tracker.finish_line()
    if tracker.hit_error_limit:
        print(f"⚠️  Stopped after {tracker.errors} errors. Partial results saved.", file=sys.stderr)
    else:
        print(f"✅ Done! {len(clear)} clear, {len(caution)} caution, {len(bumped)} bumped", file=sys.stderr)

    if tracker.errors > 0 and not tracker.hit_error_limit:
        print(f"   {tracker.errors} errors (skipped)", file=sys.stderr)

    print("", file=sys.stderr)
    print_output_summary([
        (f"{len(clear) + len(caution)} survivors", args.out),
        ("Full report", report_out),
    ])


if __name__ == "__main__":
    main()
