#!/usr/bin/env python3
"""
Name generation pipeline — Step 1: Volume generation via Datamuse API.
Zero LLM tokens. Pure API + combinatorics.

Usage:
    python3 generate.py [--seeds "memory,recall,mind"] [--out candidates-raw.txt] [--min-len 4] [--max-len 12]
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from itertools import product as iterproduct

DATAMUSE_BASE = "https://api.datamuse.com/words"
DEFAULT_SEEDS = [
    "memory",
    "recall",
    "remember",
    "trace",
    "echo",
    "mind",
    "know",
    "think",
    "weave",
    "thread",
    "pattern",
    "connect",
    "surface",
    "emerge",
    "find",
    "seek",
    "vault",
    "keep",
    "spark",
    "light",
    "vision",
    "dream",
    "ghost",
    "soul",
    "flow",
    "stream",
    "wave",
    "pulse",
    "glow",
    "drift",
]

# Prefixes and suffixes for compound generation
PREFIXES = ["re", "un", "neo", "pre", "ever", "deep", "true", "all", "pan", "omni", "syn", "meta"]
SUFFIXES = [
    "mind",
    "trace",
    "flow",
    "spark",
    "vault",
    "keep",
    "weave",
    "forge",
    "well",
    "root",
    "seed",
    "bloom",
    "wake",
    "drift",
    "mark",
    "cast",
    "bind",
    "loom",
]


# Frequency threshold: words appearing more than this many times per million
# in English text are "common" and make poor brand names (unownable, SEO nightmare).
# < 1.0 = rare/invented (great), 1-5 = uncommon (ok), > 5.0 = common (suppress)
FREQ_SUPPRESS = 5.0  # Hard suppress: too common to own
FREQ_WARN = 1.0  # Flag but keep: borderline

# Track frequency data for all words we see
_word_frequencies: dict[str, float] = {}


def _parse_frequency(tags: list[str]) -> float | None:
    """Extract frequency from Datamuse tags like 'f:25.228'."""
    for tag in tags:
        if tag.startswith("f:"):
            try:
                return float(tag[2:])
            except ValueError:
                pass
    return None


def datamuse_query(params: dict, max_results: int = 50) -> list[str]:
    """Query Datamuse API, return list of words. Filters common words by frequency."""
    params["max"] = str(max_results)
    params["md"] = "f"  # Request frequency metadata
    url = f"{DATAMUSE_BASE}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            results = []
            for item in data:
                word = item["word"]
                freq = _parse_frequency(item.get("tags", []))
                if freq is not None:
                    _word_frequencies[word] = freq
                    if freq > FREQ_SUPPRESS:
                        continue  # Too common — skip
                results.append(word)
            return results
    except Exception as e:
        print(f"  Warning: Datamuse query failed ({params}): {e}", file=sys.stderr)
        return []


def generate_semantic(seeds: list[str]) -> set[str]:
    """Generate candidates from semantic associations."""
    candidates = set()
    for seed in seeds:
        print(f"  Semantic: {seed}", file=sys.stderr)
        # Means like
        candidates.update(datamuse_query({"ml": seed}))
        time.sleep(0.15)
        # Triggered by
        candidates.update(datamuse_query({"rel_trg": seed}))
        time.sleep(0.15)
        # Sounds like
        candidates.update(datamuse_query({"sl": seed}, max_results=20))
        time.sleep(0.15)
    return candidates


def generate_compounds(base_words: list[str]) -> set[str]:
    """Generate compound names (prefix+base, base+suffix, base+base)."""
    compounds = set()
    # Short, punchy base words only
    short_bases = [w for w in base_words if 3 <= len(w) <= 7 and w.isalpha()][:60]

    for prefix in PREFIXES:
        for base in short_bases:
            compounds.add(prefix + base)

    for base in short_bases:
        for suffix in SUFFIXES:
            compounds.add(base + suffix)

    # Base + base combos (most interesting)
    for a, b in iterproduct(short_bases[:30], short_bases[:30]):
        if a != b and len(a) + len(b) <= 12:
            compounds.add(a + b)

    return compounds


def generate_morpheme_blends(seeds: list[str]) -> set[str]:
    """Generate blended/portmanteau candidates from seed morphemes."""
    blends = set()
    roots = [s[:4] for s in seeds if len(s) >= 4]  # First 4 chars
    tails = [s[-4:] for s in seeds if len(s) >= 4]  # Last 4 chars

    for root in roots:
        for tail in tails:
            if root != tail:
                blend = root + tail
                if 5 <= len(blend) <= 11:
                    blends.add(blend)

    return blends


def filter_basic(candidates: set[str], min_len: int, max_len: int) -> list[str]:
    """Basic filtering: length, alpha-only, no common English words."""
    # Common words to exclude (too generic)
    common = {
        "memory",
        "remember",
        "recall",
        "think",
        "mind",
        "know",
        "brain",
        "head",
        "thought",
        "idea",
        "dream",
        "find",
        "search",
        "look",
        "see",
        "feel",
        "sense",
        "learn",
        "the",
        "and",
        "for",
        "that",
        "this",
        "with",
        "from",
        "have",
        "has",
        "had",
        "was",
        "were",
        "been",
        "being",
        "will",
        "would",
        "could",
        "should",
        "might",
        "shall",
    }
    filtered = []
    seen = set()
    for c in candidates:
        c = c.strip().lower()
        if not c or not c.isalpha():
            continue
        if len(c) < min_len or len(c) > max_len:
            continue
        if c in common:
            continue
        if c in seen:
            continue
        seen.add(c)
        filtered.append(c)

    return sorted(filtered)


def main():
    parser = argparse.ArgumentParser(description="Generate naming candidates via Datamuse API")
    parser.add_argument("--seeds", type=str, default=None, help="Comma-separated seed words (default: built-in list)")
    parser.add_argument("--out", type=str, default="candidates-raw.txt", help="Output filename (placed in output dir)")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory (default: ./namer-output/)")
    parser.add_argument("--min-len", type=int, default=4, help="Minimum name length")
    parser.add_argument("--max-len", type=int, default=12, help="Maximum name length")
    args = parser.parse_args()

    from output import get_output_dir, print_output_summary, resolve_output_path

    # If --out is a bare filename, put it in the output dir. If it's a path, use as-is.
    if os.sep not in args.out and not os.path.dirname(args.out):
        args.out = resolve_output_path(args.out, args.out_dir)
    else:
        get_output_dir(args.out_dir)  # still create output dir for consistency

    seeds = args.seeds.split(",") if args.seeds else DEFAULT_SEEDS

    print("", file=sys.stderr)
    print(f"🌱 Starting generation with {len(seeds)} seeds: {', '.join(seeds[:10])}", file=sys.stderr)
    if len(seeds) > 10:
        print(f"   ...and {len(seeds) - 10} more", file=sys.stderr)
    print("", file=sys.stderr)

    # Phase 1: Semantic expansion
    print("Phase 1/3: Semantic expansion via Datamuse API...", file=sys.stderr)
    try:
        semantic = generate_semantic(seeds)
        print(f"  ✅ {len(semantic)} semantic candidates", file=sys.stderr)
    except Exception as e:
        print(f"  ❌ Datamuse API error: {e}", file=sys.stderr)
        print("     Check your internet connection and try again.", file=sys.stderr)
        sys.exit(1)

    # Phase 2: Compound generation
    print("Phase 2/3: Compound generation...", file=sys.stderr)
    base_words = list(semantic) + seeds
    compounds = generate_compounds(base_words)
    print(f"  ✅ {len(compounds)} compound candidates", file=sys.stderr)

    # Phase 3: Morpheme blends
    print("Phase 3/3: Morpheme blends...", file=sys.stderr)
    blends = generate_morpheme_blends(seeds + list(semantic)[:50])
    print(f"  ✅ {len(blends)} blend candidates", file=sys.stderr)

    # Combine and filter (don't add raw seeds — they're common words used as input, not output)
    all_candidates = semantic | compounds | blends
    filtered = filter_basic(all_candidates, args.min_len, args.max_len)

    # Write output
    with open(args.out, "w") as f:
        for c in filtered:
            f.write(c + "\n")

    # Count how many common words were suppressed
    suppressed = sum(1 for f in _word_frequencies.values() if f > FREQ_SUPPRESS)

    print("", file=sys.stderr)
    print(
        f"✅ Done! {len(all_candidates)} raw → {len(filtered)} after filtering ({args.min_len}-{args.max_len} chars, alpha only)",
        file=sys.stderr,
    )
    if suppressed:
        print(f"   🚫 {suppressed} common words suppressed (frequency > {FREQ_SUPPRESS}/million)", file=sys.stderr)

    print_output_summary(
        [
            (f"{len(filtered)} candidates", args.out),
        ]
    )

    # Next step guidance
    print("▶️  Next: python3 scripts/filter.py", file=sys.stderr)
    if len(filtered) > 500:
        print(
            f"💡 {len(filtered)} is a lot! Consider: python3 scripts/filter.py --pre-filter 'key,words' --limit 500",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
