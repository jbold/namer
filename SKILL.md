---
name: namer
description: Generate, filter, and evaluate product/brand names for any domain — tech, retail, food, services, anything. Generates 1000+ candidates via Datamuse API (zero LLM tokens), mechanically shortlists by pronounceability, then the LLM picks top names and web-searches them for conflicts. Token-efficient — LLM only sees ~200 pre-filtered survivors.
---

# Namer

Structured naming pipeline. Works for any product, company, or brand — not just software.

**Pipeline:** Strategy → Generate (free) → Shortlist (free) → LLM Pick → Availability Check → Present

## Process Overview

### Step 1: Discovery (5 questions)

Ask these in plain language, adapted to the user's product:

1. **What does winning look like?** — Describe the product, who it's for, and what success looks like.
2. **What do we have to win?** — What's the advantage? What makes this different from the competition?
3. **What do we need to win?** — What's missing? What gaps need to be filled? (stage, users, trust, resources)
4. **What do we need to say?** — What should the name communicate? What should it *feel* like?
5. **What's the domain?** — What industry or category? (e.g. "coffee shop", "npm package", "AI tool", "law firm")

The domain answer is critical — it determines what you search for in the availability check. A name that's clean for a coffee shop might be taken for a SaaS tool.

See `references/diamond-framework.md` for the full strategic framework.

### Step 2: Generate (zero LLM tokens)

Tell the user: *"Default generates ~10,000 candidates from your seeds. That's the full creative blast — more candidates means more hidden gems. The expensive part is later steps, not generation. Want the full set, or should I cap it? (500 is plenty for a first pass.)"*

```bash
python3 scripts/generate.py --seeds "your,seed,words,here"
```
- Datamuse API: semantic neighbors, sound-alikes, triggered-by associations
- Compound generation: prefix+base, base+suffix, base+base
- Morpheme blends: portmanteau candidates
- `--limit N` caps output to top N candidates (by alphabetical; use shortlist for quality ranking)
- Output: `namer-output/candidates-raw.txt`

Tip: Add manual candidates (foreign words, metaphors, invented words) by appending to the raw file before shortlisting.

### Step 3: Shortlist (zero LLM tokens)

Mechanically filter 10K → ~200 candidates so the LLM never sees the full list.

```bash
python3 scripts/shortlist.py
```
- Scores by: pronounceability, ease of spelling (penalizes ambiguous phonemes like "ph"/"gh"/"ck"), length sweetspot (5-9 chars), letter variety, strong starts
- `--top N` controls how many survive (default: 200)
- `--pre-filter "key,words"` to only keep candidates containing specific substrings
- Output: `namer-output/candidates-shortlist.txt` (one per line, scored)

### Step 4: LLM Pick (this is you)

Read `namer-output/candidates-shortlist.txt` (~200 names). Using the strategy from Step 1, rank them and pick your **top 10** by:

1. Strategic alignment (Vision, Advantage, Gaps, Message)
2. Sound symbolism (see `references/diamond-framework.md`)
3. Compound multiplier effect (1+1=3?)
4. Gut check: "Your competitor just launched with this name — reaction?"
5. Discomfort signal: if it feels safe, it's probably wrong

Keep positions 11-20 as a **bench** — you'll pull from these if any top 10 get bumped.

**Token budget:** ~200 names × ~8 chars = ~1,600 tokens input. Cheap.

### Step 5: Availability Check (you + web search)

Check your top 10 in order. For each, web search: `"[name] [domain from Step 1]"`

Example: if domain is "quantum computing demo" and name is "qubitly", search `"qubitly quantum computing"`.

**Decision per name:**
- Nothing relevant in results → ✅ CLEAR — stays on the list
- Weak match (blog post, unrelated product) → ⚠️ CAUTION — stays, note it
- Existing product/company in same space → ❌ BUMP — remove it, pull the next name from your bench (position 11, then 12, etc.) and check that one too

Keep going until you have 10 clear/caution names.

**Optional extras** (suggest to user, don't assume):
- Domain availability: check .com/.io for the finalists
- Trademark: search USPTO (tmsearch.uspto.gov) for the top 3
- Social handles: check @name on X, Instagram, GitHub
- **Software projects specifically:** run `python3 scripts/filter.py` to check npm/PyPI/crates.io/GitHub

### Step 6: Present Top 10

For each finalist:
- The name
- Why it works (tied to strategy)
- Sound symbolism notes
- Any cautions from the availability check
- Suggested domain if checked

## API Costs

| Step | API | Cost | Key Required? |
|------|-----|------|---------------|
| Generate | Datamuse | Free, no limits | No |
| Shortlist | None (local) | Free | No |
| LLM Pick | Your model | ~1,600 tokens in | N/A |
| Availability | Your search tool | ~20 queries | Depends |
| Filter (optional) | npm/PyPI/crates/GitHub | Free, rate-limited | No |

## Output

All scripts write to `./namer-output/` by default. Override with `--out-dir` or `NAMER_OUTPUT_DIR` env var. Each script prints output file paths when finished.

Pipeline files:
- `candidates-raw.txt` — Step 2 (all generated candidates)
- `candidates-shortlist.txt` — Step 3 (mechanically scored survivors)
- `candidates-filtered.txt` — Optional (npm/PyPI/crates/GitHub results, software only)

Scripts auto-resolve `--input` from the output dir, so you can chain without full paths.

## Tips
- Run multiple generation passes with different seed clusters (technical, emotional, metaphorical, physical)
- Compounds outperform single words for memorability
- Don't evaluate during generation — separate the phases strictly
- The domain question changes everything — "atlas" is clear for a coffee shop, taken for software
