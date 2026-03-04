---
name: namer
description: Generate, filter, and evaluate product/brand names for any domain — tech, retail, food, services, anything. Uses David Placek's Diamond Framework for strategy, Datamuse API for volume generation (zero LLM tokens), mechanical shortlisting to ~100 survivors, then LLM picks top 10 and web-searches for conflicts.
---

# Namer

Structured naming pipeline. Works for any product, company, or brand — not just software.

**Pipeline:** Strategy → Generate (free) → Shortlist (free) → LLM Pick → Availability Check → Present

## Process Overview

### Step 1: Discovery (5 questions)

Ask these in order — domain first, then the four Diamond Framework questions:

**1. What's the domain?** — "What industry or category is this?" (e.g. coffee shop, developer tool, law firm, band)
> *Sets context for the other 4 questions. Gets prepended to availability searches later.*

**2. What does winning look like?** — The vision. What is this, who's it for, what does success look like?
> *Swiffer: "Build a mop-like device people pay a premium for. Make cleaning floors something people want to do."*

**3. What do we have to win?** — The advantage. What assets or insights give you an edge?
> *Swiffer: "P&G's Pampers diaper tech — a lighter, more effective tool using absorbent pads instead of water."*

**4. What do we need to win?** — The gaps. What's missing? What must be overcome?
> *Swiffer: "Avoid being seen as just another mop. People hate mopping — they need to see this as entirely new."*

**5. What do we need to say?** — The message. What should the name communicate? What should it *feel* like?
> *Swiffer: "Logical: efficient, quick, easy. Emotional: fun, joyful, light. Should sound like a quick, satisfying action."*

See `references/diamond-framework.md` for the full framework with examples and sound symbolism.

### Step 1b: Extract Seeds

From the user's answers, extract **30-50 seed words** across these categories:

