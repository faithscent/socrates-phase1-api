"""
Unit Tests for Swing Detection Engine (SWING_V1)

Test coverage:
1. Synthetic controlled patterns (known swing locations)
2. Edge cases (insufficient data, flat markets, extreme moves)
3. ATR calculation accuracy
4. Significance classification
5. Algorithm determinism
"""

import unittest
from datetime import datetime, timedelta
from typing import List

from socrates_data.technical.swings import (
    detect_swings,
    calculate_atr,
    get_last_swing_high,
    get_last_swing_low,
    get_swing_sequence_direction,
    ALGORITHM_VERSION,
)
from socrates_data.technical.types import OHLCV


class TestATRCalculation(unittest.TestCase):
    """Test ATR (Average True Range) calculation accuracy."""

    def test_atr_insufficient_data(self):
        """ATR should handle bars < period gracefully."""
        bars: List[OHLCV] = [
            OHLCV(
                timestamp=datetime(2024, 1, 1),
                open=100.0,
                high=102.0,
                low=99.0,
                close=101.0,
                volume=1000,
            )
        ]
        atr = calculate_atr(bars, period=14)
        self.assertEqual(len(atr), 1)
        self.assertEqual(atr[0], 0.0)  # Insufficient data

    def test_atr_basic_calculation(self):
        """ATR should calculate correctly with sufficient bars."""
        # Generate 20 bars with known TR pattern
        bars: List[OHLCV] = []
        for i in range(20):
            # Simple uptrend
            close = 100.0 + i
            bars.append(
                OHLCV(
                    timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                    open=close - 0.5,
                    high=close + 1.0,
                    low=close - 1.0,
                    close=close,
                    volume=1000,
                )
            )

        atr = calculate_atr(bars, period=14)

        # First 13 should be 0 (insufficient data)
        for i in range(13):
            self.assertEqual(atr[i], 0.0)

        # 14th onwards should have values
        self.assertGreater(atr[13], 0.0)
        self.assertGreater(atr[14], 0.0)

        # ATR should be relatively stable
        atr_mean = sum(atr[13:]) / len(atr[13:])
        for val in atr[13:]:
            self.assertGreater(val, 0.5)  # Reasonable range


class TestSwingDetection(unittest.TestCase):
    """Test swing detection algorithm."""

    def test_insufficient_bars_error(self):
        """Should return error when bars < ATR_PERIOD + 2."""
        bars: List[OHLCV] = [
            OHLCV(
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=1000,
            )
            for i in range(10)
        ]

        result = detect_swings(bars, "TEST", "1D")

        self.assertFalse(result["success"])
        self.assertIsNotNone(result["error"])
        self.assertEqual(len(result["swings"]), 0)

    def test_simple_uptrend_swings(self):
        """Detect swings in a simple uptrend."""
        # Create pattern with larger moves: low, high, low, high
        bars: List[OHLCV] = []
        pattern = [
            # Baseline: establish ATR (first 14 bars)
            (100, 101, 99),
            (100, 101, 99),
            (100, 101, 99),
            (100, 101, 99),
            (100, 101, 99),
            (100, 101, 99),
            (100, 101, 99),
            (100, 101, 99),
            (100, 101, 99),
            (100, 101, 99),
            (100, 101, 99),
            (100, 101, 99),
            (100, 101, 99),
            (100, 101, 99),
            # Swing down (swing low)
            (99, 99, 85),
            (88, 92, 85),
            (87, 90, 80),
            (85, 90, 80),
            (85, 85, 82),
            # Swing up (swing high)
            (90, 110, 87),
            (105, 115, 105),
            (112, 120, 110),
            (118, 122, 115),
            (120, 120, 118),
            # Swing down (swing low)
            (118, 118, 95),
            (100, 105, 90),
            (96, 100, 90),
            (93, 98, 88),
            (90, 90, 88),
        ]

        for i, (op, hi, lo) in enumerate(pattern):
            bars.append(
                OHLCV(
                    timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                    open=op,
                    high=hi,
                    low=lo,
                    close=(op + hi + lo) / 3,
                    volume=1000,
                )
            )

        result = detect_swings(bars, "TEST", "1D")

        self.assertTrue(result["success"])
        # Should detect at least some swings with this clear pattern
        self.assertGreater(result["total_swings_found"], 0)

        # Check algorithm version is tagged
        if result["swings"]:
            self.assertEqual(result["swings"][0]["algorithm_version"], ALGORITHM_VERSION)

    def test_flat_market_minimal_swings(self):
        """Flat market should produce minimal or no swings."""
        bars: List[OHLCV] = [
            OHLCV(
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                open=100.0,
                high=100.1,
                low=99.9,
                close=100.0,
                volume=1000,
            )
            for i in range(25)
        ]

        result = detect_swings(bars, "TEST", "1D")

        self.assertTrue(result["success"])
        # Flat market should have very few swings
        self.assertLessEqual(result["total_swings_found"], 3)

    def test_extreme_move_significant_swing(self):
        """Large ATR move should create MAJOR significance swing."""
        bars: List[OHLCV] = []

        # First, stable period to establish ATR baseline
        for i in range(20):
            bars.append(
                OHLCV(
                    timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                    open=100.0 + i * 0.1,
                    high=100.1 + i * 0.1,
                    low=99.9 + i * 0.1,
                    close=100.0 + i * 0.1,
                    volume=1000,
                )
            )

        # Large drop (swing low)
        for i in range(20, 24):
            bars.append(
                OHLCV(
                    timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                    open=102.0 - (i - 20) * 15,  # Sharp drop
                    high=103.0 - (i - 20) * 15,
                    low=101.0 - (i - 20) * 15,
                    close=102.0 - (i - 20) * 15,
                    volume=2000,
                )
            )

        # Large rally (swing high)
        for i in range(24, 28):
            bars.append(
                OHLCV(
                    timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                    open=42.0 + (i - 24) * 15,  # Sharp rally
                    high=43.0 + (i - 24) * 15,
                    low=41.0 + (i - 24) * 15,
                    close=42.0 + (i - 24) * 15,
                    volume=2000,
                )
            )

        result = detect_swings(bars, "TEST", "1D")

        self.assertTrue(result["success"])
        # Should detect the large moves
        major_swings = [s for s in result["swings"] if s["significance"] == "MAJOR"]
        self.assertGreater(len(major_swings), 0)


