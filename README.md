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

The web search gate auto-discovers your search provider from environment variables. Set any one:

| Provider | Env vars | Cost |
|----------|----------|------|
| Brave Search | `BRAVE_API_KEY` | Free: 2000/month |
| Serper (Google) | `SERPER_API_KEY` | $2.50/1000 queries |
| Google Custom Search | `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` | Free: 100/day |
| SearXNG | `SEARXNG_URL` | Free (self-hosted) |

No search API? The web gate step is optional — skip it and go straight from filtering to evaluation.

## Other API costs

| API | Cost | Key required? |
|-----|------|---------------|
| Datamuse (generation) | Free, no limits | No |
| npm / PyPI / crates.io (filtering) | Free, public APIs | No |
| GitHub Search (filtering) | Free, rate-limited | No |

## Usage (manual)

```bash
# Generate candidates
python3 scripts/generate.py --seeds "memory,recall,mind,trace" --out candidates-raw.txt

# Filter by namespace availability
python3 scripts/filter.py --input candidates-raw.txt --out candidates-filtered.txt

# Web search gate (optional — uses whatever search API you have configured)
python3 scripts/websearch_gate.py --input candidates-filtered.txt --out candidates-gated.txt
```

## License

MIT — see [LICENSE](LICENSE). Attribution appreciated.
