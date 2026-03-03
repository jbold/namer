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
    "memory", "recall", "remember", "trace", "echo", "mind", "know", "think",
    "weave", "thread", "pattern", "connect", "surface", "emerge", "find", "seek",
    "vault", "keep", "spark", "light", "vision", "dream", "ghost", "soul",
    "flow", "stream", "wave", "pulse", "glow", "drift",
]

PREFIXES = ["re", "un", "neo", "pre", "ever", "deep", "true", "all", "pan", "omni", "syn", "meta"]
SUFFIXES = [
    "mind", "trace", "flow", "spark", "vault", "keep", "weave", "forge",
    "well", "root", "seed", "bloom", "wake", "drift", "mark", "cast", "bind", "loom",
]

# Frequency thresholds for Datamuse results (per million in English text)
FREQ_SUPPRESS = 5.0  # Too common to own as a brand
FREQ_WARN = 1.0  # Borderline

# Common words to exclude from output (too generic for brand names)
COMMON_EXCLUSIONS = {
    "memory", "remember", "recall", "think", "mind", "know", "brain", "head",
    "thought", "idea", "dream", "find", "search", "look", "see", "feel",
    "sense", "learn", "the", "and", "for", "that", "this", "with", "from",
    "have", "has", "had", "was", "were", "been", "being", "will", "would",
    "could", "should", "might", "shall",
}

# Track frequency data for suppression reporting
_word_frequencies: dict[str, float] = {}


# --- Datamuse API ---


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
    """Query Datamuse API. Filters common words by frequency."""
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
                        continue
                results.append(word)
            return results
    except Exception as e:
        print(f"  Warning: Datamuse query failed ({params}): {e}", file=sys.stderr)
        return []


# --- Generation strategies ---


def generate_semantic(seeds: list[str], verbose: bool = False) -> set[str]:
    """Generate candidates from semantic associations via Datamuse."""
    candidates = set()
    for i, seed in enumerate(seeds):
        if verbose:
            print(f"  Semantic: {seed}", file=sys.stderr)
        else:
            pct = int((i + 1) / len(seeds) * 100)
            print(f"\r  Querying Datamuse: {i + 1}/{len(seeds)} seeds ({pct}%)   ", end="", file=sys.stderr)
        candidates.update(datamuse_query({"ml": seed}))
        time.sleep(0.15)
        candidates.update(datamuse_query({"rel_trg": seed}))
        time.sleep(0.15)
        candidates.update(datamuse_query({"sl": seed}, max_results=20))
        time.sleep(0.15)
    if not verbose:
        print("", file=sys.stderr)  # clear \r line
    return candidates


def generate_compounds(base_words: list[str]) -> set[str]:
    """Generate compound names (prefix+base, base+suffix, base+base)."""
    compounds = set()
    short_bases = [w for w in base_words if 3 <= len(w) <= 7 and w.isalpha()][:60]

    for prefix in PREFIXES:
        for base in short_bases:
            compounds.add(prefix + base)

    for base in short_bases:
        for suffix in SUFFIXES:
            compounds.add(base + suffix)

    for a, b in iterproduct(short_bases[:30], short_bases[:30]):
        if a != b and len(a) + len(b) <= 12:
            compounds.add(a + b)

    return compounds


def generate_morpheme_blends(
    seeds: list[str],
    blend_prefixes: list[str] | None = None,
    blend_suffixes: list[str] | None = None,
) -> set[str]:
    """Generate blended/portmanteau candidates from morpheme parts.

    If blend_prefixes/blend_suffixes are provided (LLM-generated), uses those.
    Otherwise falls back to extracting word[:4]/word[-4:] from seeds.
    """
    blends = set()
    roots = blend_prefixes if blend_prefixes else [s[:4] for s in seeds if len(s) >= 4]
    tails = blend_suffixes if blend_suffixes else [s[-4:] for s in seeds if len(s) >= 4]

    for root in roots:
        for tail in tails:
            if root != tail:
                blend = root + tail
                if 5 <= len(blend) <= 11:
                    blends.add(blend)

    return blends


