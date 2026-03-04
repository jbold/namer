#!/usr/bin/env python3
"""
Name shortlisting pipeline — Step 3: Mechanical quality scoring.
Zero LLM tokens. Zero API calls. Pure heuristics.

Scores candidates by pronounceability, length sweetspot, letter patterns,
and uniqueness. Reduces ~10,000 candidates to ~100 high-quality survivors
so the LLM never has to read the full list.

Usage:
    python3 shortlist.py [--input candidates-raw.txt] [--top 100]
    python3 shortlist.py --pre-filter "quant,flux,ion"
"""

import argparse
import sys

from fileio import apply_pre_filter, load_candidates, resolve_input, resolve_output
from output import print_output_summary

VOWELS = set("aeiouy")
CONSONANTS = set("bcdfghjklmnpqrstvwxz")

# Common English words that make bad product names (too generic)
COMMON_WORDS = {
    "about", "after", "again", "also", "always", "another", "back", "because",
    "been", "before", "being", "between", "both", "came", "come", "could",
    "does", "done", "down", "each", "even", "every", "first", "from", "give",
    "going", "good", "great", "have", "here", "high", "home", "into", "just",
    "keep", "know", "last", "left", "life", "like", "line", "little", "long",
    "look", "made", "make", "many", "might", "more", "most", "much", "must",
    "name", "never", "next", "night", "only", "open", "other", "over", "part",
    "place", "point", "right", "same", "said", "show", "side", "since", "small",
    "some", "still", "such", "take", "tell", "than", "that", "their", "them",
    "then", "there", "these", "they", "thing", "this", "those", "thought",
    "three", "through", "time", "told", "turn", "under", "upon", "used", "very",
    "want", "water", "well", "went", "were", "what", "when", "where", "which",
    "while", "will", "with", "word", "work", "world", "would", "year", "your",
    # Domain words too generic for names
    "brain", "data", "head", "idea", "info", "learn", "mind", "note", "plan",
    "read", "save", "search", "send", "sort", "start", "store", "task", "test",
    "tool", "type", "view", "write",
}


# --- Scoring functions (each does ONE thing) ---


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

    # Penalize consonant clusters (3+ in a row = hard to say)
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


def score_spellability(name: str) -> float:
    """Score 0-1 based on how easy the name is to spell from hearing it.
    Penalizes ambiguous phonemes, silent letters, and unusual combos."""
    if not name:
        return 0.0

    score = 1.0
    n = name.lower()

    # Ambiguous phoneme pairs (sounds the same, spelled differently)
    ambiguous = [
        "ph", "gh", "ck", "qu", "wr", "kn", "gn", "ps", "rh", "wh",
        "ough", "eigh", "tion", "sion", "ious", "eous", "ei", "ie",
    ]
    for combo in ambiguous:
        if combo in n:
            score -= 0.15

    # Unusual double letters
    unusual_doubles = [
        "aa", "bb", "cc", "dd", "ff", "gg", "hh", "jj", "kk",
        "pp", "qq", "uu", "vv", "ww", "xx", "yy", "zz",
    ]
    for dd in unusual_doubles:
        if dd in n:
            score -= 0.1

    # Bonus: clean CV alternation (no triple consonants or triple vowels)
    cv_pattern = "".join("V" if c in VOWELS else "C" for c in n)
    if "CCC" not in cv_pattern and "VVV" not in cv_pattern:
        score += 0.1

    return max(0.0, min(1.0, score))


def score_length(name: str) -> float:
    """Score 0-1 based on name length. Sweetspot: 5-8 characters."""
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
    if ratio >= 0.7:
        return 1.0
    elif ratio >= 0.5:
        return 0.7
    else:
        return 0.3


def score_starts_strong(name: str) -> float:
    """Bonus for starting with a strong/memorable consonant."""
    strong_starts = set("bcdgkmpstvz")
    if name and name[0] in strong_starts:
        return 1.0
    elif name and name[0] in VOWELS:
        return 0.7
    else:
        return 0.5


# --- Sound symbolism categories ---

PLOSIVES = set("bdgkptcq")  # c is usually /k/, q is /k/
FRICATIVES = set("fhsvzjx")  # h=glottal, j=/dʒ/, x=/ks/
NASALS = set("mn")
LIQUIDS = set("lrw")  # w=approximant, grouped with liquids

# Pharma-sounding suffixes to penalize
PHARMA_SUFFIXES = (
    "ucid", "enix", "ogan", "ixin", "azol", "idol", "ipam", "otal",
    "ucin", "exin", "orin", "idan", "azin", "ifen", "opam", "udin",
)


