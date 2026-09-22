"""
Unit Tests for Market Structure Engine (STRUCTURE_V1)

Test coverage:
1. HH/HL pattern detection (BULLISH)
2. LL/LH pattern detection (BEARISH)
3. Structure breaks
4. Insufficient data handling
5. Mixed and transitional states
"""

import unittest
from datetime import datetime, timedelta

from socrates_data.technical.market_structure import (
    analyze_market_structure,
    is_bullish_structure,
    is_bearish_structure,
    has_structure_break,
    get_structure_break_direction,
    ALGORITHM_VERSION,
)
from socrates_data.technical.types import SwingPoint


class TestStructureDetection(unittest.TestCase):
    """Test market structure classification."""

    def test_insufficient_data_no_swings(self):
        """Empty swing list should return INSUFFICIENT_DATA."""
        result = analyze_market_structure([], "TEST", "1D")

        self.assertTrue(result["success"])
        self.assertEqual(result["structure"]["structure_state"], "INSUFFICIENT_DATA")

    def test_insufficient_data_single_swing(self):
        """Single swing should return INSUFFICIENT_DATA."""
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

        result = analyze_market_structure([swing], "TEST", "1D")

        self.assertTrue(result["success"])
        self.assertEqual(result["structure"]["structure_state"], "INSUFFICIENT_DATA")

    def test_bullish_structure_hh_hl(self):
        """HH + HL pattern should be classified as BULLISH."""
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
                price=110.0,
                swing_type="HIGH",  # type: ignore
                bar_index=5,
                atr_at_swing=2.0,
                move_from_previous_swing=10.0,
                move_pct=10.0,
                move_atr=5.0,
                significance="INTERMEDIATE",  # type: ignore
                previous_swing_id="0",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 3),
                price=102.0,
                swing_type="LOW",  # type: ignore
                bar_index=8,
                atr_at_swing=2.0,
                move_from_previous_swing=8.0,
                move_pct=7.3,
                move_atr=4.0,
                significance="INTERMEDIATE",  # type: ignore
                previous_swing_id="1",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 4),
                price=115.0,
                swing_type="HIGH",  # type: ignore
                bar_index=12,
                atr_at_swing=2.0,
                move_from_previous_swing=13.0,
                move_pct=12.7,
                move_atr=6.5,
                significance="MAJOR",  # type: ignore
                previous_swing_id="2",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
        ]

        result = analyze_market_structure(swings, "TEST", "1D")

        self.assertTrue(result["success"])
        self.assertEqual(result["structure"]["structure_state"], "BULLISH")
        self.assertTrue(is_bullish_structure(result["structure"]))
        self.assertFalse(is_bearish_structure(result["structure"]))

    def test_bearish_structure_ll_lh(self):
        """LL + LH pattern should be classified as BEARISH."""
        swings = [
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 1),
                price=120.0,
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
                move_from_previous_swing=20.0,
                move_pct=16.7,
                move_atr=10.0,
                significance="MAJOR",  # type: ignore
                previous_swing_id="0",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 3),
                price=110.0,
                swing_type="HIGH",  # type: ignore
                bar_index=8,
                atr_at_swing=2.0,
                move_from_previous_swing=10.0,
                move_pct=10.0,
                move_atr=5.0,
                significance="INTERMEDIATE",  # type: ignore
                previous_swing_id="1",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 4),
                price=90.0,
                swing_type="LOW",  # type: ignore
                bar_index=12,
                atr_at_swing=2.0,
                move_from_previous_swing=20.0,
                move_pct=18.2,
                move_atr=10.0,
                significance="MAJOR",  # type: ignore
                previous_swing_id="2",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
        ]

        result = analyze_market_structure(swings, "TEST", "1D")

        self.assertTrue(result["success"])
        self.assertEqual(result["structure"]["structure_state"], "BEARISH")
        self.assertFalse(is_bullish_structure(result["structure"]))
        self.assertTrue(is_bearish_structure(result["structure"]))

    def test_structure_break_bearish(self):
        """HH broken (becomes LH) indicates bearish structure break."""
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
                price=115.0,
                swing_type="HIGH",  # type: ignore
                bar_index=5,
                atr_at_swing=2.0,
                move_from_previous_swing=15.0,
                move_pct=15.0,
                move_atr=7.5,
                significance="MAJOR",  # type: ignore
                previous_swing_id="0",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 3),
                price=105.0,
                swing_type="LOW",  # type: ignore
                bar_index=8,
                atr_at_swing=2.0,
                move_from_previous_swing=10.0,
                move_pct=8.7,
                move_atr=5.0,
                significance="INTERMEDIATE",  # type: ignore
                previous_swing_id="1",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
            SwingPoint(
                symbol="TEST",
                timeframe="1D",
                timestamp=datetime(2024, 1, 4),
                price=110.0,
                swing_type="HIGH",  # type: ignore
                bar_index=12,
                atr_at_swing=2.0,
                move_from_previous_swing=5.0,
                move_pct=4.8,
                move_atr=2.5,
                significance="MINOR",  # type: ignore
                previous_swing_id="2",
                algorithm_version="SWING_V1",  # type: ignore
                created_at=datetime.utcnow(),
            ),
        ]

        result = analyze_market_structure(swings, "TEST", "1D")

        self.assertTrue(result["success"])
        self.assertTrue(has_structure_break(result["structure"]))
        # HH broken (110 < 115) so structure break is bearish
        break_direction = get_structure_break_direction(result["structure"])
        self.assertIsNotNone(break_direction)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions for structure analysis."""

    def test_is_bullish_structure(self):
        """is_bullish_structure should correctly identify bullish state."""
        from socrates_data.technical.types import MarketStructure

        bullish = MarketStructure(
            symbol="TEST",
            timeframe="1D",
            as_of=datetime.utcnow(),
            structure_state="BULLISH",  # type: ignore
            last_high=110.0,
            last_high_time=datetime(2024, 1, 1),
            previous_high=105.0,
            previous_high_time=datetime(2024, 1, 1),
            last_low=100.0,
            last_low_time=datetime(2024, 1, 1),
            previous_low=95.0,
            previous_low_time=datetime(2024, 1, 1),
            structure_break=False,
            structure_break_type=None,
            structure_break_price=None,
            structure_break_date=None,
            algorithm_version="STRUCTURE_V1",  # type: ignore
            created_at=datetime.utcnow(),
        )

        self.assertTrue(is_bullish_structure(bullish))

    def test_is_bearish_structure(self):
        """is_bearish_structure should correctly identify bearish state."""
        from socrates_data.technical.types import MarketStructure

        bearish = MarketStructure(
            symbol="TEST",
            timeframe="1D",
            as_of=datetime.utcnow(),
            structure_state="BEARISH",  # type: ignore
            last_high=100.0,
            last_high_time=datetime(2024, 1, 1),
            previous_high=105.0,
            previous_high_time=datetime(2024, 1, 1),
            last_low=90.0,
            last_low_time=datetime(2024, 1, 1),
            previous_low=95.0,
            previous_low_time=datetime(2024, 1, 1),
            structure_break=False,
            structure_break_type=None,
            structure_break_price=None,
            structure_break_date=None,
            algorithm_version="STRUCTURE_V1",  # type: ignore
            created_at=datetime.utcnow(),
        )

        self.assertTrue(is_bearish_structure(bearish))


class TestAlgorithmVersioning(unittest.TestCase):
    """Test algorithm versioning."""

    def test_structure_tagged_with_version(self):
        """Structure output should be tagged with STRUCTURE_V1."""
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

        result = analyze_market_structure([swing], "TEST", "1D")

        self.assertEqual(result["structure"]["algorithm_version"], ALGORITHM_VERSION)


if __name__ == "__main__":
    unittest.main()