# --- Filtering ---


def filter_basic(candidates: set[str], min_len: int, max_len: int) -> list[str]:
    """Basic filtering: length, alpha-only, no common English words."""
    filtered = []
    seen = set()
    for c in candidates:
        c = c.strip().lower()
        if not c or not c.isalpha():
            continue
        if len(c) < min_len or len(c) > max_len:
            continue
        if c in COMMON_EXCLUSIONS:
            continue
        if c in seen:
            continue
        seen.add(c)
        filtered.append(c)

    return sorted(filtered)


# --- CLI ---


def main():
    parser = argparse.ArgumentParser(description="Generate naming candidates via Datamuse API")
    parser.add_argument("--seeds", type=str, default=None, help="Comma-separated seed words")
    parser.add_argument("--out", type=str, default="candidates-raw.txt", help="Output filename")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory (default: ./namer-output/)")
    parser.add_argument("--min-len", type=int, default=4, help="Minimum name length")
    parser.add_argument("--max-len", type=int, default=12, help="Maximum name length")
    parser.add_argument("--blend-prefixes", type=str, default=None,
                        help="Comma-separated blend prefixes (LLM-generated, replaces word[:4] extraction)")
    parser.add_argument("--blend-suffixes", type=str, default=None,
                        help="Comma-separated blend suffixes (LLM-generated, replaces word[-4:] extraction)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show per-seed progress (default: summary only)")
    args = parser.parse_args()

    from output import get_output_dir, print_output_summary, resolve_output_path

    # Resolve output path
    if os.sep not in args.out and not os.path.dirname(args.out):
        args.out = resolve_output_path(args.out, args.out_dir)
    else:
        get_output_dir(args.out_dir)

    seeds = args.seeds.split(",") if args.seeds else DEFAULT_SEEDS

    print("", file=sys.stderr)
    print(f"🌱 Starting generation with {len(seeds)} seeds: {', '.join(seeds[:10])}", file=sys.stderr)
    if len(seeds) > 10:
        print(f"   ...and {len(seeds) - 10} more", file=sys.stderr)
    print("", file=sys.stderr)

    # Phase 1: Semantic expansion
    print("Phase 1/3: Semantic expansion via Datamuse API...", file=sys.stderr)
    try:
        semantic = generate_semantic(seeds, verbose=args.verbose)
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
    blend_prefixes = args.blend_prefixes.split(",") if args.blend_prefixes else None
    blend_suffixes = args.blend_suffixes.split(",") if args.blend_suffixes else None
    blends = generate_morpheme_blends(
        seeds + list(semantic)[:50],
        blend_prefixes=blend_prefixes,
        blend_suffixes=blend_suffixes,
    )
    print(f"  ✅ {len(blends)} blend candidates", file=sys.stderr)

    # Combine and filter
    all_candidates = semantic | compounds | blends
    filtered = filter_basic(all_candidates, args.min_len, args.max_len)

    # Write output
    with open(args.out, "w") as f:
        for c in filtered:
            f.write(c + "\n")

    suppressed = sum(1 for f in _word_frequencies.values() if f > FREQ_SUPPRESS)

    print("", file=sys.stderr)
    print(
        f"✅ Done! {len(all_candidates)} raw → {len(filtered)} after filtering "
        f"({args.min_len}-{args.max_len} chars, alpha only)",
        file=sys.stderr,
    )
    if suppressed:
        print(f"   🚫 {suppressed} common words suppressed (frequency > {FREQ_SUPPRESS}/million)", file=sys.stderr)

    print_output_summary([(f"{len(filtered)} candidates", args.out)])
    print("▶️  Next: python3 scripts/filter.py", file=sys.stderr)
    if len(filtered) > 500:
        print(
            f"💡 {len(filtered)} is a lot! Consider: python3 scripts/filter.py --pre-filter 'key,words' --limit 500",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