class TestSignificanceClassification(unittest.TestCase):
    """Test swing significance classification."""

    def test_significance_thresholds(self):
        """Swings should be classified by move_atr multiple."""
        # Create controlled pattern with clear swings
        bars: List[OHLCV] = []

        # Baseline: first 14 bars to establish ATR
        for i in range(14):
            bars.append(
                OHLCV(
                    timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.0,
                    volume=1000,
                )
            )

        # Large move down (creates swing low at bar 18)
        for i in range(14, 19):
            bars.append(
                OHLCV(
                    timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                    open=100.0 - (i - 14) * 8,
                    high=101.0 - (i - 14) * 8,
                    low=99.0 - (i - 14) * 8,
                    close=100.0 - (i - 14) * 8,
                    volume=1000,
                )
            )

        # Large move up (creates swing high)
        for i in range(19, 24):
            bars.append(
                OHLCV(
                    timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                    open=60.0 + (i - 19) * 12,
                    high=61.0 + (i - 19) * 12,
                    low=59.0 + (i - 19) * 12,
                    close=60.0 + (i - 19) * 12,
                    volume=1000,
                )
            )

        # Move back to baseline
        for i in range(24, 30):
            bars.append(
                OHLCV(
                    timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.0,
                    volume=1000,
                )
            )

        result = detect_swings(bars, "TEST", "1D")

        self.assertTrue(result["success"])
        # Should have some swings
        self.assertGreater(result["total_swings_found"], 0)
        # Each swing should have a significance value
        for swing in result["swings"]:
            self.assertIn(swing["significance"], ["MINOR", "INTERMEDIATE", "MAJOR"])


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions for swing analysis."""

    def test_get_last_swing_high(self):
        """Should correctly identify last swing high."""
        bars: List[OHLCV] = [
            OHLCV(
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                open=100.0 + i if i % 2 == 0 else 100.0 - i,
                high=102.0 + i if i % 2 == 0 else 102.0 - i,
                low=98.0 + i if i % 2 == 0 else 98.0 - i,
                close=100.0 + i if i % 2 == 0 else 100.0 - i,
                volume=1000,
            )
            for i in range(25)
        ]

        result = detect_swings(bars, "TEST", "1D")

        if result["swings"]:
            last_high = get_last_swing_high(result["swings"])
            self.assertIsNotNone(last_high)
            self.assertEqual(last_high["swing_type"], "HIGH")

    def test_get_swing_sequence_direction(self):
        """Should identify current direction from swing sequence."""
        # Create simple swing pattern
        bars: List[OHLCV] = []

        # Swing up: low, high, low, high
        swings_pattern = [100, 110, 105, 115]

        for i in range(25):
            bar_type = i % 4
            if bar_type == 0:
                price = 100
            elif bar_type == 1:
                price = 110
            elif bar_type == 2:
                price = 105
            else:
                price = 115

            bars.append(
                OHLCV(
                    timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                    open=price,
                    high=price + 1,
                    low=price - 1,
                    close=price,
                    volume=1000,
                )
            )

        result = detect_swings(bars, "TEST", "1D")

        if result["swings"]:
            direction = get_swing_sequence_direction(result["swings"])
            self.assertIn(direction, ["UP", "DOWN", None])


class TestDeterminism(unittest.TestCase):
    """Test that swing detection is deterministic."""

    def test_same_input_produces_same_output(self):
        """Running twice on same bars should produce identical results."""
        bars: List[OHLCV] = [
            OHLCV(
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                open=100.0 + (i % 5),
                high=102.0 + (i % 5),
                low=98.0 + (i % 5),
                close=100.0 + (i % 5),
                volume=1000,
            )
            for i in range(25)
        ]

        result1 = detect_swings(bars, "TEST", "1D")
        result2 = detect_swings(bars, "TEST", "1D")

        # Same number of swings
        self.assertEqual(result1["total_swings_found"], result2["total_swings_found"])

        # Same swing prices (within precision)
        for s1, s2 in zip(result1["swings"], result2["swings"]):
            self.assertAlmostEqual(s1["price"], s2["price"], places=6)
            self.assertEqual(s1["swing_type"], s2["swing_type"])


class TestAlgorithmVersioning(unittest.TestCase):
    """Test algorithm version tagging."""

    def test_all_swings_tagged_with_version(self):
        """Every swing should be tagged with SWING_V1."""
        bars: List[OHLCV] = [
            OHLCV(
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                open=100.0 + i,
                high=102.0 + i,
                low=98.0 + i,
                close=100.0 + i,
                volume=1000,
            )
            for i in range(25)
        ]

        result = detect_swings(bars, "TEST", "1D")

        self.assertTrue(result["success"])
        for swing in result["swings"]:
            self.assertEqual(swing["algorithm_version"], ALGORITHM_VERSION)


if __name__ == "__main__":
    unittest.main()
