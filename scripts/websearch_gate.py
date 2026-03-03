#!/usr/bin/env python3
"""
Name web search gate — Check if candidates have existing product/service presence.

Discovery order:
  1. Detect agent environment (Claude Code, OpenClaw, Cursor, etc.)
  2. Scan MCP configs for search tools (brave-search, web-search, etc.)
  3. Check environment variables (BRAVE_API_KEY, SERPER_API_KEY, etc.)
  4. Check for CLI search tools on PATH (ddgr, googler, etc.)
  5. If nothing found, prompt user to set up Brave Search API (free tier)

Usage:
    python3 websearch_gate.py --input candidates-filtered.txt --out candidates-gated.txt
    python3 websearch_gate.py --input candidates-filtered.txt --provider brave --api-key KEY
    python3 websearch_gate.py --detect  # just print what's available and exit
"""

import argparse
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# --- Environment Detection ---

AGENT_ENVIRONMENTS = {
    "claude-code": {
        "indicators": ["~/.claude", ".claude"],
        "mcp_configs": ["~/.claude/mcp.json", ".claude/mcp.json", "~/.claude.json"],
        "name": "Claude Code",
    },
    "cursor": {
        "indicators": ["~/.cursor"],
        "mcp_configs": ["~/.cursor/mcp.json"],
        "name": "Cursor",
    },
    "openclaw": {
        "indicators": ["~/.openclaw"],
        "mcp_configs": ["~/.openclaw/openclaw.json"],
        "name": "OpenClaw",
    },
    "windsurf": {
        "indicators": ["~/.codeium"],
        "mcp_configs": ["~/.codeium/windsurf/mcp_config.json"],
        "name": "Windsurf",
    },
    "vscode": {
        "indicators": [],
        "mcp_configs": [".vscode/mcp.json"],
        "name": "VS Code",
    },
}

# MCP tool names that provide web search capability
SEARCH_MCP_TOOLS = {
    "brave-search",
    "brave_search",
    "brave_web_search",
    "web-search",
    "web_search",
    "google-search",
    "google_search",
    "serper",
    "serper-search",
    "tavily",
    "tavily-search",
    "tavily_search",
    "exa",
    "exa-search",
    "exa_search",
    "searxng",
    "searxng-search",
    "bing-search",
    "bing_search",
}


def expand_path(p: str) -> str:
    return os.path.expanduser(os.path.expandvars(p))


def detect_environment() -> dict:
    """Detect what agent environment we're running in.
    Returns {env_name, env_label, mcp_search_tools: [{name, config_path}]}
    """
    result = {"env_name": None, "env_label": "unknown", "mcp_search_tools": []}

    for env_name, info in AGENT_ENVIRONMENTS.items():
        found = any(os.path.exists(expand_path(p)) for p in info["indicators"])
        if not found:
            continue

        result["env_name"] = env_name
        result["env_label"] = info["name"]

        # Scan MCP configs for search tools (read-only, never logs or exfiltrates keys)
        for config_path in info["mcp_configs"]:
            full_path = expand_path(config_path)
            if not os.path.isfile(full_path):
                continue

            try:
                with open(full_path) as f:
                    config = json.load(f)

                # Different config formats
                servers = {}
                if "mcpServers" in config:
                    servers = config["mcpServers"]  # Claude Code / Cursor format
                elif "mcp" in config and "servers" in config.get("mcp", {}):
                    servers = config["mcp"]["servers"]  # OpenClaw format
                elif "servers" in config:
                    servers = config["servers"]  # Generic

                for server_name, server_config in servers.items():
                    name_lower = server_name.lower().replace("-", "_").replace(" ", "_")
                    # Check if server name matches known search tools
                    if name_lower in {t.replace("-", "_") for t in SEARCH_MCP_TOOLS}:
                        result["mcp_search_tools"].append(
                            {
                                "name": server_name,
                                "config_path": full_path,
                                "server_config": server_config,
                            }
                        )
                        continue

                    # Check command/args for search-related keywords
                    cmd = server_config.get("command", "")
                    args = " ".join(server_config.get("args", []))
                    combined = f"{cmd} {args}".lower()
                    if any(
                        kw in combined
                        for kw in ["brave", "serper", "tavily", "exa", "searx", "web-search", "web_search"]
                    ):
                        result["mcp_search_tools"].append(
                            {
                                "name": server_name,
                                "config_path": full_path,
                                "server_config": server_config,
                            }
                        )

            except (json.JSONDecodeError, OSError, KeyError):
                continue

        if result["env_name"]:
            break  # Use first matching environment

    return result


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
            print("  Rate limited, waiting 2s...", file=sys.stderr)
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
    url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(query)}&key={api_key}&cx={cse_id}&num=5"
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


