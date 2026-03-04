---
name: namer
description: Use when naming products, companies, brands, or projects in any domain. Runs a structured naming pipeline using David Placek's Diamond Framework for strategy, then generates and evaluates candidates using naming best practices and web-search availability verification.
---

# Namer

Structured naming pipeline for any product, company, or brand. Uses the Diamond Framework (David Placek / Lexicon Branding) for strategy, then leverages LLM knowledge of languages, cultures, history, and sound symbolism to generate and evaluate candidates.

**Pipeline:** Discover → Seeds → Generate → Evaluate → Verify → Present

## Step 1: Discover

Ask these 5 questions **one at a time**, in order:

**1. What's the domain?** — "What industry or category is this?" (e.g. coffee shop, developer tool, law firm, band)

**2. What does winning look like?** — The vision. What is this, who's it for, what does success look like?
> *Swiffer: "Build a mop-like device people pay a premium for. Make cleaning floors something people want to do."*

**3. What do we have to win?** — The advantage. What assets or insights give you an edge?
> *Swiffer: "P&G's Pampers diaper tech — a lighter, more effective tool using absorbent pads instead of water."*

**4. What do we need to win?** — The gaps. What's missing? What must be overcome?
> *Swiffer: "Avoid being seen as just another mop. People hate mopping — they need to see this as entirely new."*

**5. What do we need to say?** — The message. What should the name communicate? What should it *feel* like?
> *Swiffer: "Logical: efficient, quick, easy. Emotional: fun, joyful, light. Should sound like a quick, satisfying action."*

See `references/diamond-framework.md` for the full framework with case studies.

## Step 2: Extract Seeds

From the user's answers, extract **30-50 seed words**:

**Literal seeds (~15-25):**
- ~3-5 from domain vocabulary
- ~3-5 from "winning" (vision/ambition)
- ~3-5 from "have to win" (differentiators)
- ~2-3 from "need to win" (aspirations)
- ~3-5 from "need to say" (feeling/tone)

**Evocative seeds (~15-25) — generate these yourself:**
- **Metaphorical** — words from adjacent domains (nature, mythology, architecture, music, materials). "If this product were a natural phenomenon, what would it be?"
- **Cross-cultural roots** — Latin, Greek, Sanskrit, Japanese, Arabic roots carrying the right connotation
- **Sound-designed** — invented syllable combos chosen for phonetic personality

**Sound profile** — from "need to say," define the target phonetic character:

| Sound | Effect | Example |
|-------|--------|---------|
| Plosives (b,d,k,t) | Decisive, strong, crisp | **B**lackBerry, Palen**t**ir |
| Fricatives (s,f,v) | Smooth, flowing, alive | **V**ercel, **S**onos |
| Nasals (m,n) | Warm, resonant, approachable | **N**avan |
| Front vowels (i,e) | Light, fast, precise | Sw**i**ffer, Dasan**i** |
| Back vowels (o,u) | Solid, strong, grounded | S**o**nos |
| Z | Electric, attention-drawing | A**z**ure |
| X | Innovative, edgy | Ne**x**t |

Present the seeds and sound profile to the user before proceeding.

## Step 3: Generate

Generate **150-200 name candidates** using these approaches:

1. **Cross-cultural roots** — Latin, Greek, Sanskrit, Japanese, Arabic, Celtic, Norse words/roots related to seeds. Remix, combine, truncate into name-length forms.
2. **Mythological & historical** — figures, places, concepts from world mythology and history that resonate with the brand strategy.
3. **Morpheme blends & portmanteaus** — combine syllable fragments from seeds into invented words. Target 5-9 characters.
4. **Compound multipliers** — two short words/fragments combined where 1+1=3 (creates richer associations than either alone). E.g. BlackBerry, Impossible.
5. **Sound-symbolic inventions** — coinages built from phonemes matching the target sound profile. Not derived from real words — pure phonetic design.
6. **Industry vocabulary remixes** — take domain-specific terms and transform them (truncation, blending, respelling, suffix swaps) into ownable forms.
7. **Unexpected assemblies** — familiar word parts combined in unfamiliar ways. Palindromes, letter pattern plays, respellings.

**Generation rules:**
- Target length: 4-10 characters (sweet spot: 5-8)
- Must be pronounceable in English
- Must be spellable from hearing it spoken
- No existing common English words (they're unownable in search/SEO)
- Separate creation from judgment — generate all candidates before evaluating any
- Aim for diversity across approaches, not all from one category

## Step 4: Evaluate

Filter to **top 20** candidates (ranked) using these criteria:

**Placek's Three Pillars:**
1. **Build for trust** — name inspires confidence. Familiar components assembled unexpectedly (Azure: "z" = signal, "sure" = confidence). Invented names that *feel* like real words.
2. **Communicate an original idea, never describe** — descriptive names are boring and have thousands of competitors. The name should make people say "they're not like the other guys."
3. **Be accessible** — easy to process, pronounce, spell, remember. The brain doesn't like complexity.

**Additional filters:**
- **Strategic alignment** — does it serve the Vision, Advantage, Gaps, and Message from discovery?
- **Sound symbolism match** — does the phonetic character match the target sound profile?
- **Compound multiplier** — if a compound, does 1+1=3? Does it create richer associations?
- **Competitor gut check** — "Your competitor just launched with this name. Reaction?" If you'd shrug, it's too weak.
- **Discomfort signal** — if the name feels safe and comfortable, it's probably wrong. Great names make you uncomfortable at first.

Keep positions 11-20 as a **bench** for replacement if top names get bumped in verification.

## Step 5: Verify Availability

Web-search each of the top 20 candidates. Two searches per name:

1. **Bare name:** `"[name]"` — is it already a brand/product?
2. **Domain-specific:** `"[name] [domain from Step 1]"` — is it taken in this space?

**Decision per name:**
- Nothing relevant → **CLEAR** — stays
- Hits exist but not in same space → **CAUTION** — stays, note the conflict
- Existing product/company in same space → **BUMP** — remove, pull next from bench
- Common dictionary word with millions of results → **BUMP** — unownable in SEO

Keep going until you have 10 CLEAR/CAUTION names.

**Optional extras** (suggest to user, don't assume):
- Domain availability (.com, .io)
- Trademark search (USPTO)
- Social handles (@name on major platforms)
- Software registries (npm, PyPI, crates.io, GitHub)

## Step 6: Present Top 10

For each finalist:
- **The name**
- **Why it works** — tied to Diamond Framework strategy
- **Sound notes** — phonetic character and symbolism
- **Cautions** — any availability concerns
- **Domain** — if checked

## Key Principles

- **Invented names take LESS money to build** than existing words. They signal "new and innovative" and generate more attention. Humans are drawn to the new.
- **Great names don't describe reality — they change it.** Swiffer made mopping feel like a quick, joyful action.
- **Quantity breeds quality** — but intentional quantity, not mechanical volume. Every candidate should have a reason to exist.
- **Compounds outperform single words** for memorability.
- **Don't brainstorm with 4+ people** — peer pressure kills originality.
- **The domain question changes everything** — "Atlas" is clear for a coffee shop, taken for software.
