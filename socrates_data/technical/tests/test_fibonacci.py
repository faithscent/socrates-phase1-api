"""
Unit Tests for Fibonacci Engine (FIB_V1)

Test coverage:
1. Retracement calculation accuracy
2. Extension calculation accuracy
3. Projection calculation accuracy
4. Insufficient data handling
5. Nearest level queries
6. Filtering and utility functions
"""

import unittest
from datetime import datetime, timedelta

from socrates_data.technical.fibonacci import (
    calculate_fibonacci_levels,
    get_fib_level_zone,
    filter_levels_by_type,
    filter_levels_by_direction,
    get_level_by_percentage,
    sort_levels_by_price,
    ALGORITHM_VERSION,
    RETRACEMENT_LEVELS,
    EXTENSION_LEVELS,
)
from socrates_data.technical.types import SwingPoint


class TestFibonacciCalculation(unittest.TestCase):
    """Test Fibonacci level calculations."""

    def test_insufficient_data_no_swings(self):
        """No swings should return empty result."""
        result = calculate_fibonacci_levels([], "TEST", "1D")

        self.assertTrue(result["success"])
        self.assertEqual(len(result["retracements"]), 0)
        self.assertEqual(len(result["extensions"]), 0)
        self.assertEqual(len(result["projections"]), 0)

    def test_insufficient_data_single_swing(self):
        """Single swing should return empty result."""
        swing = SwingPoint(
            symbol="TEST",
            timeframe="1D",
            timestamp=datetime(2024, 1, 1),
            price=100.0,
            swing_type="HIGH",  # type: ignore
            bar_index=0,
            atr_at_swing=2.0,
            move_from_previous_swing=0.0,
            move_pct=0.0,
            move_atr=0.0,
            significance="MINOR",  # type: ignore
            previous_swing_id=None,
            algorithm_version="SWING_V1",  # type: ignore
            created_at=datetime.utcnow(),
        )

        result = calculate_fibonacci_levels([swing], "TEST", "1D")

        self.assertTrue(result["success"])
        self.assertEqual(len(result["retracements"]), 0)
        self.assertEqual(len(result["extensions"]), 0)

    def test_retracement_bullish_calculation(self):
        """Bullish retracements should calculate correctly."""
        swings = [
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",  # type: ignore
                bar_index=0,
                atr_at_swing=2.0,
                move_from_previous_swing=0.0,
                move_pct=0.0,
                move_atr=0.0,
                significance="MINOR",  # type: ignore
                previous_swing_id=None,
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 2),
                price=200.0,
                swing_type="HIGH",  # type: ignore
                bar_index=5,
                atr_at_swing=2.0,
                move_from_previous_swing=100.0,
                move_pct=100.0,
                move_atr=50.0,
                significance="MAJOR",  # type: ignore
                previous_swing_id="0",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
        ]

        result = calculate_fibonacci_levels(swings, "TEST", "1D")

        self.assertTrue(result["success"])
        # Should have retracements (high to low is 100 move)
        self.assertGreater(len(result["retracements"]), 0)
        self.assertEqual(len(result["retracements"]), len(RETRACEMENT_LEVELS))

        # Check 50% retracement = 100 + (100 * 50/100) = 150
        fib_50 = get_level_by_percentage(result["retracements"], 50.0)
        self.assertIsNotNone(fib_50)
        self.assertAlmostEqual(fib_50["price"], 150.0, places=2)

    def test_retracement_bearish_calculation(self):
        """Bearish retracements should calculate correctly."""
        swings = [
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 1),
                price=200.0,
                swing_type="HIGH",  # type: ignore
                bar_index=0,
                atr_at_swing=2.0,
                move_from_previous_swing=0.0,
                move_pct=0.0,
                move_atr=0.0,
                significance="MINOR",  # type: ignore
                previous_swing_id=None,
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 2),
                price=100.0,
                swing_type="LOW",  # type: ignore
                bar_index=5,
                atr_at_swing=2.0,
                move_from_previous_swing=100.0,
                move_pct=50.0,
                move_atr=50.0,
                significance="MAJOR",  # type: ignore
                previous_swing_id="0",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
        ]

        result = calculate_fibonacci_levels(swings, "TEST", "1D")

        self.assertTrue(result["success"])
        self.assertGreater(len(result["retracements"]), 0)

        # Check 61.8% retracement = 100 + (100 * 61.8/100) = 161.8
        fib_618 = get_level_by_percentage(result["retracements"], 61.8)
        self.assertIsNotNone(fib_618)
        self.assertAlmostEqual(fib_618["price"], 161.8, places=2)

    def test_extension_calculation(self):
        """Extensions should calculate correctly."""
        swings = [
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",  # type: ignore
                bar_index=0,
                atr_at_swing=2.0,
                move_from_previous_swing=0.0,
                move_pct=0.0,
                move_atr=0.0,
                significance="MINOR",  # type: ignore
                previous_swing_id=None,
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 2),
                price=200.0,
                swing_type="HIGH",  # type: ignore
                bar_index=5,
                atr_at_swing=2.0,
                move_from_previous_swing=100.0,
                move_pct=100.0,
                move_atr=50.0,
                significance="MAJOR",  # type: ignore
                previous_swing_id="0",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
        ]

        result = calculate_fibonacci_levels(swings, "TEST", "1D")

        self.assertTrue(result["success"])
        self.assertGreater(len(result["extensions"]), 0)
        self.assertEqual(len(result["extensions"]), len(EXTENSION_LEVELS))

        # 100% extension = 200 + 0 = 200
        fib_100 = get_level_by_percentage(result["extensions"], 100.0)
        self.assertIsNotNone(fib_100)
        self.assertAlmostEqual(fib_100["price"], 200.0, places=2)

        # 161.8% extension = 200 + (100 * 61.8/100) = 261.8
        fib_1618 = get_level_by_percentage(result["extensions"], 161.8)
        self.assertIsNotNone(fib_1618)
        self.assertAlmostEqual(fib_1618["price"], 261.8, places=2)

    def test_projection_calculation(self):
        """Projections should calculate with 3+ swings."""
        swings = [
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",  # type: ignore
                bar_index=0,
                atr_at_swing=2.0,
                move_from_previous_swing=0.0,
                move_pct=0.0,
                move_atr=0.0,
                significance="MINOR",  # type: ignore
                previous_swing_id=None,
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 2),
                price=150.0,
                swing_type="HIGH",  # type: ignore
                bar_index=5,
                atr_at_swing=2.0,
                move_from_previous_swing=50.0,
                move_pct=50.0,
                move_atr=25.0,
                significance="INTERMEDIATE",  # type: ignore
                previous_swing_id="0",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 3),
                price=120.0,
                swing_type="LOW",  # type: ignore
                bar_index=10,
                atr_at_swing=2.0,
                move_from_previous_swing=30.0,
                move_pct=20.0,
                move_atr=15.0,
                significance="INTERMEDIATE",  # type: ignore
                previous_swing_id="1",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
        ]

        result = calculate_fibonacci_levels(swings, "TEST", "1D")

        self.assertTrue(result["success"])
        # 3+ swings should produce projections
        self.assertGreater(len(result["projections"]), 0)