**Literal seeds (~15-25):**
- ~3-5 from domain (the industry's vocabulary)
- ~3-5 from "winning" (vision/ambition words)
- ~3-5 from "have to win" (differentiator words)
- ~2-3 from "need to win" (aspiration/gap words)
- ~3-5 from "need to say" (feeling/tone words)

**Evocative seeds (~15-25) — YOU generate these based on the domain:**
- ~3-5 **metaphorical** — words from adjacent domains that FEEL like the brand but aren't literal. Draw from nature, mythology, architecture, music, materials, art movements. Ask: "If this product were a natural phenomenon / material / type of motion, what would it be?"
- ~3-5 **cross-cultural roots** — foreign language roots (Latin, Greek, Sanskrit, Japanese, Arabic, etc.) that carry the right connotation. Ask: "What words from other languages capture the essence?"
- ~2-3 **sound-designed** — invented syllable combos chosen for phonetic personality. Front vowels (i,e) = light/fast/precise. Back vowels (o,u) = solid/strong/warm. Plosives (b,d,k,t) = decisive. Fricatives (s,f,v) = smooth/flowing. Nasals (m,n) = warm/resonant.

**Blend parts (~20-30) — for morpheme blend generation:**
- ~10-15 **blend prefixes** (2-4 chars) — syllable fragments that sound right for the brand's tone. These replace mechanical `word[:4]` extraction. E.g. for a calm wellness brand: `sol, lun, ven, mer, syl, vel, ari, zen, cel, kai`
- ~10-15 **blend suffixes** (2-4 chars) — ending fragments that feel like natural word endings. E.g.: `ora, ine, ova, ium, ent, aro, elo, ith, ura, ane`

Example for Swiffer:
- Literal: `clean,sweep,wipe,swift,quick,light,easy,fun,snap,fresh,new,pad,glide,breeze,play,joy,smooth,action`
- Metaphorical: `zephyr,dart,flick,ripple,cascade`
- Cross-cultural: `vento,levis,rapido,souffle,karui`
- Sound-designed: `swif,fliro,breva`
- Blend prefixes: `swi,gli,bre,fli,sna,whi,qui,dri,cri,zep`
- Blend suffixes: `ift,ide,eeze,isk,irl,elo,ane,ist,ova,ina`

### Step 2: Generate (zero LLM tokens)

Tell the user: *"Generating ~1,000 candidates from your seeds (recommended minimum). More candidates = more hidden gems in the shortlist. Want more? I can go up to 10,000."*

```bash
python3 scripts/generate.py \
  --seeds "clean,sweep,swift,quick,light,easy,fun,snap,fresh,glide,breeze,play,joy,zephyr,dart,flick,ripple,cascade,vento,levis,rapido,souffle,karui,swif,fliro,breva" \
  --blend-prefixes "swi,gli,bre,fli,sna,whi,qui,dri,cri,zep" \
  --blend-suffixes "ift,ide,eeze,isk,irl,elo,ane,ist,ova,ina"
```
- Datamuse API: semantic neighbors, sound-alikes, triggered-by associations
- Compound generation: prefix+base, base+suffix, base+base
- Morpheme blends: uses LLM-generated blend prefixes/suffixes (falls back to `word[:4]`/`word[-4:]` extraction if not provided)
- `--limit N` caps output to top N candidates (by alphabetical; use shortlist for quality ranking)
- Output: `namer-output/candidates-raw.txt`

### Step 3: Shortlist (zero LLM tokens)

Mechanically filter 10K → ~100 candidates so the LLM never sees the full list.

```bash
python3 scripts/shortlist.py
```
- Scores by: pronounceability, ease of spelling, length sweetspot (5-9 chars), letter variety, strong starts, sound symbolism (phonetic consistency + pharma suffix penalty), prefix diversity (penalizes >10 candidates sharing a 4-char prefix)
- `--top N` controls how many survive (default: 100, per Lexicon's "shortlist to 50-100" guideline)
- `--pre-filter "key,words"` to only keep candidates containing specific substrings
- Output: `namer-output/candidates-shortlist.txt` (one per line, scored)

### Step 4: LLM Pick (this is you)

Read `namer-output/candidates-shortlist.txt` (~100 names). Using the strategy from Step 1, rank them and pick your **top 10** by:

1. Strategic alignment (Vision, Advantage, Gaps, Message)
2. Sound symbolism (see `references/diamond-framework.md`)
3. Compound multiplier effect (1+1=3?)
4. Gut check: "Your competitor just launched with this name — reaction?"
5. Discomfort signal: if it feels safe, it's probably wrong

Keep positions 11-20 as a **bench** — you'll pull from these if any top 10 get bumped.

**Token budget:** ~100 names × ~8 chars = ~800 tokens input. Cheap.

### Step 5: Availability Check (you + web search)

Check your top 10 in order. Two searches per name:

1. **Bare name search:** `"[name]"` — is the word already a brand/product anywhere?
2. **Domain search:** `"[name] [domain from Step 1]"` — is it taken in this specific space?

Example: for "qubitly" in quantum computing:
- Search `"qubitly"` → nothing → good
- Search `"qubitly quantum computing"` → nothing → ✅ CLEAR

**Decision per name:**
- Nothing relevant in either search → ✅ CLEAR — stays on the list
- Bare name has some hits but not in same space → ⚠️ CAUTION — stays, note it
- Existing product/company in same space → ❌ BUMP — remove it, pull the next name from your bench (position 11, then 12, etc.) and check that one too
- Bare name is a common dictionary word with millions of results → ❌ BUMP — unownable in search/SEO

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

## Token & API Costs

**Scripts (zero LLM tokens):**
- `generate.py` — Datamuse API, free, no key, no limits
- `shortlist.py` — pure local Python, no API calls at all
- `filter.py` — npm/PyPI/crates/GitHub, free (rate-limited), no key
- `websearch_gate.py` — your search API (Brave free tier: 2000/month)

**Agent steps (where tokens are spent):**
- Discovery (5 questions + reading answers): ~500 tokens
- Seed extraction from answers: ~300 tokens
- LLM Pick (reading ~100 shortlisted names + ranking): ~1,300 tokens
- Availability (web search × 10-15 names): ~2,000-3,000 tokens
- Present top 10 with rationale: ~1,000 tokens

**Total: ~5,000-6,000 tokens for the full pipeline.** The expensive work (generating 8K+ candidates, scoring, registry checks) is all free.

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
