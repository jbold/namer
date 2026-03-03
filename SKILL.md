---
name: namer
description: Generate, filter, and evaluate product/brand names. Use when naming a product, project, company, or feature. Generates 1000+ candidates via Datamuse API (zero LLM tokens), filters by namespace availability (npm/PyPI/crates/GitHub), web search gates for existing products, then evaluates finalists against strategic criteria and sound symbolism. Token-efficient — LLM only touches the final 20-50 survivors.
---

# Namer

Structured naming pipeline. Volume generation (zero LLM tokens) → automated filtering → strategic evaluation.

## Process Overview

### Step 1: Define the Strategy
Before generating, work through strategic discovery with the user. See `references/diamond-framework.md` for the full framework. Four questions:
- **Vision** — What does success look like? How should the market perceive us?
- **Advantage** — What sets us apart? What's our moat?
- **Gaps** — What capabilities, trust signals, or adoption requirements are we missing?
- **Message** — What feeling or experience should the name evoke?

### Step 2: Generate (zero LLM tokens)
```bash
python3 scripts/generate.py --seeds "memory,recall,mind,trace" --out candidates-raw.txt
```
- Datamuse API: semantic neighbors, sound-alikes, triggered-by associations
- Compound generation: prefix+base, base+suffix, base+base
- Morpheme blends: portmanteau candidates
- Custom seeds: pass `--seeds` with domain-specific terms
- Output: ~1000-3000 candidates in a flat text file

Add manual candidates (foreign words, metaphors, invented words) by appending to the raw file before filtering.

### Step 3: Filter by Namespace (zero LLM tokens)
```bash
python3 scripts/filter.py --input candidates-raw.txt --out candidates-filtered.txt
```
- Checks: npm, PyPI, crates.io, GitHub repo count
- Verdicts: CLEAN / LIKELY_OK / CHECK / TAKEN
- Use `--pre-filter "mem,rec,mind"` to only check candidates containing specific substrings (saves API calls on large sets)
- Use `--limit 100` for testing
- Full results in TSV for review

### Step 4: Web Search Gate (zero LLM tokens)

**If you have a built-in search tool** (web_search, MCP search server, browser search, etc.), use it directly. For each candidate, search the name and check for these product signals:
- Keywords: app, software, platform, saas, tool, service, download, pricing, sign up, login, api, sdk, startup, inc, ltd, gmbh, solutions, technologies, product, features, demo, get started, free trial, enterprise, cloud
- Domain signals: .io, .ai, .app
- Verdict: 0-1 signals = CLEAR, 1 signal = CAUTION, 2+ signals = BUMPED (existing product, name is dead)

**If no search tool is available**, use the standalone script:
```bash
python3 scripts/websearch_gate.py --input candidates-filtered.txt --out candidates-gated.txt
```
- Auto-discovers environment (Claude Code, OpenClaw, Cursor, etc.) and available search providers
- Checks MCP configs, env vars, and CLI tools in priority order
- If nothing found, prompts user to configure a search provider (Brave recommended as default)
- Outputs report with evidence (top results + signals detected)
- Rate limit: use `--delay 1.1` for free tiers

### Step 5: Evaluate (LLM, small batch only)
Load `references/diamond-framework.md`. Score the filtered survivors against:
1. Strategic alignment (Vision, Advantage, Gaps, Message from Step 1)
2. Sound symbolism (V=vibrant, B=reliable, Z=attention, X=innovation)
3. Compound multiplier effect (1+1=3?)
4. Competitor test: "Your competitor just launched with this name — reaction?"
5. Discomfort signal: if it feels safe, it's probably wrong
6. Pronounceability, memorability, distinctiveness

Present top 10-20 with rationale. Use polarization as a positive signal.

### Step 6: Validate
- Web search for trademark conflicts in target classes
- Domain availability (but don't let it drive the decision)
- Cross-language/culture check (does it mean something bad somewhere?)

## API Costs

| API | Cost | Key Required? |
|-----|------|---------------|
| Datamuse (generation) | Free, no limits | No |
| npm / PyPI / crates.io (filtering) | Free, public APIs | No |
| GitHub Search (filtering) | Free, rate-limited | No |
| **Web search gate** (any one of:) | | |
| — Brave Search | Free tier: 2000/month | `BRAVE_API_KEY` |
| — Serper (Google) | $2.50/1000 queries | `SERPER_API_KEY` |
| — Google Custom Search | Free tier: 100/day | `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` |
| — SearXNG | Free (self-hosted) | `SEARXNG_URL` |

## Tips
- Append manual candidates (foreign words, historical references, invented words) to raw file before filtering
- Run multiple generation passes with different seed clusters (technical, emotional, metaphorical, physical)
- Compounds outperform single words for memorability
- Don't evaluate during generation — separate the phases strictly