def discover_provider(verbose: bool = True) -> tuple[str, dict]:
    """Auto-discover search provider. Checks MCP configs, env vars, and CLI tools.
    Returns (provider_name, {env_var: value}) or exits with guidance."""

    env_info = detect_environment()

    if verbose and env_info["env_name"]:
        print(f"Detected environment: {env_info['env_label']}", file=sys.stderr)

    # 1. Check MCP search tools
    if env_info["mcp_search_tools"]:
        tools = env_info["mcp_search_tools"]
        tool_names = [t["name"] for t in tools]
        if verbose:
            print(f"Found MCP search tools: {', '.join(tool_names)}", file=sys.stderr)
            print("", file=sys.stderr)
            print("Your agent has search via MCP. You have two options:", file=sys.stderr)
            print("  1. Let your agent use its MCP search tool directly (recommended)", file=sys.stderr)
            print("     → Skip this script, have the agent search each candidate inline", file=sys.stderr)
            print("  2. Set the matching API key as an env var for this script", file=sys.stderr)
            print("", file=sys.stderr)

        # Try to extract API key from MCP server config env
        for tool in tools:
            server_env = tool.get("server_config", {}).get("env", {})
            for env_key, env_val in server_env.items():
                # Check if the env value references another env var
                if env_val.startswith("${") and env_val.endswith("}"):
                    actual_var = env_val[2:-1]
                    actual_val = os.environ.get(actual_var)
                    if actual_val:
                        env_val = actual_val

                # Map MCP env vars to our providers
                if env_key == "BRAVE_API_KEY" and env_val:
                    return "brave", {"BRAVE_API_KEY": env_val}
                elif env_key in ("SERPER_API_KEY", "SERPER_KEY") and env_val:
                    return "serper", {"SERPER_API_KEY": env_val}
                elif env_key == "TAVILY_API_KEY" and env_val and verbose:
                    print("  Found Tavily key in MCP config but Tavily provider not yet implemented.", file=sys.stderr)
                    print("  Consider setting BRAVE_API_KEY or SERPER_API_KEY instead.", file=sys.stderr)

    # 2. Check environment variables
    for name, info in PROVIDERS.items():
        env_vals = {}
        for var in info["env"]:
            val = os.environ.get(var)
            if not val:
                break
            env_vals[var] = val
        if len(env_vals) == len(info["env"]):
            return name, env_vals

    # 3. Check CLI search tools on PATH
    cli_tools = {
        "ddgr": "DuckDuckGo (ddgr)",
        "googler": "Google (googler)",
        "s": "Surfraw (s)",
    }
    found_cli = []
    for cmd, label in cli_tools.items():
        if shutil.which(cmd):
            found_cli.append(label)
    if found_cli and verbose:
        print(f"Found CLI search tools: {', '.join(found_cli)}", file=sys.stderr)
        print("  These can't be used directly by this script yet.", file=sys.stderr)
        print("  Set a search API key instead (see below).", file=sys.stderr)
        print("", file=sys.stderr)

    # 4. Nothing found — guide the user
    print("No search provider detected.", file=sys.stderr)
    print("", file=sys.stderr)

    if env_info["mcp_search_tools"]:
        print("You have MCP search tools configured — your agent can search directly.", file=sys.stderr)
        print("To use this script standalone, set one of these env vars:", file=sys.stderr)
    else:
        print("Set one of these in your environment:", file=sys.stderr)

    print("", file=sys.stderr)
    print("  BRAVE_API_KEY=...        (https://brave.com/search/api/ — free tier: 2000/month)", file=sys.stderr)
    print("  SERPER_API_KEY=...       (https://serper.dev — $2.50/1000 queries)", file=sys.stderr)
    print("  GOOGLE_API_KEY=... + GOOGLE_CSE_ID=...  (Google Custom Search)", file=sys.stderr)
    print("  SEARXNG_URL=...          (self-hosted, free, no key)", file=sys.stderr)
    print("", file=sys.stderr)
    print("Recommended default: Brave Search (free, 2000 queries/month, 30 sec signup)", file=sys.stderr)
    print("  → https://brave.com/search/api/", file=sys.stderr)
    print("  → Set: export BRAVE_API_KEY=your_key_here", file=sys.stderr)
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
    "app",
    "software",
    "platform",
    "saas",
    "tool",
    "service",
    "download",
    "pricing",
    "sign up",
    "login",
    "api",
    "sdk",
    "startup",
    "inc",
    "ltd",
    "gmbh",
    "solutions",
    "technologies",
    ".io",
    ".ai",
    ".app",
    "product",
    "features",
    "demo",
    "get started",
    "free trial",
    "enterprise",
    "cloud",
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

        result["top_results"].append({"title": r.get("title", "")[:80], "url": r.get("url", "")[:80]})

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
    parser.add_argument("--input", type=str, help="Input candidates file")
    parser.add_argument("--out", type=str, default="candidates-gated.txt")
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        choices=["brave", "serper", "google", "searxng"],
        help="Search provider (auto-detected if omitted)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key (overrides env var for the selected provider)",
    )
    parser.add_argument("--delay", type=float, default=1.1, help="Delay between searches (seconds)")
    parser.add_argument("--detect", action="store_true", help="Detect environment and available providers, then exit")
    args = parser.parse_args()

    # Detect-only mode
    if args.detect:
        env_info = detect_environment()
        print(f"Environment: {env_info['env_label']}")
        if env_info["mcp_search_tools"]:
            print("MCP search tools:")
            for t in env_info["mcp_search_tools"]:
                print(f"  - {t['name']} (from {t['config_path']})")
        else:
            print("MCP search tools: none found")
        print()
        # Check env vars
        for _name, info in PROVIDERS.items():
            vals = {var: os.environ.get(var) for var in info["env"]}
            if all(vals.values()):
                print(f"Env var provider: {info['name']} ✓")
            else:
                missing = [k for k, v in vals.items() if not v]
                print(f"Env var provider: {info['name']} ✗ (missing: {', '.join(missing)})")
        # Check CLI tools
        for cmd, label in {"ddgr": "DuckDuckGo", "googler": "Google", "s": "Surfraw"}.items():
            found = "✓" if shutil.which(cmd) else "✗"
            print(f"CLI tool: {label} ({cmd}) {found}")
        return

    if not args.input:
        parser.error("--input is required (or use --detect)")

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
        print(f"  [{i + 1}/{len(candidates)}] {name}: {status} (signals: {signals})", file=sys.stderr)

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
