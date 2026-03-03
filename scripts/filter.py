#!/usr/bin/env python3
"""
Name filtering pipeline — Step 2: Automated namespace collision checking.
Zero LLM tokens. Pure API checks.

Usage:
    python3 filter.py [--input candidates-raw.txt] [--out candidates-filtered.txt] [--delay 0.3]

Checks: npm, PyPI, crates.io, GitHub repos (count).
Outputs TSV: name \t npm \t pypi \t crates \t github_count \t verdict
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error


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
        return None  # Unknown
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

    # Verdict: CLEAN if no registry hits and low GitHub count
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


def main():
    parser = argparse.ArgumentParser(description="Filter naming candidates by namespace availability")
    parser.add_argument("--input", type=str, default="candidates-raw.txt")
    parser.add_argument("--out", type=str, default="candidates-filtered.txt")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between API calls (seconds)")
    parser.add_argument("--limit", type=int, default=None, help="Max candidates to check (for testing)")
    parser.add_argument("--pre-filter", type=str, default=None,
                        help="Comma-separated keywords: only check candidates containing one of these substrings")
    args = parser.parse_args()

    with open(args.input) as f:
        candidates = [line.strip() for line in f if line.strip()]

    if args.pre_filter:
        keywords = [k.strip() for k in args.pre_filter.split(",")]
        candidates = [c for c in candidates if any(k in c for k in keywords)]

    if args.limit:
        candidates = candidates[:args.limit]

    print(f"Checking {len(candidates)} candidates...", file=sys.stderr)

    results = []
    clean = []
    for i, name in enumerate(candidates):
        result = check_candidate(name, args.delay)
        results.append(result)
        status = result["verdict"]
        gh = result["github"] if result["github"] is not None else "?"
        print(f"  [{i+1}/{len(candidates)}] {name}: {status} (gh:{gh})", file=sys.stderr)
        if status in ("CLEAN", "LIKELY_OK"):
            clean.append(result)

    # Write full results as TSV
    tsv_out = args.out.replace(".txt", "-full.tsv")
    with open(tsv_out, "w") as f:
        f.write("name\tnpm\tpypi\tcrates\tgithub\tverdict\n")
        for r in results:
            f.write(f"{r['name']}\t{r['npm']}\t{r['pypi']}\t{r['crates']}\t{r['github']}\t{r['verdict']}\n")

    # Write clean candidates only
    with open(args.out, "w") as f:
        for r in clean:
            f.write(f"{r['name']}\n")

    taken = sum(1 for r in results if r["verdict"] == "TAKEN")
    check = sum(1 for r in results if r["verdict"] == "CHECK")
    print(f"\nResults: {len(clean)} clean, {check} needs-check, {taken} taken", file=sys.stderr)
    print(f"Clean candidates → {args.out}", file=sys.stderr)
    print(f"Full results → {tsv_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
