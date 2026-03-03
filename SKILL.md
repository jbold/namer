---
name: namer
description: Generate, filter, and evaluate product/brand names. Use when naming a product, project, company, or feature. Generates 1000+ candidates via Datamuse API (zero LLM tokens), filters by namespace availability (npm/PyPI/crates/GitHub), web search gates for existing products, then evaluates finalists against strategic criteria and sound symbolism. Token-efficient — LLM only touches the final 20-50 survivors.
---

# Namer

Structured naming pipeline. Volume generation (zero LLM tokens) → automated filtering → strategic evaluation.

## Process Overview

### Step 1: Define the Strategy
Before generating, fill out the four strategic quadrants with the user. See `references/diamond-framework.md` for the full framework. Four questions: What does winning look like? What do we have to win? What do we need to win? What do we need to say?

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

### Step 4: Web Search Gate (zero LLM tokens, requires Brave API key)
```bash
BRAVE_API_KEY=... python3 scripts/websearch_gate.py --input candidates-filtered.txt --out candidates-gated.txt
```
- Brave Search API checks each candidate for existing product/service presence
- Detects product signals: app, software, platform, pricing, sign up, .io, .ai, etc.
- Verdicts: CLEAR (no products) / CAUTION (weak signal) / BUMPED (existing product)
- **This is a hard gate**: if a web search returns existing products, the name is dead
- Outputs report with evidence (top results + signals detected)
- Brave free tier: 1 req/sec, use `--delay 1.1`

### Step 5: Evaluate (LLM, small batch only)
Load `references/diamond-framework.md`. Score the filtered survivors against:
1. Strategic quadrant alignment (from Step 1)
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
| Brave Search (web gate) | Free tier: 2000 queries/month | Yes (`BRAVE_API_KEY`) |

## Tips
- Append manual candidates (foreign words, historical references, invented words) to raw file before filtering
- Run multiple generation passes with different seed clusters (technical, emotional, metaphorical, physical)
- Compounds outperform single words for memorability
- Don't evaluate during generation — separate the phases strictly
