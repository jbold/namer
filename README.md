# namer

An AI agent skill for structured product/brand naming — for anything, not just software. Coffee shops, SaaS tools, bands, law firms, whatever needs a name.

Uses David Placek's Diamond Framework (Lexicon Branding — Swiffer, Sonos, Azure, Vercel, Pentium, BlackBerry, Impossible Foods) for strategy, then leverages the LLM's knowledge of languages, cultures, history, and sound symbolism to generate and evaluate candidates.

**Zero dependencies** — just markdown. Works with any LLM agent that can read skill files and perform web searches.

## How it works

1. **Discover** — 5 Diamond Framework questions (domain first, then vision/advantage/gaps/message)
2. **Seeds** — extract 30-50 seed words from answers (literal + evocative: metaphorical, cross-cultural roots, sound-designed)
3. **Generate** — LLM creates 150-200 candidates using cross-cultural roots, mythology, morpheme blends, compound multipliers, sound-symbolic inventions, and industry vocabulary remixes
4. **Evaluate** — filter to top 20 using Placek's three pillars (trust, originality, accessibility) + competitor gut check + discomfort signal
5. **Verify** — web search each candidate for conflicts (CLEAR / CAUTION / BUMP), bench mechanism for replacements
6. **Present** — top 10 with strategy-tied rationale

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
├── SKILL.md                        # Complete pipeline instructions
├── README.md                       # This file
├── LICENSE                         # MIT
└── references/
    └── diamond-framework.md        # Placek's framework with case studies
```

## License

MIT — see [LICENSE](LICENSE).
