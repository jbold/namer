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


def datamuse_query(params: dict, max_results: int = 50) -> list[str]:
    """Query Datamuse API, return list of words."""
    params["max"] = str(max_results)
    url = f"{DATAMUSE_BASE}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            return [item["word"] for item in data]
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

    print(f"Generating candidates from {len(seeds)} seeds...", file=sys.stderr)

    # Phase 1: Semantic expansion
    print("Phase 1: Semantic expansion via Datamuse...", file=sys.stderr)
    semantic = generate_semantic(seeds)
    print(f"  → {len(semantic)} raw semantic candidates", file=sys.stderr)

    # Phase 2: Compound generation
    print("Phase 2: Compound generation...", file=sys.stderr)
    base_words = list(semantic) + seeds
    compounds = generate_compounds(base_words)
    print(f"  → {len(compounds)} compound candidates", file=sys.stderr)

    # Phase 3: Morpheme blends
    print("Phase 3: Morpheme blends...", file=sys.stderr)
    blends = generate_morpheme_blends(seeds + list(semantic)[:50])
    print(f"  → {len(blends)} blend candidates", file=sys.stderr)

    # Combine and filter
    all_candidates = semantic | compounds | blends | set(seeds)
    print(f"Total raw: {len(all_candidates)}", file=sys.stderr)

    filtered = filter_basic(all_candidates, args.min_len, args.max_len)
    print(f"After basic filter: {len(filtered)}", file=sys.stderr)

    # Write output
    with open(args.out, "w") as f:
        for c in filtered:
            f.write(c + "\n")

    print_output_summary(
        [
            (f"{len(filtered)} candidates", args.out),
        ]
    )


if __name__ == "__main__":
    main()
