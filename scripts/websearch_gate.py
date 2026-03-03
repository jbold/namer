#!/usr/bin/env python3
"""
Name web search gate — Check if candidates have existing product/service presence.
Auto-discovers available search provider from environment.

Supported providers (checked in order):
  - Brave Search:   BRAVE_API_KEY
  - Serper:          SERPER_API_KEY
  - Google Custom:   GOOGLE_API_KEY + GOOGLE_CSE_ID
  - SearXNG:         SEARXNG_URL (self-hosted, no key needed)

Usage:
    python3 websearch_gate.py --input candidates-filtered.txt --out candidates-gated.txt
    python3 websearch_gate.py --input candidates-filtered.txt --provider brave --api-key KEY
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse


# --- Search Provider Implementations ---

def search_brave(query: str, api_key: str) -> list[dict]:
    """Brave Search API."""
    url = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(query)}&count=5"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("X-Subscription-Token", api_key)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return [
                {"title": r.get("title", ""), "url": r.get("url", ""), "description": r.get("description", "")}
                for r in data.get("web", {}).get("results", [])[:5]
            ]
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"  Rate limited, waiting 2s...", file=sys.stderr)
            time.sleep(2)
            return search_brave(query, api_key)
        raise


def search_serper(query: str, api_key: str) -> list[dict]:
    """Serper.dev API (Google results)."""
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query, "num": 5}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("X-API-KEY", api_key)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return [
                {"title": r.get("title", ""), "url": r.get("link", ""), "description": r.get("snippet", "")}
                for r in data.get("organic", [])[:5]
            ]
    except Exception as e:
        print(f"  Serper error: {e}", file=sys.stderr)
        return []


def search_google(query: str, api_key: str, cse_id: str) -> list[dict]:
    """Google Custom Search API."""
    url = (
        f"https://www.googleapis.com/customsearch/v1"
        f"?q={urllib.parse.quote(query)}&key={api_key}&cx={cse_id}&num=5"
    )
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return [
                {"title": r.get("title", ""), "url": r.get("link", ""), "description": r.get("snippet", "")}
                for r in data.get("items", [])[:5]
            ]
    except Exception as e:
        print(f"  Google CSE error: {e}", file=sys.stderr)
        return []


def search_searxng(query: str, base_url: str) -> list[dict]:
    """SearXNG self-hosted instance."""
    url = f"{base_url.rstrip('/')}/search?q={urllib.parse.quote(query)}&format=json&categories=general"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "namer-skill/1.0")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return [
                {"title": r.get("title", ""), "url": r.get("url", ""), "description": r.get("content", "")}
                for r in data.get("results", [])[:5]
            ]
    except Exception as e:
        print(f"  SearXNG error: {e}", file=sys.stderr)
        return []


# --- Provider Discovery ---

PROVIDERS = {
    "brave": {"env": ["BRAVE_API_KEY"], "name": "Brave Search"},
    "serper": {"env": ["SERPER_API_KEY"], "name": "Serper (Google)"},
    "google": {"env": ["GOOGLE_API_KEY", "GOOGLE_CSE_ID"], "name": "Google Custom Search"},
    "searxng": {"env": ["SEARXNG_URL"], "name": "SearXNG"},
}


def discover_provider() -> tuple[str, dict]:
    """Auto-discover search provider from environment variables.
    Returns (provider_name, {env_var: value}) or exits with guidance."""
    for name, info in PROVIDERS.items():
        env_vals = {}
        for var in info["env"]:
            val = os.environ.get(var)
            if not val:
                break
            env_vals[var] = val
        if len(env_vals) == len(info["env"]):
            return name, env_vals

    print("Error: No search provider detected.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Set one of these in your environment:", file=sys.stderr)
    print("  BRAVE_API_KEY=...        (https://brave.com/search/api/ — free tier: 2000/month)", file=sys.stderr)
    print("  SERPER_API_KEY=...       (https://serper.dev — $2.50/1000 queries)", file=sys.stderr)
    print("  GOOGLE_API_KEY=... + GOOGLE_CSE_ID=...  (Google Custom Search)", file=sys.stderr)
    print("  SEARXNG_URL=...          (self-hosted, free, no key)", file=sys.stderr)
    print("", file=sys.stderr)
    print("Or pass --provider and --api-key explicitly.", file=sys.stderr)
    sys.exit(1)


def do_search(provider: str, env_vals: dict, query: str) -> list[dict]:
    """Route search to the right provider."""
    if provider == "brave":
        return search_brave(query, env_vals["BRAVE_API_KEY"])
    elif provider == "serper":
        return search_serper(query, env_vals["SERPER_API_KEY"])
    elif provider == "google":
        return search_google(query, env_vals["GOOGLE_API_KEY"], env_vals["GOOGLE_CSE_ID"])
    elif provider == "searxng":
        return search_searxng(query, env_vals["SEARXNG_URL"])
    else:
        print(f"Unknown provider: {provider}", file=sys.stderr)
        sys.exit(1)


# --- Product Presence Check ---

PRODUCT_SIGNALS = [
    "app", "software", "platform", "saas", "tool", "service",
    "download", "pricing", "sign up", "login", "api", "sdk",
    "startup", "inc", "ltd", "gmbh", "solutions", "technologies",
    ".io", ".ai", ".app", "product", "features", "demo",
    "get started", "free trial", "enterprise", "cloud"
]


def check_product_presence(provider: str, env_vals: dict, name: str) -> dict:
    """Check if a name has existing product/service web presence."""
    result = {"name": name, "has_product": False, "signals": [], "top_results": []}

    results = do_search(provider, env_vals, name)

    for r in results:
        title = r.get("title", "").lower()
        desc = r.get("description", "").lower()
        url = r.get("url", "").lower()
        combined = f"{title} {desc} {url}"

        result["top_results"].append({
            "title": r.get("title", "")[:80],
            "url": r.get("url", "")[:80]
        })

        for signal in PRODUCT_SIGNALS:
            if signal in combined:
                result["signals"].append(signal)

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
    parser.add_argument("--provider", type=str, default=None,
                        choices=["brave", "serper", "google", "searxng"],
                        help="Search provider (auto-detected from env if omitted)")
    parser.add_argument("--api-key", type=str, default=None,
                        help="API key (overrides env var for the selected provider)")
    parser.add_argument("--delay", type=float, default=1.1, help="Delay between searches (seconds)")
    args = parser.parse_args()

    # Resolve provider
    if args.provider and args.api_key:
        provider = args.provider
        if provider == "google":
            cse_id = os.environ.get("GOOGLE_CSE_ID", "")
            env_vals = {"GOOGLE_API_KEY": args.api_key, "GOOGLE_CSE_ID": cse_id}
        elif provider == "searxng":
            env_vals = {"SEARXNG_URL": args.api_key}
        else:
            env_key = PROVIDERS[provider]["env"][0]
            env_vals = {env_key: args.api_key}
    elif args.provider:
        # Provider specified, discover key from env
        info = PROVIDERS[args.provider]
        env_vals = {}
        for var in info["env"]:
            val = os.environ.get(var)
            if not val:
                print(f"Error: --provider {args.provider} requires {var} env var", file=sys.stderr)
                sys.exit(1)
            env_vals[var] = val
        provider = args.provider
    else:
        provider, env_vals = discover_provider()

    print(f"Using search provider: {PROVIDERS[provider]['name']}", file=sys.stderr)

    with open(args.input) as f:
        candidates = [line.strip().split("\t")[0] for line in f if line.strip()]

    print(f"Web search gate: checking {len(candidates)} candidates...", file=sys.stderr)

    clear = []
    caution = []
    bumped = []

    for i, name in enumerate(candidates):
        result = check_product_presence(provider, env_vals, name)
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

    print(f"\n{len(clear)} clear, {len(caution)} caution, {len(bumped)} bumped", file=sys.stderr)
    print(f"Survivors → {args.out}", file=sys.stderr)
    print(f"Full report → {report_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
