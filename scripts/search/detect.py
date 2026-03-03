"""
Agent environment detection — find MCP search tools in known agent configs.
Read-only: never logs, modifies, or exfiltrates keys.
"""

import json
import os

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
    "brave-search", "brave_search", "brave_web_search",
    "web-search", "web_search",
    "google-search", "google_search",
    "serper", "serper-search",
    "tavily", "tavily-search", "tavily_search",
    "exa", "exa-search", "exa_search",
    "searxng", "searxng-search",
    "bing-search", "bing_search",
}


def _expand_path(p: str) -> str:
    return os.path.expanduser(os.path.expandvars(p))


def detect_environment() -> dict:
    """Detect agent environment and scan for MCP search tools.
    Returns {env_name, env_label, mcp_search_tools: [{name, config_path, server_config}]}
    """
    result = {"env_name": None, "env_label": "unknown", "mcp_search_tools": []}

    for env_name, info in AGENT_ENVIRONMENTS.items():
        if not any(os.path.exists(_expand_path(p)) for p in info["indicators"]):
            continue

        result["env_name"] = env_name
        result["env_label"] = info["name"]
        result["mcp_search_tools"] = _scan_mcp_configs(info["mcp_configs"])
        break  # use first matching environment

    return result


def _scan_mcp_configs(config_paths: list[str]) -> list[dict]:
    """Scan MCP config files for search-capable servers."""
    tools = []
    for config_path in config_paths:
        full_path = _expand_path(config_path)
        if not os.path.isfile(full_path):
            continue
        try:
            with open(full_path) as f:
                config = json.load(f)
            servers = _extract_servers(config)
            for server_name, server_config in servers.items():
                if _is_search_server(server_name, server_config):
                    tools.append({
                        "name": server_name,
                        "config_path": full_path,
                        "server_config": server_config,
                    })
        except (json.JSONDecodeError, OSError, KeyError):
            continue
    return tools


def _extract_servers(config: dict) -> dict:
    """Extract server dict from various MCP config formats."""
    if "mcpServers" in config:
        return config["mcpServers"]
    if "mcp" in config and "servers" in config.get("mcp", {}):
        return config["mcp"]["servers"]
    if "servers" in config:
        return config["servers"]
    return {}


def _is_search_server(name: str, config: dict) -> bool:
    """Check if a server name or its command/args indicate search capability."""
    normalized = name.lower().replace("-", "_").replace(" ", "_")
    if normalized in {t.replace("-", "_") for t in SEARCH_MCP_TOOLS}:
        return True
    # Check command/args for search-related keywords
    cmd = config.get("command", "")
    args = " ".join(config.get("args", []))
    combined = f"{cmd} {args}".lower()
    return any(kw in combined for kw in [
        "brave", "serper", "tavily", "exa", "searx", "web-search", "web_search"
    ])
