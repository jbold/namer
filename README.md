# namer

An AI agent skill for structured product/brand naming. Generates 1000+ candidates using free APIs (zero LLM tokens), filters by namespace availability and web presence, then evaluates finalists against strategic criteria.

**Token-efficient by design** — the LLM only touches the final 20-50 survivors.

## How it works

1. **Define strategy** — Four quadrants: Win, What we have to win, What we need to win, What we need to say
2. **Generate** — Datamuse API produces semantic neighbors, compounds, and blends (~1000-3000 candidates)
3. **Filter** — Automated namespace checks (npm, PyPI, crates.io, GitHub)
4. **Web search gate** — Brave Search checks for existing products (optional, needs API key)
5. **Evaluate** — LLM scores survivors on strategy alignment, sound symbolism, memorability
6. **Validate** — Trademark search, domain check, cross-language/culture review

## Requirements

- **Python 3.8+** (stdlib only — no pip installs needed)
- **Brave API key** (optional, for web search gate step — [free tier: 2000 queries/month](https://brave.com/search/api/))

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

## API costs

| API | Cost | Key required? |
|-----|------|---------------|
| Datamuse (generation) | Free, no limits | No |
| npm / PyPI / crates.io (filtering) | Free, public APIs | No |
| GitHub Search (filtering) | Free, rate-limited | No |
| Brave Search (web gate) | Free tier: 2000 queries/month | Yes (`BRAVE_API_KEY`) |

## Usage (manual)

```bash
# Generate candidates
python3 scripts/generate.py --seeds "memory,recall,mind,trace" --out candidates-raw.txt

# Filter by namespace availability
python3 scripts/filter.py --input candidates-raw.txt --out candidates-filtered.txt

# Web search gate (optional)
BRAVE_API_KEY=your_key python3 scripts/websearch_gate.py --input candidates-filtered.txt --out candidates-gated.txt
```

## License

MIT — see [LICENSE](LICENSE). Attribution appreciated.
