# Namer Skill Refactor — LLM-Native Architecture

**Date:** 2026-03-03
**Status:** Approved

## Problem

The current namer skill has 11 Python scripts (generate.py, shortlist.py, filter.py, websearch_gate.py, + 7 utilities) that:
1. Create maintenance burden across environments
2. Underuse the LLM's knowledge of languages, cultures, history, sound symbolism
3. Reduce portability — requires Python 3, network for Datamuse, specific directory structure
4. The Datamuse API + mechanical scoring produces volume over quality

## Decision

Refactor to a pure LLM skill: SKILL.md + one reference doc. No scripts, no dependencies.

## Architecture

### File Structure (before → after)

**Before:** SKILL.md + 11 .py scripts + tests/ + references/
**After:**
```
namer/
├── SKILL.md
└── references/
    └── diamond-framework.md
```

### Pipeline (6 steps, all LLM-driven)

| Step | What | Method |
|------|------|--------|
| 1. Discover | Diamond Framework interview | 5 questions, one at a time |
| 2. Seeds | Extract seed vocabulary + sound profile | LLM extracts from answers |
| 3. Generate | 150-200 candidates | LLM draws on languages, history, mythology, sound symbolism, morpheme blending |
| 4. Evaluate | Filter to top 20 | Placek's three pillars + discomfort signal + competitor gut check |
| 5. Verify | Web search availability | 2 searches per name, bench mechanism |
| 6. Present | Top 10 with rationale | Strategy-tied explanation |

### What's Kept
- Diamond Framework content (strategy questions + examples)
- Sound symbolism reference (phoneme → effect table)
- Bench mechanism (positions 11-20 as replacements)
- Availability check process (web search)
- Key principles (invented > descriptive, discomfort signal, competitor gut check)

### What's Cut
- All Python scripts (generate.py, shortlist.py, filter.py, websearch_gate.py)
- All utility modules (output.py, fileio.py, progress.py, search/)
- All tests (test_generate.py, test_shortlist.py, etc.)
- Datamuse API dependency
- Output directory management
- namer-output/ directory convention

### Token Budget

| Step | Tokens |
|------|--------|
| Discovery | ~500 |
| Seed extraction | ~300 |
| Generation | ~2,000 |
| Evaluation | ~1,500 |
| Availability | ~3,000 |
| Presentation | ~1,000 |
| **Total** | **~8,300** |

~3K more than current, but zero dependencies and higher quality candidates.

### Key Trade-off

Volume drops (8,000 → 200), quality rises. Every candidate has a reason to exist because the LLM generates intentionally from its knowledge of linguistics, cultural references, and naming history — rather than mechanical Cartesian products of morphemes.

## Portability

No tool-specific syntax. Any LLM agent that can read markdown and perform web searches can run this skill. No Claude Code assumptions.
