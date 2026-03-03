#!/usr/bin/env python3
"""
Name web search gate — Step 2b: Check if candidates have existing product/service presence.
Uses Brave Search API. Candidates with product/service results get bumped.

Usage:
    python3 websearch_gate.py --input candidates-filtered.txt --out candidates-gated.txt [--api-key KEY]

Requires BRAVE_API_KEY env var or --api-key flag.
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error


def brave_search(query: str, api_key: str) -> dict:
    """Search Brave and return results."""
    url = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(query)}&count=5"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("X-Subscription-Token", api_key)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"  Rate limited, waiting 2s...", file=sys.stderr)
            time.sleep(2)
            return brave_search(query, api_key)
        raise


import urllib.parse


def check_product_presence(name: str, api_key: str) -> dict:
    """Check if a name has existing product/service web presence."""
    result = {"name": name, "has_product": False, "signals": [], "top_results": []}

    data = brave_search(name, api_key)
    web_results = data.get("web", {}).get("results", [])

    # Product/service signal keywords in titles and descriptions
    product_signals = [
        "app", "software", "platform", "saas", "tool", "service",
        "download", "pricing", "sign up", "login", "api", "sdk",
        "startup", "inc", "ltd", "gmbh", "solutions", "technologies",
        ".io", ".ai", ".app", "product", "features", "demo",
        "get started", "free trial", "enterprise", "cloud"
    ]

    for r in web_results[:5]:
        title = r.get("title", "").lower()
        desc = r.get("description", "").lower()
        url = r.get("url", "").lower()
        combined = f"{title} {desc} {url}"

        result["top_results"].append({
            "title": r.get("title", "")[:80],
            "url": r.get("url", "")[:80]
        })

        for signal in product_signals:
            if signal in combined:
                result["signals"].append(signal)

    # Verdict: if 2+ product signals across results, it's a product
    unique_signals = set(result["signals"])
    if len(unique_signals) >= 2:
        result["has_product"] = True
        result["verdict"] = "BUMPED"
    elif len(unique_signals) == 1:
        result["verdict"] = "CAUTION"
    else:
        result["verdict"] = "CLEAR"

    return result


def main():
    parser = argparse.ArgumentParser(description="Web search gate for naming candidates")
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--out", type=str, default="candidates-gated.txt")
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--delay", type=float, default=1.1, help="Delay between searches (Brave free = 1/sec)")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("BRAVE_API_KEY")
    if not api_key:
        print("Error: Set BRAVE_API_KEY env var or use --api-key", file=sys.stderr)
        sys.exit(1)

    with open(args.input) as f:
        candidates = [line.strip() for line in f if line.strip()]

    print(f"Web search gate: checking {len(candidates)} candidates...", file=sys.stderr)

    clear = []
    caution = []
    bumped = []

    for i, name in enumerate(candidates):
        result = check_product_presence(name, api_key)
        status = result["verdict"]
        signals = ", ".join(list(set(result["signals"]))[:3]) if result["signals"] else "none"
        print(f"  [{i+1}/{len(candidates)}] {name}: {status} (signals: {signals})", file=sys.stderr)

        if status == "CLEAR":
            clear.append(result)
        elif status == "CAUTION":
            caution.append(result)
        else:
            bumped.append(result)

        time.sleep(args.delay)

    # Write clear candidates
    with open(args.out, "w") as f:
        for r in clear + caution:
            f.write(f"{r['name']}\t{r['verdict']}\n")

    # Write full report
    report_out = args.out.replace(".txt", "-report.md")
    with open(report_out, "w") as f:
        f.write("# Web Search Gate Results\n\n")
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

    print(f"\n{len(clear)} clear, {len(caution)} caution, {len(bumped)} bumped", file=sys.stderr)
    print(f"Survivors → {args.out}", file=sys.stderr)
    print(f"Full report → {report_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