def score_sound_symbolism(name: str) -> float:
    """Score 0-1 based on phonetic personality consistency.
    Rewards names that commit to a clear sound profile
    (consistently warm OR consistently sharp, not a random mix).
    Penalizes pharma-sounding patterns."""
    if not name:
        return 0.0

    n = name.lower()

    # Classify each consonant into its phonetic category
    category_counts = {"plosive": 0, "fricative": 0, "nasal": 0, "liquid": 0}
    consonant_total = 0

    for c in n:
        if c in PLOSIVES:
            category_counts["plosive"] += 1
            consonant_total += 1
        elif c in FRICATIVES:
            category_counts["fricative"] += 1
            consonant_total += 1
        elif c in NASALS:
            category_counts["nasal"] += 1
            consonant_total += 1
        elif c in LIQUIDS:
            category_counts["liquid"] += 1
            consonant_total += 1

    if consonant_total == 0:
        # All vowels — no consonant personality to measure
        return 0.5

    # Score consistency: highest category ratio indicates clear personality
    max_ratio = max(category_counts.values()) / consonant_total
    # Scale: 0.25 (uniform across 4) → 1.0 (all one category)
    consistency = (max_ratio - 0.25) / 0.75  # normalize to 0-1
    consistency = max(0.0, min(1.0, consistency))

    # Base score from consistency
    score = 0.3 + 0.7 * consistency

    # Pharma suffix penalty
    for suffix in PHARMA_SUFFIXES:
        if n.endswith(suffix):
            score -= 0.3
            break

    return max(0.0, min(1.0, score))


def score_prefix_diversity(name: str, prefix_counts: dict[str, int] | None = None) -> float:
    """Score 0-1 based on prefix uniqueness across the candidate pool.
    Penalizes when >10 candidates share a 4-char prefix."""
    if not prefix_counts or len(name) < 4:
        return 1.0

    prefix = name[:4].lower()
    count = prefix_counts.get(prefix, 1)

    if count <= 3:
        return 1.0
    elif count <= 6:
        return 0.7
    elif count <= 10:
        return 0.4
    else:
        return 0.2


# --- Composite scoring ---

WEIGHTS = {
    "pronounce": 0.20,
    "spelling": 0.20,
    "length": 0.15,
    "variety": 0.10,
    "start": 0.05,
    "sound": 0.15,
    "diversity": 0.15,
}


def score_candidate(name: str, prefix_counts: dict[str, int] | None = None) -> dict:
    """Score a candidate name. Returns dict with individual scores and weighted total."""
    scores = {
        "pronounce": score_pronounceability(name),
        "spelling": score_spellability(name),
        "length": score_length(name),
        "variety": score_letter_variety(name),
        "start": score_starts_strong(name),
        "sound": score_sound_symbolism(name),
        "diversity": score_prefix_diversity(name, prefix_counts),
    }
    scores["total"] = round(sum(scores[k] * WEIGHTS[k] for k in WEIGHTS), 3)
    return scores


def main():
    parser = argparse.ArgumentParser(description="Shortlist naming candidates by mechanical quality scoring")
    parser.add_argument("--input", type=str, default="candidates-raw.txt")
    parser.add_argument("--out", type=str, default="candidates-shortlist.txt", help="Output filename")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory (default: ./namer-output/)")
    parser.add_argument("--top", type=int, default=100, help="Number of top candidates to keep (default: 100)")
    parser.add_argument("--pre-filter", type=str, default=None, help="Comma-separated substrings to match")
    args = parser.parse_args()

    # Resolve paths
    args.out = resolve_output(args.out, args.out_dir)
    args.input = resolve_input(args.input, args.out_dir)

    # Load, filter, and remove common words
    candidates = load_candidates(
        args.input, step_name="generate",
        run_hint="python3 scripts/generate.py --seeds 'your,seed,words'",
    )
    candidates = [c.lower() for c in candidates]
    candidates = apply_pre_filter(candidates, args.pre_filter)

    before = len(candidates)
    candidates = [c for c in candidates if c not in COMMON_WORDS]
    removed = before - len(candidates)

    print("", file=sys.stderr)
    print(f"🔍 Scoring {len(candidates)} candidates...", file=sys.stderr)
    if removed > 0:
        print(f"   ({removed} common words removed)", file=sys.stderr)

    # Prefix frequency pre-pass for diversity scoring
    from collections import Counter
    prefix_counts = Counter(c[:4] for c in candidates if len(c) >= 4)

    # Score and sort
    scored = [(name, score_candidate(name, prefix_counts)) for name in candidates]
    scored.sort(key=lambda x: x[1]["total"], reverse=True)
    top = scored[: args.top]

    # Write output
    with open(args.out, "w") as f:
        for name, scores in top:
            f.write(f"{name}\t{scores['total']}\n")

    # Summary
    if top:
        best = top[0]
        worst = top[-1]
        print("", file=sys.stderr)
        print(f"✅ Done! {len(candidates)} → {len(top)} survivors", file=sys.stderr)
        print(f"   Best:  {best[0]} (score: {best[1]['total']})", file=sys.stderr)
        print(f"   Worst: {worst[0]} (score: {worst[1]['total']})", file=sys.stderr)
        print(f"   Cutoff score: {worst[1]['total']}", file=sys.stderr)
    else:
        print("⚠️  No candidates survived filtering.", file=sys.stderr)

    print("", file=sys.stderr)
    print_output_summary([(f"{len(top)} shortlisted candidates", args.out)])
    print("▶️  Next: Agent reads shortlist and picks top 20 for availability check", file=sys.stderr)


if __name__ == "__main__":
    main()
