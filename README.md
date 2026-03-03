# namer

An AI agent skill for structured product/brand naming — for anything, not just software. Coffee shops, SaaS tools, bands, law firms, whatever needs a name.

Generates 1000+ candidates using free APIs (zero LLM tokens), mechanically shortlists by quality, then the LLM picks the best and checks them against real-world conflicts.

**Token-efficient by design** — the LLM only sees ~100 pre-filtered survivors.

## How it works

Uses David Placek's Diamond Framework (Lexicon Branding — Swiffer, Sonos, Azure, Vercel, Pentium).

1. **Domain** — What industry/category? (sets context for everything)
2. **Diamond questions** — What does winning look like? What do we have to win? What do we need to win? What do we need to say?
3. **Extract seeds** — LLM pulls 15-25 seed words from the answers
4. **Generate** — Datamuse API blasts seeds into ~1,000–10,000 candidates (zero tokens)
5. **Shortlist** — Mechanical scoring (pronounceability, spellability, length, letter patterns) cuts to ~100
6. **LLM picks top 10** — Reads shortlist, selects based on strategy, keeps 11-20 as bench
7. **Availability check** — Web search `"[name] [industry]"`, bump conflicts, pull from bench
8. **Present top 10** — With rationale and evidence

## Requirements

- **Python 3.8+** (stdlib only — no pip installs needed)
- **Any web search** (agent's built-in search, or API key for the standalone script)

## Install

This skill follows the [Agent Skills](https://agentskills.io) open standard.

### Claude Code (VS Code / Desktop / CLI)

```bash
# Personal (available in all projects)
cp -r namer ~/.claude/skills/namer

# Or per-project
cp -r namer .claude/skills/namer
```

### OpenClaw

```bash
cp -r namer ~/openclaw/skills/namer
```

### Generic (any agent)

Point your agent at `SKILL.md` as a prompt. The scripts are standalone Python.

## Usage

All output goes to `./namer-output/` by default. Override with `--out-dir` or `NAMER_OUTPUT_DIR` env var.

```bash
# Generate candidates → namer-output/candidates-raw.txt
python3 scripts/generate.py --seeds "spark,drift,pulse"

# Shortlist by quality → namer-output/candidates-shortlist.txt
python3 scripts/shortlist.py                     # default: top 100
python3 scripts/shortlist.py --top 200           # keep more
python3 scripts/shortlist.py --pre-filter "flux"  # only score names containing "flux"

# (Optional) Check software namespaces → namer-output/candidates-filtered.txt
python3 scripts/filter.py

# (Optional) Standalone web search gate → namer-output/candidates-gated.txt
python3 scripts/websearch_gate.py --input candidates-shortlist.txt

# See what search providers are available
python3 scripts/websearch_gate.py --detect
```

Each script prints output file paths when finished and auto-resolves `--input` from the output dir.

## Pipeline scripts

| Script | Purpose | API calls | LLM tokens |
|--------|---------|-----------|------------|
| `generate.py` | Volume candidate generation | Datamuse (free) | 0 |
| `shortlist.py` | Mechanical quality scoring | None | 0 |
| `filter.py` | Software namespace checks | npm/PyPI/crates/GitHub | 0 |
| `websearch_gate.py` | Web presence check | Your search API | 0 |

`filter.py` and `websearch_gate.py` are optional. The default flow is: generate → shortlist → LLM picks → LLM web-searches.

## Web search providers

The web search gate auto-discovers your setup:

1. **Agent environment** — detects Claude Code, OpenClaw, Cursor, Windsurf, VS Code
2. **MCP configs** — scans for search tools (brave-search, tavily, serper, exa, etc.)
3. **Environment variables** — direct API keys
4. **CLI tools** — ddgr, googler
5. **Guided setup** — recommends Brave Search (free, 30 sec signup)

| Provider | Env vars | Cost |
|----------|----------|------|
| Brave Search | `BRAVE_API_KEY` | Free: 2000/month |
| Serper (Google) | `SERPER_API_KEY` | $2.50/1000 queries |
| Google Custom Search | `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` | Free: 100/day |
| SearXNG | `SEARXNG_URL` | Free (self-hosted) |

**If your agent has a built-in search tool**, the SKILL.md tells it to use that directly instead of the script.

## Security

- No secrets are prompted for, logged, or stored
- MCP config scanning is read-only — keys only sent to their matching API
- `--detect` never prints keys
- Outbound calls limited to: Datamuse, package registries, your chosen search API

## License

MIT — see [LICENSE](LICENSE).