class TestUtilityFunctions(unittest.TestCase):
    """Test Fibonacci utility functions."""

    def test_get_fib_level_zone(self):
        """get_fib_level_zone should return zone around level."""
        from socrates_data.technical.types import FibonacciLevel

        level = FibonacciLevel(
            symbol="TEST",
            timeframe="1D",
            fib_type="RETRACEMENT",  # type: ignore
            direction="BULLISH",  # type: ignore
            anchor_high=200.0,
            anchor_high_date=datetime.utcnow(),
            anchor_low=100.0,
            anchor_low_date=datetime.utcnow(),
            level=50.0,
            price=150.0,
            source="CALCULATED",  # type: ignore
            algorithm_version="FIB_V1",  # type: ignore
            created_at=datetime.utcnow(),
        )

        zone_low, zone_high = get_fib_level_zone(level, zone_width_pips=1.0)

        self.assertAlmostEqual(zone_low, 149.5, places=2)
        self.assertAlmostEqual(zone_high, 150.5, places=2)

    def test_filter_levels_by_type(self):
        """filter_levels_by_type should return only matching types."""
        swings = [
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",  # type: ignore
                bar_index=0,
                atr_at_swing=2.0,
                move_from_previous_swing=0.0,
                move_pct=0.0,
                move_atr=0.0,
                significance="MINOR",  # type: ignore
                previous_swing_id=None,
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 2),
                price=200.0,
                swing_type="HIGH",  # type: ignore
                bar_index=5,
                atr_at_swing=2.0,
                move_from_previous_swing=100.0,
                move_pct=100.0,
                move_atr=50.0,
                significance="MAJOR",  # type: ignore
                previous_swing_id="0",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
        ]

        result = calculate_fibonacci_levels(swings, "TEST", "1D")
        all_levels = result["retracements"] + result["extensions"]

        retracements_only = filter_levels_by_type(all_levels, "RETRACEMENT")
        self.assertTrue(all(l["fib_type"] == "RETRACEMENT" for l in retracements_only))

        extensions_only = filter_levels_by_type(all_levels, "EXTENSION")
        self.assertTrue(all(l["fib_type"] == "EXTENSION" for l in extensions_only))

    def test_filter_levels_by_direction(self):
        """filter_levels_by_direction should return only matching direction."""
        swings = [
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",  # type: ignore
                bar_index=0,
                atr_at_swing=2.0,
                move_from_previous_swing=0.0,
                move_pct=0.0,
                move_atr=0.0,
                significance="MINOR",  # type: ignore
                previous_swing_id=None,
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 2),
                price=200.0,
                swing_type="HIGH",  # type: ignore
                bar_index=5,
                atr_at_swing=2.0,
                move_from_previous_swing=100.0,
                move_pct=100.0,
                move_atr=50.0,
                significance="MAJOR",  # type: ignore
                previous_swing_id="0",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
        ]

        result = calculate_fibonacci_levels(swings, "TEST", "1D")
        all_levels = result["retracements"]

        bullish = filter_levels_by_direction(all_levels, "BULLISH")
        self.assertTrue(all(l["direction"] == "BULLISH" for l in bullish))

    def test_sort_levels_by_price(self):
        """sort_levels_by_price should sort ascending/descending."""
        swings = [
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",  # type: ignore
                bar_index=0,
                atr_at_swing=2.0,
                move_from_previous_swing=0.0,
                move_pct=0.0,
                move_atr=0.0,
                significance="MINOR",  # type: ignore
                previous_swing_id=None,
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 2),
                price=200.0,
                swing_type="HIGH",  # type: ignore
                bar_index=5,
                atr_at_swing=2.0,
                move_from_previous_swing=100.0,
                move_pct=100.0,
                move_atr=50.0,
                significance="MAJOR",  # type: ignore
                previous_swing_id="0",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
        ]

        result = calculate_fibonacci_levels(swings, "TEST", "1D")
        all_levels = result["retracements"]

        sorted_desc = sort_levels_by_price(all_levels, descending=True)
        for i in range(len(sorted_desc) - 1):
            self.assertGreaterEqual(sorted_desc[i]["price"], sorted_desc[i + 1]["price"])

        sorted_asc = sort_levels_by_price(all_levels, descending=False)
        for i in range(len(sorted_asc) - 1):
            self.assertLessEqual(sorted_asc[i]["price"], sorted_asc[i + 1]["price"])


class TestAlgorithmVersioning(unittest.TestCase):
    """Test algorithm versioning."""

    def test_all_levels_tagged_with_version(self):
        """All levels should be tagged with FIB_V1."""
        swings = [
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 1),
                price=100.0,
                swing_type="LOW",  # type: ignore
                bar_index=0,
                atr_at_swing=2.0,
                move_from_previous_swing=0.0,
                move_pct=0.0,
                move_atr=0.0,
                significance="MINOR",  # type: ignore
                previous_swing_id=None,
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 2),
                price=200.0,
                swing_type="HIGH",  # type: ignore
                bar_index=5,
                atr_at_swing=2.0,
                move_from_previous_swing=100.0,
                move_pct=100.0,
                move_atr=50.0,
                significance="MAJOR",  # type: ignore
                previous_swing_id="0",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
        ]

        result = calculate_fibonacci_levels(swings, "TEST", "1D")
        all_levels = result["retracements"] + result["extensions"]

        for level in all_levels:
            self.assertEqual(level["algorithm_version"], ALGORITHM_VERSION)


if __name__ == "__main__":
    unittest.main()
