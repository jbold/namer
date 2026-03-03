#!/usr/bin/env python3
"""
Name shortlisting pipeline — Step 3: Mechanical quality scoring.
Zero LLM tokens. Zero API calls. Pure heuristics.

Scores candidates by pronounceability, length sweetspot, letter patterns,
and uniqueness. Reduces ~10,000 candidates to ~200 high-quality survivors
so the LLM never has to read the full list.

Usage:
    python3 shortlist.py [--input candidates-raw.txt] [--top 200]
    python3 shortlist.py --pre-filter "quant,flux,ion"
"""

import argparse
import os
import sys

VOWELS = set("aeiouy")
CONSONANTS = set("bcdfghjklmnpqrstvwxz")

# Common English words that make bad product names (too generic)
COMMON_WORDS = {
    "about",
    "after",
    "again",
    "also",
    "always",
    "another",
    "back",
    "because",
    "been",
    "before",
    "being",
    "between",
    "both",
    "came",
    "come",
    "could",
    "does",
    "done",
    "down",
    "each",
    "even",
    "every",
    "first",
    "from",
    "give",
    "going",
    "good",
    "great",
    "have",
    "here",
    "high",
    "home",
    "into",
    "just",
    "keep",
    "know",
    "last",
    "left",
    "life",
    "like",
    "line",
    "little",
    "long",
    "look",
    "made",
    "make",
    "many",
    "might",
    "more",
    "most",
    "much",
    "must",
    "name",
    "never",
    "next",
    "night",
    "only",
    "open",
    "other",
    "over",
    "part",
    "place",
    "point",
    "right",
    "same",
    "said",
    "show",
    "side",
    "since",
    "small",
    "some",
    "still",
    "such",
    "take",
    "tell",
    "than",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "thing",
    "this",
    "those",
    "thought",
    "three",
    "through",
    "time",
    "told",
    "turn",
    "under",
    "upon",
    "used",
    "very",
    "want",
    "water",
    "well",
    "went",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "will",
    "with",
    "word",
    "work",
    "world",
    "would",
    "year",
    "your",
    # Domain words too generic for names
    "brain",
    "data",
    "head",
    "idea",
    "info",
    "learn",
    "mind",
    "note",
    "plan",
    "read",
    "save",
    "search",
    "send",
    "sort",
    "start",
    "store",
    "task",
    "test",
    "tool",
    "type",
    "view",
    "write",
}


def score_pronounceability(name: str) -> float:
    """Score 0-1 based on vowel/consonant alternation and ratio."""
    if not name:
        return 0.0

    vowel_count = sum(1 for c in name if c in VOWELS)
    ratio = vowel_count / len(name)

    # Ideal ratio is 0.35-0.50 (natural language range)
    if 0.30 <= ratio <= 0.55:
        ratio_score = 1.0
    elif 0.20 <= ratio <= 0.65:
        ratio_score = 0.6
    else:
        ratio_score = 0.2

    # Check for consonant clusters (3+ consonants in a row = hard to say)
    max_consonant_run = 0
    current_run = 0
    for c in name:
        if c in CONSONANTS:
            current_run += 1
            max_consonant_run = max(max_consonant_run, current_run)
        else:
            current_run = 0

    if max_consonant_run >= 4:
        cluster_penalty = 0.2
    elif max_consonant_run >= 3:
        cluster_penalty = 0.6
    else:
        cluster_penalty = 1.0

    return ratio_score * cluster_penalty


def score_length(name: str) -> float:
    """Score 0-1 based on name length. Sweetspot: 5-9 characters."""
    n = len(name)
    if 5 <= n <= 8:
        return 1.0
    elif n == 4 or n == 9:
        return 0.8
    elif n == 10:
        return 0.5
    elif n == 11:
        return 0.3
    else:
        return 0.1


def score_letter_variety(name: str) -> float:
    """Score 0-1 based on unique letter ratio (penalize repetition)."""
    if not name:
        return 0.0
    unique = len(set(name))
    ratio = unique / len(name)
    # 0.6+ is good variety, below 0.4 is repetitive (e.g. "aaabbb")
    if ratio >= 0.7:
        return 1.0
    elif ratio >= 0.5:
        return 0.7
    else:
        return 0.3


def score_spellability(name: str) -> float:
    """Score 0-1 based on how easy the name is to spell from hearing it.
    Penalizes ambiguous phonemes, silent letters, and unusual combos."""
    if not name:
        return 0.0

    score = 1.0
    n = name.lower()

    # Ambiguous phoneme pairs (sounds the same, spelled differently)
    # Each one means "could be spelled wrong"
    ambiguous = [
        "ph",  # could be "f"
        "gh",  # could be silent or "f"
        "ck",  # could be just "k"
        "qu",  # unusual
        "wr",  # silent w
        "kn",  # silent k
        "gn",  # silent g
        "ps",  # silent p
        "rh",  # unusual
        "wh",  # could be just "w"
        "ough",  # nightmare
        "eigh",  # nightmare
        "tion",  # could be "shun"
        "sion",  # could be "shun" or "zhun"
        "ious",  # hard to spell
        "eous",  # hard to spell
        "ei",  # i before e confusion
        "ie",  # i before e confusion
    ]

    for combo in ambiguous:
        if combo in n:
            score -= 0.15

    # Double letters are fine for common ones (ll, ss, tt) but unusual ones hurt
    unusual_doubles = [
        "aa",
        "bb",
        "cc",
        "dd",
        "ff",
        "gg",
        "hh",
        "jj",
        "kk",
        "pp",
        "qq",
        "uu",
        "vv",
        "ww",
        "xx",
        "yy",
        "zz",
    ]
    for dd in unusual_doubles:
        if dd in n:
            score -= 0.1

    # Bonus: name is phonetically transparent (consonant-vowel patterns)
    # Simple alternating CV patterns are easiest to spell
    cv_pattern = "".join("V" if c in VOWELS else "C" for c in n)
    if "CCC" not in cv_pattern and "VVV" not in cv_pattern:
        score += 0.1

    return max(0.0, min(1.0, score))


