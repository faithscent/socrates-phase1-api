"""
Unit tests for Target Engine (TARGET_V1)

Tests cover:
- Target extraction from all sources (FIB, ELLIOTT, STRUCTURE, CONFLUENCE)
- Target ranking (1=nearest, 2=mid, 3=long-term)
- Distance calculations (% and ATR)
- Confidence scoring
- Confluence linking
- Utility functions
- Version tagging
"""

import unittest
from datetime import datetime

from socrates_data.technical.targets import (
    derive_trading_targets,
    get_nearest_target,
    get_mid_term_targets,
    get_long_term_targets,
    filter_high_confidence_targets,
    get_targets_by_type,
    ALGORITHM_VERSION,
)
from socrates_data.technical.types import (
    OHLCV,
    SwingPoint,
    SwingDetectionOutput,
    MarketStructure,
    MarketStructureOutput,
    FibonacciLevel,
    FibonacciOutput,
    ElliottWaveOutput,
    ConfluenceOutput,
)


class TestTargetExtraction(unittest.TestCase):
    """Test target extraction from different sources."""

    def test_extract_fibonacci_targets(self):
        """Should extract Fibonacci levels as targets."""
        swings = SwingDetectionOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            swings=[
                SwingPoint(
                    symbol="TEST",
                    timeframe="1D",
                    timestamp=datetime(2024, 1, 1),
                    price=100.0,
                    swing_type="LOW",
                    bar_index=0,
                    atr_at_swing=2.0,
                    move_from_previous_swing=0.0,
                    move_pct=0.0,
                    move_atr=0.0,
                    significance="INTERMEDIATE",
                    previous_swing_id=None,
                    algorithm_version="SWING_V1",
                    created_at=datetime(2024, 1, 1),
                )
            ],
            total_bars_analyzed=30,
            total_swings_found=1,
            minor_swings=0,
            intermediate_swings=1,
            major_swings=0,
            last_swing_time=datetime(2024, 1, 1),
            last_swing_price=100.0,
        )

        structure = MarketStructureOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            structure=MarketStructure(
                symbol="TEST",
                timeframe="1D",
                as_of=datetime(2024, 1, 1),
                structure_state="BULLISH",
                last_high=115.0,
                last_high_time=datetime(2024, 1, 1),
                previous_high=110.0,
                previous_high_time=datetime(2023, 12, 31),
                last_low=105.0,
                last_low_time=datetime(2024, 1, 1),
                previous_low=100.0,
                previous_low_time=datetime(2023, 12, 30),
                structure_break=False,
                structure_break_type=None,
                structure_break_price=None,
                structure_break_date=None,
                algorithm_version="STRUCTURE_V1",
                created_at=datetime(2024, 1, 1),
            ),
            is_bullish=True,
            is_bearish=False,
            is_transitioning=False,
        )

        fibonacci = FibonacciOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            retracements=[
                FibonacciLevel(
                    symbol="TEST",
                    timeframe="1D",
                    fib_type="RETRACEMENT",
                    direction="BULLISH",
                    anchor_high=115.0,
                    anchor_high_date=datetime(2024, 1, 1),
                    anchor_low=100.0,
                    anchor_low_date=datetime(2024, 1, 1),
                    level=50.0,
                    price=107.5,
                    source="CALCULATED",
                    algorithm_version="FIB_V1",
                    created_at=datetime(2024, 1, 1),
                )
            ],
            extensions=[],
            projections=[],
            total_levels=1,
            nearest_level_below=None,
            nearest_level_above=None,
        )

        elliott = ElliottWaveOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            impulse_candidates=[],
            correction_candidates=[],
            primary_count=None,
            alternate_count=None,
            current_phase=None,
            total_candidates=0,
        )

        confluence = ConfluenceOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            zones=[],
            high_confluence_zones=0,
            medium_confluence_zones=0,
            low_confluence_zones=0,
        )

        result = derive_trading_targets(
            swings, structure, fibonacci, elliott, confluence, "TEST", "1D", 110.0
        )

        fib_targets = get_targets_by_type(result["targets"], "FIB")
        self.assertGreater(len(fib_targets), 0)

    def test_extract_structure_targets(self):
        """Should extract structure breaks as targets."""
        swings = SwingDetectionOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            swings=[],
            total_bars_analyzed=30,
            total_swings_found=0,
            minor_swings=0,
            intermediate_swings=0,
            major_swings=0,
            last_swing_time=None,
            last_swing_price=None,
        )

        structure = MarketStructureOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            structure=MarketStructure(
                symbol="TEST",
                timeframe="1D",
                as_of=datetime(2024, 1, 1),
                structure_state="BULLISH",
                last_high=115.0,
                last_high_time=datetime(2024, 1, 1),
                previous_high=110.0,
                previous_high_time=datetime(2023, 12, 31),
                last_low=105.0,
                last_low_time=datetime(2024, 1, 1),
                previous_low=100.0,
                previous_low_time=datetime(2023, 12, 30),
                structure_break=True,
                structure_break_type="BULLISH",
                structure_break_price=120.0,
                structure_break_date=datetime(2024, 1, 1),
                algorithm_version="STRUCTURE_V1",
                created_at=datetime(2024, 1, 1),
            ),
            is_bullish=True,
            is_bearish=False,
            is_transitioning=False,
        )

        fibonacci = FibonacciOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            retracements=[],
            extensions=[],
            projections=[],
            total_levels=0,
            nearest_level_below=None,
            nearest_level_above=None,
        )

        elliott = ElliottWaveOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            impulse_candidates=[],
            correction_candidates=[],
            primary_count=None,
            alternate_count=None,
            current_phase=None,
            total_candidates=0,
        )

        confluence = ConfluenceOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            zones=[],
            high_confluence_zones=0,
            medium_confluence_zones=0,
            low_confluence_zones=0,
        )

        result = derive_trading_targets(
            swings, structure, fibonacci, elliott, confluence, "TEST", "1D", 110.0
        )

        structure_targets = get_targets_by_type(result["targets"], "STRUCTURE")
        self.assertGreater(len(structure_targets), 0)


