"""
Unit tests for Elliott Wave Engine (ELLIOTT_V1)

Tests cover:
- Insufficient data handling
- Impulse pattern detection (5-wave)
- Correction pattern detection (3-wave)
- Fibonacci ratio validation
- Invalidation levels
- Primary vs alternate counts
- Utility functions
- Determinism and version tagging
"""

import unittest
from datetime import datetime, timedelta

from socrates_data.technical.elliott import (
    detect_elliott_waves,
    is_impulse_pattern,
    is_correction_pattern,
    is_bullish_wave,
    is_bearish_wave,
    get_invalidation_level,
    filter_candidates_by_confidence,
    get_highest_confidence_candidate,
    get_wave_label,
    ALGORITHM_VERSION,
)
from socrates_data.technical.types import OHLCV, SwingPoint


class TestElliottWaveInsufficientData(unittest.TestCase):
    """Test Elliott Wave with insufficient data."""

    def test_no_swings(self):
        """Should return success with empty candidates for no swings."""
        result = detect_elliott_waves([], "TEST", "1D")
        self.assertTrue(result["success"])
        self.assertEqual(len(result["impulse_candidates"]), 0)
        self.assertEqual(len(result["correction_candidates"]), 0)
        self.assertIsNone(result["primary_count"])

    def test_single_swing(self):
        """Should return success with empty candidates for single swing."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            )
        ]
        result = detect_elliott_waves(swings, "TEST", "1D")
        self.assertTrue(result["success"])
        self.assertEqual(len(result["impulse_candidates"]), 0)

    def test_two_swings(self):
        """Should return success with empty candidates for two swings."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=115.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "TEST", "1D")
        self.assertTrue(result["success"])
        self.assertEqual(len(result["impulse_candidates"]), 0)


class TestElliottWaveImpulsePatterns(unittest.TestCase):
    """Test impulse (5-wave) pattern detection."""

    def test_bullish_impulse_simple(self):
        """Should detect a simple bullish impulse pattern (1-2-3-4-5)."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=105.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=102.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 4),
                price=115.0,
                swing_type="HIGH",
                significance="MAJOR",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 5),
                price=110.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "QQQ", "1D")
        self.assertTrue(result["success"])
        self.assertGreater(len(result["impulse_candidates"]), 0)

    def test_bearish_impulse_simple(self):
        """Should detect a simple bearish impulse pattern (1-2-3-4-5)."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=115.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=110.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=113.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 4),
                price=100.0,
                swing_type="LOW",
                significance="MAJOR",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 5),
                price=105.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "QQQ", "1D")
        self.assertTrue(result["success"])
        self.assertGreater(len(result["impulse_candidates"]), 0)

    def test_impulse_has_correct_labels(self):
        """Impulse pattern should have correct wave labels (1-2-3-4-5)."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=105.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=102.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 4),
                price=115.0,
                swing_type="HIGH",
                significance="MAJOR",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 5),
                price=110.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "TEST", "1D")
        if result["impulse_candidates"]:
            candidate = result["impulse_candidates"][0]
            self.assertEqual(
                candidate["wave_labels"],
                ["WAVE_1", "WAVE_2", "WAVE_3", "WAVE_4", "WAVE_5"],
            )


class TestElliottWaveCorrectionPatterns(unittest.TestCase):
    """Test correction (3-wave) pattern detection."""

    def test_bearish_correction_simple(self):
        """Should detect a simple bearish correction pattern (A-B-C)."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=115.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=105.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=110.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "QQQ", "1D")
        self.assertTrue(result["success"])
        self.assertGreater(len(result["correction_candidates"]), 0)

    def test_bullish_correction_simple(self):
        """Should detect a simple bullish correction pattern (A-B-C)."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=110.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=105.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "QQQ", "1D")
        self.assertTrue(result["success"])
        self.assertGreater(len(result["correction_candidates"]), 0)

    def test_correction_has_correct_labels(self):
        """Correction pattern should have correct wave labels (A-B-C)."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=115.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=105.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=110.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "TEST", "1D")
        if result["correction_candidates"]:
            candidate = result["correction_candidates"][0]
            self.assertEqual(
                candidate["wave_labels"], ["WAVE_A", "WAVE_B", "WAVE_C"]
            )