def score_starts_strong(name: str) -> float:
    """Bonus for starting with a strong/memorable consonant."""
    strong_starts = set("bcdgkmpstvz")
    if name and name[0] in strong_starts:
        return 1.0
    elif name and name[0] in VOWELS:
        return 0.7
    else:
        return 0.5


def score_candidate(name: str) -> dict:
    """Score a candidate name. Returns dict with scores and total."""
    scores = {
        "pronounce": score_pronounceability(name),
        "spelling": score_spellability(name),
        "length": score_length(name),
        "variety": score_letter_variety(name),
        "start": score_starts_strong(name),
    }

    # Weighted total (pronounceability + spelling matter most)
    weights = {"pronounce": 0.30, "spelling": 0.25, "length": 0.20, "variety": 0.15, "start": 0.10}
    total = sum(scores[k] * weights[k] for k in scores)
    scores["total"] = round(total, 3)

    return scores


def main():
    parser = argparse.ArgumentParser(description="Shortlist naming candidates by mechanical quality scoring")
    parser.add_argument("--input", type=str, default="candidates-raw.txt")
    parser.add_argument(
        "--out",
        type=str,
        default="candidates-shortlist.txt",
        help="Output filename (placed in output dir)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default=None,
        help="Output directory (default: ./namer-output/)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=200,
        help="Number of top candidates to keep (default: 200)",
    )
    parser.add_argument(
        "--pre-filter",
        type=str,
        default=None,
        help="Comma-separated substrings: only score candidates containing one of these",
    )
    args = parser.parse_args()

    from output import print_output_summary, resolve_output_path

    # Resolve paths
    if os.sep not in args.out and not os.path.dirname(args.out):
        args.out = resolve_output_path(args.out, args.out_dir)

    if not os.path.exists(args.input) and os.sep not in args.input:
        alt = resolve_output_path(args.input, args.out_dir)
        if os.path.exists(alt):
            args.input = alt

    # Load candidates
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Expected: candidates-raw.txt from the generate step.", file=sys.stderr)
        print("Run: python3 scripts/generate.py --seeds 'your,seed,words'", file=sys.stderr)
        sys.exit(1)

    with open(args.input) as f:
        candidates = [line.strip().lower() for line in f if line.strip()]

    if not candidates:
        print("❌ Input file is empty. No candidates to shortlist.", file=sys.stderr)
        sys.exit(1)

    # Pre-filter
    if args.pre_filter:
        keywords = [k.strip().lower() for k in args.pre_filter.split(",")]
        before = len(candidates)
        candidates = [c for c in candidates if any(k in c for k in keywords)]
        print(
            f"Pre-filter: {before} → {len(candidates)} candidates (keywords: {', '.join(keywords)})",
            file=sys.stderr,
        )

    # Remove common words
    before = len(candidates)
    candidates = [c for c in candidates if c not in COMMON_WORDS]
    removed = before - len(candidates)

    print("", file=sys.stderr)
    print(f"🔍 Scoring {len(candidates)} candidates...", file=sys.stderr)
    if removed > 0:
        print(f"   ({removed} common words removed)", file=sys.stderr)

    # Score all candidates
    scored = []
    for name in candidates:
        scores = score_candidate(name)
        scored.append((name, scores))

    # Sort by total score descending
    scored.sort(key=lambda x: x[1]["total"], reverse=True)

    # Take top N
    top = scored[: args.top]

    # Write output
    with open(args.out, "w") as f:
        for name, scores in top:
            f.write(f"{name}\t{scores['total']}\n")

    # Stats
    if top:
        best = top[0]
        worst = top[-1]
        print("", file=sys.stderr)
        print(
            f"✅ Done! {len(candidates)} → {len(top)} survivors",
            file=sys.stderr,
        )
        print(
            f"   Best:  {best[0]} (score: {best[1]['total']})",
            file=sys.stderr,
        )
        print(
            f"   Worst: {worst[0]} (score: {worst[1]['total']})",
            file=sys.stderr,
        )
        print(
            f"   Cutoff score: {worst[1]['total']}",
            file=sys.stderr,
        )
    else:
        print("⚠️  No candidates survived filtering.", file=sys.stderr)

    print("", file=sys.stderr)
    print_output_summary(
        [
            (f"{len(top)} shortlisted candidates", args.out),
        ]
    )

    print("▶️  Next: Agent reads shortlist and picks top 20 for availability check", file=sys.stderr)


if __name__ == "__main__":
    main()
