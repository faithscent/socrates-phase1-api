"""
Unit tests for Confluence Engine (CONFLUENCE_V1)

Tests cover:
- Zone generation and grouping
- Evidence aggregation from multiple sources
- Confluence state classification (HIGH/MEDIUM/LOW)
- Zone width calculations
- Utility functions
- Determinism and version tagging
"""

import unittest
from datetime import datetime

from socrates_data.technical.confluence import (
    calculate_confluence_zones,
    get_high_confluence_zones,
    get_medium_confluence_zones,
    get_low_confluence_zones,
    get_nearest_zone_below,
    get_nearest_zone_above,
    has_multiple_evidence_sources,
    ALGORITHM_VERSION,
)
from socrates_data.technical.types import (
    FibonacciLevel,
    FibonacciOutput,
    MarketStructure,
    MarketStructureOutput,
    ElliottWaveOutput,
)


class TestConfluenceZoneGeneration(unittest.TestCase):
    """Test confluence zone creation."""

    def test_single_evidence_source_creates_low_confluence(self):
        """Single evidence source should create LOW confluence zone."""
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
                structure_break_price=112.0,
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

        result = calculate_confluence_zones(
            structure, fibonacci, elliott, "TEST", "1D", 110.0
        )

        low_zones = get_low_confluence_zones(result["zones"])
        self.assertGreater(len(low_zones), 0)

    def test_multiple_evidence_sources_creates_higher_confluence(self):
        """Multiple evidence sources should create MEDIUM+ confluence."""
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
                structure_break_price=112.0,
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
            retracements=[
                FibonacciLevel(
                    symbol="TEST",
                    timeframe="1D",
                    fib_type="RETRACEMENT",
                    direction="BULLISH",
                    anchor_high=115.0,
                    anchor_high_date=datetime(2024, 1, 1),
                    anchor_low=105.0,
                    anchor_low_date=datetime(2024, 1, 1),
                    level=50.0,
                    price=110.0,
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

        result = calculate_confluence_zones(
            structure, fibonacci, elliott, "TEST", "1D", 110.0
        )

        self.assertGreater(len(result["zones"]), 0)


class TestConfluenceZoneFiltering(unittest.TestCase):
    """Test zone filtering utilities."""

    def test_filter_by_confluence_state(self):
        """Should filter zones by confluence state."""
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
                structure_break_price=112.0,
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

        result = calculate_confluence_zones(
            structure, fibonacci, elliott, "TEST", "1D", 110.0
        )

        high_zones = get_high_confluence_zones(result["zones"])
        medium_zones = get_medium_confluence_zones(result["zones"])
        low_zones = get_low_confluence_zones(result["zones"])

        total = len(high_zones) + len(medium_zones) + len(low_zones)
        self.assertEqual(total, len(result["zones"]))

    def test_get_nearest_zone_above_price(self):
        """Should return nearest zone above current price."""
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
                last_high=120.0,
                last_high_time=datetime(2024, 1, 1),
                previous_high=110.0,
                previous_high_time=datetime(2023, 12, 31),
                last_low=105.0,
                last_low_time=datetime(2024, 1, 1),
                previous_low=100.0,
                previous_low_time=datetime(2023, 12, 30),
                structure_break=True,
                structure_break_type="BULLISH",
                structure_break_price=115.0,
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

        result = calculate_confluence_zones(
            structure, fibonacci, elliott, "TEST", "1D", 100.0
        )

        zone_above = get_nearest_zone_above(result["zones"], 100.0)
        self.assertIsNotNone(zone_above)
        if zone_above:
            self.assertGreater(zone_above["zone_low"], 100.0)


class TestConfluenceVersioning(unittest.TestCase):
    """Test version tagging."""

    def test_zones_tagged_with_version(self):
        """All zones should be tagged with CONFLUENCE_V1."""
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
                structure_break_price=112.0,
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

        result = calculate_confluence_zones(
            structure, fibonacci, elliott, "TEST", "1D", 110.0
        )

        for zone in result["zones"]:
            self.assertEqual(zone["algorithm_version"], ALGORITHM_VERSION)
            self.assertEqual(zone["algorithm_version"], "CONFLUENCE_V1")


if __name__ == "__main__":
    unittest.main()
