# namer

An AI agent skill for structured product/brand naming. Generates 1000+ candidates using free APIs (zero LLM tokens), filters by namespace availability and web presence, then evaluates finalists against strategic criteria.

**Token-efficient by design** — the LLM only touches the final 20-50 survivors.

## How it works

1. **Define strategy** — Vision, Advantage, Gaps, Message
2. **Generate** — Datamuse API produces semantic neighbors, compounds, and blends (~1000-3000 candidates)
3. **Filter** — Automated namespace checks (npm, PyPI, crates.io, GitHub)
4. **Web search gate** — Brave Search checks for existing products (optional, needs API key)
5. **Evaluate** — LLM scores survivors on strategy alignment, sound symbolism, memorability
6. **Validate** — Trademark search, domain check, cross-language/culture review

## Requirements

- **Python 3.8+** (stdlib only — no pip installs needed)
- **Any web search API** (optional, for web search gate — auto-detected from environment)

## Install

This skill follows the [Agent Skills](https://agentskills.io) open standard. It works with any agent platform that supports it.

### Claude Code (VS Code / Desktop / CLI)

```bash
# Personal (available in all projects)
cp -r namer ~/.claude/skills/namer

# Or per-project
cp -r namer .claude/skills/namer
```

Claude auto-discovers it. Invoke with `/namer` or just ask Claude to help you name something.

### OpenClaw

```bash
cp -r namer ~/openclaw/skills/namer
```

### Generic (any agent)

Point your agent at `SKILL.md` as a prompt. The scripts are standalone Python — run them from any terminal.

## Web search providers

The web search gate auto-discovers your search setup in this order:

1. **Agent environment** — detects Claude Code, OpenClaw, Cursor, Windsurf, or VS Code
2. **MCP configs** — scans your MCP server configs for search tools (brave-search, web-search, tavily, serper, exa, etc.) and reuses their API keys
3. **Environment variables** — checks for direct API keys (see table)
4. **CLI tools** — checks PATH for `ddgr`, `googler`, etc. (noted but not yet used directly)
5. **Guided setup** — if nothing found, recommends Brave Search (free, 30 sec signup)

You can also run `python3 scripts/websearch_gate.py --detect` to see what's available without running anything.

| Provider | Env vars | Cost |
|----------|----------|------|
| Brave Search | `BRAVE_API_KEY` | Free: 2000/month |
| Serper (Google) | `SERPER_API_KEY` | $2.50/1000 queries |
| Google Custom Search | `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` | Free: 100/day |
| SearXNG | `SEARXNG_URL` | Free (self-hosted) |

No search API? The web gate step is optional — skip it and go straight from filtering to evaluation.

**If your agent has a built-in search tool** (web_search, MCP, etc.), the SKILL.md instructs the agent to use that directly instead of this script.

## Other API costs

| API | Cost | Key required? |
|-----|------|---------------|
| Datamuse (generation) | Free, no limits | No |
| npm / PyPI / crates.io (filtering) | Free, public APIs | No |
| GitHub Search (filtering) | Free, rate-limited | No |

## Usage (manual)

All output goes to `./namer-output/` by default. Override with `--out-dir` or `NAMER_OUTPUT_DIR` env var.

```bash
# Generate candidates → namer-output/candidates-raw.txt
python3 scripts/generate.py --seeds "memory,recall,mind,trace"

# Filter by namespace → namer-output/candidates-filtered.txt
python3 scripts/filter.py

# Web search gate (optional) → namer-output/candidates-gated.txt
python3 scripts/websearch_gate.py --input candidates-filtered.txt

# See what search providers are available
python3 scripts/websearch_gate.py --detect
```

Each script prints the full path of its output files when finished. Scripts also auto-resolve `--input` from the output dir, so you can chain them without full paths.

## Security

- **No secrets are prompted for, logged, or stored** — API keys come from your existing env vars or MCP configs
- **MCP config scanning is read-only** — the script reads your config files to find search tools you've already set up. Keys are only sent to their matching API endpoint (e.g. Brave key → Brave API). Nothing is printed, logged, or sent elsewhere.
- **`--detect` never prints keys** — only tool names and config file paths
- **Outbound network calls are limited to:** Datamuse (free, no auth), public package registries (npm/PyPI/crates.io/GitHub), and your chosen search API
- **The only data that leaves your machine** is search queries containing the candidate names

## License

MIT — see [LICENSE](LICENSE). Attribution appreciated.