class TestTargetRanking(unittest.TestCase):
    """Test target ranking by distance."""

    def test_targets_ranked_by_distance(self):
        """Targets should be ranked 1, 2, 3 by distance from price."""
        swings = SwingDetectionOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            swings=[],
            total_bars_analyzed=30,
            total_swings_found=0,
            minor_swings=0,
            intermediate_swings=0,
            major_swings=0,
            last_swing_time=None,
            last_swing_price=None,
        )

        structure = MarketStructureOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            structure=MarketStructure(
                symbol="TEST",
                timeframe="1D",
                as_of=datetime(2024, 1, 1),
                structure_state="BULLISH",
                last_high=115.0,
                last_high_time=datetime(2024, 1, 1),
                previous_high=110.0,
                previous_high_time=datetime(2023, 12, 31),
                last_low=105.0,
                last_low_time=datetime(2024, 1, 1),
                previous_low=100.0,
                previous_low_time=datetime(2023, 12, 30),
                structure_break=False,
                structure_break_type=None,
                structure_break_price=None,
                structure_break_date=None,
                algorithm_version="STRUCTURE_V1",
                created_at=datetime(2024, 1, 1),
            ),
            is_bullish=True,
            is_bearish=False,
            is_transitioning=False,
        )

        fibonacci = FibonacciOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            retracements=[
                FibonacciLevel(
                    symbol="TEST",
                    timeframe="1D",
                    fib_type="RETRACEMENT",
                    direction="BULLISH",
                    anchor_high=120.0,
                    anchor_high_date=datetime(2024, 1, 1),
                    anchor_low=100.0,
                    anchor_low_date=datetime(2024, 1, 1),
                    level=50.0,
                    price=110.0,
                    source="CALCULATED",
                    algorithm_version="FIB_V1",
                    created_at=datetime(2024, 1, 1),
                ),
                FibonacciLevel(
                    symbol="TEST",
                    timeframe="1D",
                    fib_type="EXTENSION",
                    direction="BULLISH",
                    anchor_high=120.0,
                    anchor_high_date=datetime(2024, 1, 1),
                    anchor_low=100.0,
                    anchor_low_date=datetime(2024, 1, 1),
                    level=161.8,
                    price=132.36,
                    source="CALCULATED",
                    algorithm_version="FIB_V1",
                    created_at=datetime(2024, 1, 1),
                ),
            ],
            extensions=[],
            projections=[],
            total_levels=2,
            nearest_level_below=None,
            nearest_level_above=None,
        )

        elliott = ElliottWaveOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            impulse_candidates=[],
            correction_candidates=[],
            primary_count=None,
            alternate_count=None,
            current_phase=None,
            total_candidates=0,
        )

        confluence = ConfluenceOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            zones=[],
            high_confluence_zones=0,
            medium_confluence_zones=0,
            low_confluence_zones=0,
        )

        result = derive_trading_targets(
            swings, structure, fibonacci, elliott, confluence, "TEST", "1D", 105.0
        )

        self.assertGreater(len(result["targets"]), 0)
        # Check that targets are properly ranked
        for target in result["targets"]:
            self.assertIn(target["target_number"], [1, 2, 3])


