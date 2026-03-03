"""Tests for shortlist.py — mechanical quality scoring."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from shortlist import (
    COMMON_WORDS,
    score_candidate,
    score_length,
    score_letter_variety,
    score_pronounceability,
    score_spellability,
    score_starts_strong,
)


class TestPronouncability(unittest.TestCase):
    def test_balanced_vowel_ratio_scores_high(self):
        # "revari" has good vowel/consonant balance
        score = score_pronounceability("revari")
        self.assertGreaterEqual(score, 0.6)

    def test_all_consonants_scores_low(self):
        score = score_pronounceability("bcdfgh")
        self.assertLessEqual(score, 0.3)

    def test_consonant_cluster_penalized(self):
        # "strngth" has a long consonant cluster
        harsh = score_pronounceability("strngth")
        smooth = score_pronounceability("revari")
        self.assertLess(harsh, smooth)

    def test_empty_string(self):
        self.assertEqual(score_pronounceability(""), 0.0)

    def test_all_vowels_moderate(self):
        score = score_pronounceability("aeiou")
        # All vowels = ratio 1.0, outside ideal range
        self.assertLessEqual(score, 0.7)


class TestLength(unittest.TestCase):
    def test_sweetspot_5_to_8(self):
        for n in range(5, 9):
            self.assertEqual(score_length("a" * n), 1.0, f"Length {n} should be 1.0")

    def test_4_chars_good(self):
        self.assertEqual(score_length("abcd"), 0.8)

    def test_9_chars_good(self):
        self.assertEqual(score_length("a" * 9), 0.8)

    def test_very_long_low(self):
        self.assertLessEqual(score_length("a" * 15), 0.3)


class TestLetterVariety(unittest.TestCase):
    def test_all_unique(self):
        self.assertEqual(score_letter_variety("abcdef"), 1.0)

    def test_repetitive(self):
        score = score_letter_variety("aaabbb")
        self.assertLessEqual(score, 0.5)

    def test_empty(self):
        self.assertEqual(score_letter_variety(""), 0.0)


class TestSpellability(unittest.TestCase):
    def test_simple_name_scores_high(self):
        # "spark" — easy to spell, no ambiguity
        score = score_spellability("spark")
        self.assertGreaterEqual(score, 0.8)

    def test_ambiguous_phonemes_penalized(self):
        # "phright" has ph and gh
        score = score_spellability("phright")
        self.assertLessEqual(score, 0.7)

    def test_silent_letters_penalized(self):
        # "knight" has kn and gh
        score = score_spellability("knight")
        self.assertLessEqual(score, 0.7)

    def test_simple_beats_complex(self):
        simple = score_spellability("bolt")
        complex_ = score_spellability("phloughton")
        self.assertGreater(simple, complex_)

    def test_empty_string(self):
        self.assertEqual(score_spellability(""), 0.0)

    def test_cv_pattern_bonus(self):
        # "revari" has clean CV alternation
        score = score_spellability("revari")
        self.assertGreaterEqual(score, 0.8)


class TestStartsStrong(unittest.TestCase):
    def test_strong_consonant(self):
        self.assertEqual(score_starts_strong("bolt"), 1.0)

    def test_vowel_start(self):
        self.assertEqual(score_starts_strong("atlas"), 0.7)

    def test_weak_consonant(self):
        # 'h' is not in the strong set
        self.assertEqual(score_starts_strong("haze"), 0.5)


class TestScoreCandidate(unittest.TestCase):
    def test_returns_all_scores(self):
        result = score_candidate("revari")
        self.assertIn("pronounce", result)
        self.assertIn("spelling", result)
        self.assertIn("length", result)
        self.assertIn("variety", result)
        self.assertIn("start", result)
        self.assertIn("total", result)

    def test_total_is_weighted(self):
        result = score_candidate("revari")
        expected = (
            result["pronounce"] * 0.30
            + result["spelling"] * 0.25
            + result["length"] * 0.20
            + result["variety"] * 0.15
            + result["start"] * 0.10
        )
        self.assertAlmostEqual(result["total"], round(expected, 3), places=3)

    def test_good_name_beats_bad_name(self):
        good = score_candidate("spark")
        bad = score_candidate("xcrptly")
        self.assertGreater(good["total"], bad["total"])


class TestCommonWords(unittest.TestCase):
    def test_common_words_exist(self):
        self.assertIn("brain", COMMON_WORDS)
        self.assertIn("would", COMMON_WORDS)

    def test_invented_words_not_common(self):
        self.assertNotIn("qubitly", COMMON_WORDS)
        self.assertNotIn("revari", COMMON_WORDS)


if __name__ == "__main__":
    unittest.main()
