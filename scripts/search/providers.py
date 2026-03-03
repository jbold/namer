"""
Search provider implementations and auto-discovery.
Each provider function takes a query and credentials, returns results.
"""

import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from search.detect import detect_environment

PROVIDERS = {
    "brave": {"env": ["BRAVE_API_KEY"], "name": "Brave Search"},
    "serper": {"env": ["SERPER_API_KEY"], "name": "Serper (Google)"},
    "google": {"env": ["GOOGLE_API_KEY", "GOOGLE_CSE_ID"], "name": "Google Custom Search"},
    "searxng": {"env": ["SEARXNG_URL"], "name": "SearXNG"},
}


# --- Individual provider implementations ---

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


# --- Routing ---

def do_search(provider: str, env_vals: dict, query: str) -> list[dict]:
    """Route search to the correct provider implementation."""
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


# --- Discovery ---

def discover_provider(verbose: bool = True) -> tuple[str, dict]:
    """Auto-discover search provider from MCP configs, env vars, and CLI tools.
    Returns (provider_name, {env_var: value}) or exits with guidance.
    """
    env_info = detect_environment()

    if verbose and env_info["env_name"]:
        print(f"Detected environment: {env_info['env_label']}", file=sys.stderr)

    # 1. Check MCP search tools for embedded API keys
    provider_from_mcp = _check_mcp_keys(env_info, verbose)
    if provider_from_mcp:
        return provider_from_mcp

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

    # 3. Check CLI tools (informational only — not yet usable)
    _report_cli_tools(verbose)

    # 4. Nothing found — print guidance and exit
    _print_setup_guidance(env_info)
    sys.exit(1)


def _check_mcp_keys(env_info: dict, verbose: bool) -> tuple[str, dict] | None:
    """Try to extract API keys from MCP server configs."""
    if not env_info["mcp_search_tools"]:
        return None

    tool_names = [t["name"] for t in env_info["mcp_search_tools"]]
    if verbose:
        print(f"Found MCP search tools: {', '.join(tool_names)}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Your agent has search via MCP. You have two options:", file=sys.stderr)
        print("  1. Let your agent use its MCP search tool directly (recommended)", file=sys.stderr)
        print("     → Skip this script, have the agent search each candidate inline", file=sys.stderr)
        print("  2. Set the matching API key as an env var for this script", file=sys.stderr)
        print("", file=sys.stderr)

    for tool in env_info["mcp_search_tools"]:
        server_env = tool.get("server_config", {}).get("env", {})
        for env_key, env_val in server_env.items():
            # Resolve env var references like ${BRAVE_API_KEY}
            if env_val.startswith("${") and env_val.endswith("}"):
                actual_var = env_val[2:-1]
                actual_val = os.environ.get(actual_var)
                if actual_val:
                    env_val = actual_val

            if env_key == "BRAVE_API_KEY" and env_val:
                return "brave", {"BRAVE_API_KEY": env_val}
            elif env_key in ("SERPER_API_KEY", "SERPER_KEY") and env_val:
                return "serper", {"SERPER_API_KEY": env_val}
            elif env_key == "TAVILY_API_KEY" and env_val and verbose:
                print("  Found Tavily key in MCP config but Tavily provider not yet implemented.", file=sys.stderr)
                print("  Consider setting BRAVE_API_KEY or SERPER_API_KEY instead.", file=sys.stderr)

    return None


def _report_cli_tools(verbose: bool) -> None:
    """Report any CLI search tools found on PATH."""
    if not verbose:
        return
    cli_tools = {"ddgr": "DuckDuckGo (ddgr)", "googler": "Google (googler)", "s": "Surfraw (s)"}
    found = [label for cmd, label in cli_tools.items() if shutil.which(cmd)]
    if found:
        print(f"Found CLI search tools: {', '.join(found)}", file=sys.stderr)
        print("  These can't be used directly by this script yet.", file=sys.stderr)
        print("  Set a search API key instead (see below).", file=sys.stderr)
        print("", file=sys.stderr)


def _print_setup_guidance(env_info: dict) -> None:
    """Print guidance for setting up a search provider."""
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