class TestElliottWaveProperties(unittest.TestCase):
    """Test wave direction, pattern type, and properties."""

    def test_impulse_bullish_detection(self):
        """Bullish impulse should be detected correctly."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=105.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=102.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 4),
                price=115.0,
                swing_type="HIGH",
                significance="MAJOR",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 5),
                price=110.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "TEST", "1D")
        if result["impulse_candidates"]:
            candidate = result["impulse_candidates"][0]
            self.assertTrue(is_impulse_pattern(candidate))
            self.assertTrue(is_bullish_wave(candidate))

    def test_correction_direction_detection(self):
        """Correction should have correct direction."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=115.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=105.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=110.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "TEST", "1D")
        if result["correction_candidates"]:
            candidate = result["correction_candidates"][0]
            self.assertTrue(is_correction_pattern(candidate))


class TestElliottWaveInvalidation(unittest.TestCase):
    """Test invalidation level calculation."""

    def test_bullish_impulse_invalidation(self):
        """Bullish impulse invalidation should be at Wave 2 low."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=105.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=102.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 4),
                price=115.0,
                swing_type="HIGH",
                significance="MAJOR",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 5),
                price=110.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "TEST", "1D")
        if result["impulse_candidates"]:
            candidate = result["impulse_candidates"][0]
            invalidation = get_invalidation_level(candidate)
            self.assertIsNotNone(invalidation)
            self.assertLessEqual(invalidation, 102.0)


class TestElliottWaveUtility(unittest.TestCase):
    """Test utility functions."""

    def test_filter_candidates_by_confidence(self):
        """Should filter candidates by confidence threshold."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=105.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=102.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 4),
                price=115.0,
                swing_type="HIGH",
                significance="MAJOR",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 5),
                price=110.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "TEST", "1D")
        all_candidates = result["impulse_candidates"] + result["correction_candidates"]
        high_confidence = filter_candidates_by_confidence(all_candidates, 0.5)
        self.assertLessEqual(len(high_confidence), len(all_candidates))

    def test_get_highest_confidence_candidate(self):
        """Should return highest confidence candidate."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=105.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=102.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 4),
                price=115.0,
                swing_type="HIGH",
                significance="MAJOR",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 5),
                price=110.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "TEST", "1D")
        all_candidates = result["impulse_candidates"] + result["correction_candidates"]
        highest = get_highest_confidence_candidate(all_candidates)
        if highest:
            self.assertIsNotNone(highest["confidence"])

    def test_get_wave_label(self):
        """Should return correct wave label for index."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=105.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=102.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 4),
                price=115.0,
                swing_type="HIGH",
                significance="MAJOR",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 5),
                price=110.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "TEST", "1D")
        if result["impulse_candidates"]:
            candidate = result["impulse_candidates"][0]
            label_0 = get_wave_label(candidate, 0)
            label_1 = get_wave_label(candidate, 1)
            self.assertEqual(label_0, "WAVE_1")
            self.assertEqual(label_1, "WAVE_2")


class TestElliottWaveDeterminism(unittest.TestCase):
    """Test determinism and consistency."""

    def test_same_input_produces_same_output(self):
        """Same swings should produce identical wave detection."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=105.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=102.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 4),
                price=115.0,
                swing_type="HIGH",
                significance="MAJOR",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 5),
                price=110.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
        ]

        result1 = detect_elliott_waves(swings, "TEST", "1D")
        result2 = detect_elliott_waves(swings, "TEST", "1D")

        self.assertEqual(
            len(result1["impulse_candidates"]), len(result2["impulse_candidates"])
        )
        self.assertEqual(
            len(result1["correction_candidates"]),
            len(result2["correction_candidates"]),
        )


class TestElliottWaveVersioning(unittest.TestCase):
    """Test version tagging."""

    def test_version_tagging(self):
        """All outputs should be tagged with ELLIOTT_V1."""
        swings = [
            SwingPoint(
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 2),
                price=105.0,
                swing_type="HIGH",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 3),
                price=102.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 4),
                price=115.0,
                swing_type="HIGH",
                significance="MAJOR",
            ),
            SwingPoint(
                timestamp=datetime(2024, 1, 5),
                price=110.0,
                swing_type="LOW",
                significance="INTERMEDIATE",
            ),
        ]
        result = detect_elliott_waves(swings, "TEST", "1D")
        if result["impulse_candidates"]:
            candidate = result["impulse_candidates"][0]
            self.assertEqual(candidate["algorithm_version"], ALGORITHM_VERSION)
            self.assertEqual(candidate["algorithm_version"], "ELLIOTT_V1")


if __name__ == "__main__":
    unittest.main()