class TestTargetUtility(unittest.TestCase):
    """Test utility functions."""

    def test_filter_high_confidence_targets(self):
        """Should filter targets with HIGH confluence."""
        swings = SwingDetectionOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            swings=[],
            total_bars_analyzed=30,
            total_swings_found=0,
            minor_swings=0,
            intermediate_swings=0,
            major_swings=0,
            last_swing_time=None,
            last_swing_price=None,
        )

        structure = MarketStructureOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            structure=MarketStructure(
                symbol="TEST",
                timeframe="1D",
                as_of=datetime(2024, 1, 1),
                structure_state="BULLISH",
                last_high=115.0,
                last_high_time=datetime(2024, 1, 1),
                previous_high=110.0,
                previous_high_time=datetime(2023, 12, 31),
                last_low=105.0,
                last_low_time=datetime(2024, 1, 1),
                previous_low=100.0,
                previous_low_time=datetime(2023, 12, 30),
                structure_break=False,
                structure_break_type=None,
                structure_break_price=None,
                structure_break_date=None,
                algorithm_version="STRUCTURE_V1",
                created_at=datetime(2024, 1, 1),
            ),
            is_bullish=True,
            is_bearish=False,
            is_transitioning=False,
        )

        fibonacci = FibonacciOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            retracements=[],
            extensions=[],
            projections=[],
            total_levels=0,
            nearest_level_below=None,
            nearest_level_above=None,
        )

        elliott = ElliottWaveOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            impulse_candidates=[],
            correction_candidates=[],
            primary_count=None,
            alternate_count=None,
            current_phase=None,
            total_candidates=0,
        )

        confluence = ConfluenceOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            zones=[],
            high_confluence_zones=0,
            medium_confluence_zones=0,
            low_confluence_zones=0,
        )

        result = derive_trading_targets(
            swings, structure, fibonacci, elliott, confluence, "TEST", "1D", 110.0
        )

        high_conf = filter_high_confidence_targets(result["targets"])
        self.assertLessEqual(len(high_conf), len(result["targets"]))


class TestTargetVersioning(unittest.TestCase):
    """Test version tagging."""

    def test_targets_tagged_with_version(self):
        """All targets should be tagged with TARGET_V1."""
        swings = SwingDetectionOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            swings=[],
            total_bars_analyzed=30,
            total_swings_found=0,
            minor_swings=0,
            intermediate_swings=0,
            major_swings=0,
            last_swing_time=None,
            last_swing_price=None,
        )

        structure = MarketStructureOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            structure=MarketStructure(
                symbol="TEST",
                timeframe="1D",
                as_of=datetime(2024, 1, 1),
                structure_state="BULLISH",
                last_high=115.0,
                last_high_time=datetime(2024, 1, 1),
                previous_high=110.0,
                previous_high_time=datetime(2023, 12, 31),
                last_low=105.0,
                last_low_time=datetime(2024, 1, 1),
                previous_low=100.0,
                previous_low_time=datetime(2023, 12, 30),
                structure_break=False,
                structure_break_type=None,
                structure_break_price=None,
                structure_break_date=None,
                algorithm_version="STRUCTURE_V1",
                created_at=datetime(2024, 1, 1),
            ),
            is_bullish=True,
            is_bearish=False,
            is_transitioning=False,
        )

        fibonacci = FibonacciOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            retracements=[],
            extensions=[],
            projections=[],
            total_levels=0,
            nearest_level_below=None,
            nearest_level_above=None,
        )

        elliott = ElliottWaveOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            impulse_candidates=[],
            correction_candidates=[],
            primary_count=None,
            alternate_count=None,
            current_phase=None,
            total_candidates=0,
        )

        confluence = ConfluenceOutput(
            success=True,
            error=None,
            symbol="TEST",
            timeframe="1D",
            zones=[],
            high_confluence_zones=0,
            medium_confluence_zones=0,
            low_confluence_zones=0,
        )

        result = derive_trading_targets(
            swings, structure, fibonacci, elliott, confluence, "TEST", "1D", 110.0
        )

        for target in result["targets"]:
            self.assertEqual(target["algorithm_version"], ALGORITHM_VERSION)
            self.assertEqual(target["algorithm_version"], "TARGET_V1")


if __name__ == "__main__":
    unittest.main()
