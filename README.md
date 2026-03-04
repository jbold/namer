# namer

An AI agent skill for structured product/brand naming — for anything, not just software. Coffee shops, SaaS tools, bands, law firms, whatever needs a name.

Uses David Placek's Diamond Framework (Lexicon Branding — Swiffer, Sonos, Azure, Vercel, Pentium, BlackBerry, Impossible Foods) for strategy, then leverages the LLM's knowledge of languages, cultures, history, and sound symbolism to generate and evaluate candidates.

**Zero dependencies** — just markdown. Works with any LLM agent that can read skill files and perform web searches.

## How it works

1. **Discover** — 5 Diamond Framework questions (domain first, then vision/advantage/gaps/message)
2. **Seeds** — extract 30-50 seed words from answers (literal + evocative), define a target sound profile using sound symbolism research
3. **Generate** — 150-200 candidates using cross-cultural roots, mythology, morpheme blends, compound multipliers, sound-symbolic inventions, and industry vocabulary remixes — guided by a curated morpheme database
4. **Evaluate** — filter to top 20 using Placek's three pillars (trust, originality, accessibility) + sound symbolism alignment + competitor gut check + discomfort signal
5. **Verify** — web search each candidate for existing products (CLEAR / CAUTION / BUMP), bench mechanism pulls replacements from positions 11-20
6. **Present** — top 10 with strategy-tied rationale, sound notes, and availability status

## Reference files

The skill includes curated reference data that gets loaded into context during naming runs:

- **`references/diamond-framework.md`** — Placek's Diamond Framework with Swiffer and Windsurf case studies
- **`references/sound-symbolism.md`** — letter-to-psychology mappings, phoneme classes, vowel symbolism, compound effects, and the bouba/kiki principle
- **`references/morphemes.md`** — ~800 productive morphemes across 16 semantic domains (motion, light, strength, mind, nature, etc.) plus Latin, Greek, Sanskrit, Japanese, and Arabic roots

These aren't just documentation — they're working knowledge that shapes generation quality. The sound symbolism reference ensures consistent phonetic targeting, and the morpheme database surfaces cross-cultural roots the LLM might not reach for unprompted.

## Install

This skill follows the [Agent Skills](https://agentskills.io) open standard.

**Claude Code — personal** (available in all projects):
```bash
git clone https://github.com/jbold/namer.git ~/.claude/skills/namer
```

**Claude Code — per-project only:**
```bash
git clone https://github.com/jbold/namer.git .claude/skills/namer
```

**OpenClaw:**
```bash
git clone https://github.com/jbold/namer.git ~/openclaw/skills/namer
```

Or just point any agent at `SKILL.md` — it's self-contained markdown with no external dependencies.

## File structure

```
namer/
├── SKILL.md                           # Complete pipeline instructions
├── README.md                          # This file
├── LICENSE                            # MIT
└── references/
    ├── diamond-framework.md           # Placek's framework + case studies
    ├── sound-symbolism.md             # Phoneme → psychology mappings
    └── morphemes.md                   # ~800 morphemes by semantic domain
```

## License

MIT — see [LICENSE](LICENSE).
