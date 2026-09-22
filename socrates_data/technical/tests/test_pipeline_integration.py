"""
End-to-end integration tests for Phase 1 pipeline.

Tests the complete flow: SWING → STRUCTURE → FIB → ELLIOTT → CONFLUENCE → TARGET
"""

import unittest
from datetime import datetime

from socrates_data.technical.pipeline import analyze_symbol, report_to_dict
from socrates_data.technical.types import OHLCV


class TestPipelineIntegration(unittest.TestCase):
    """Test complete Phase 1 pipeline."""

    def setUp(self):
        """Create realistic market data for testing."""
        # Simulate 30 bars of QQQ daily data
        self.bars = [
            {
                "timestamp": datetime(2024, 1, i + 1),
                "open": 400.0 + (i * 0.5),
                "high": 410.0 + (i * 0.5),
                "low": 395.0 + (i * 0.5),
                "close": 405.0 + (i * 0.5),
                "volume": 1000000 + (i * 10000),
            }
            for i in range(30)
        ]

        # Convert to OHLCV TypedDicts
        self.ohlcv_bars = [
            OHLCV(
                timestamp=bar["timestamp"],
                open=bar["open"],
                high=bar["high"],
                low=bar["low"],
                close=bar["close"],
                volume=bar["volume"],
            )
            for bar in self.bars
        ]

    def test_complete_pipeline_flow(self):
        """Test full pipeline from market data to targets."""
        report = analyze_symbol(
            bars=self.ohlcv_bars,
            symbol="QQQ",
            timeframe="1D",
            current_price=420.0,
        )

        # Verify report structure
        self.assertIsNotNone(report)
        self.assertEqual(report["symbol"], "QQQ")
        self.assertEqual(report["timeframe"], "1D")
        self.assertTrue(report["all_engines_successful"])
        self.assertEqual(len(report["errors"]), 0)

    def test_all_engines_executed(self):
        """Verify all 6 engines ran and produced output."""
        report = analyze_symbol(
            bars=self.ohlcv_bars,
            symbol="SPY",
            timeframe="1D",
            current_price=450.0,
        )

        # SWING_V1
        self.assertTrue(report["swings"]["success"])
        self.assertIsNotNone(report["swings"]["total_bars_analyzed"])

        # STRUCTURE_V1
        self.assertTrue(report["structure"]["success"])
        self.assertIsNotNone(report["structure"]["structure"]["structure_state"])

        # FIB_V1
        self.assertTrue(report["fibonacci"]["success"])
        self.assertIsNotNone(report["fibonacci"]["total_levels"])

        # ELLIOTT_V1
        self.assertTrue(report["elliott"]["success"])
        self.assertIsNotNone(report["elliott"]["total_candidates"])

        # CONFLUENCE_V1
        self.assertTrue(report["confluence"]["success"])
        self.assertIsNotNone(report["confluence"]["high_confluence_zones"])

        # TARGET_V1
        self.assertTrue(report["targets"]["success"])
        self.assertIsNotNone(report["targets"]["total_targets"])

    def test_algorithm_versions_tagged(self):
        """Verify all outputs tagged with algorithm versions."""
        report = analyze_symbol(
            bars=self.ohlcv_bars,
            symbol="TSLA",
            timeframe="1D",
            current_price=430.0,
        )

        versions = report["algorithm_versions"]
        self.assertEqual(versions["SWING"], "SWING_V1")
        self.assertEqual(versions["STRUCTURE"], "STRUCTURE_V1")
        self.assertEqual(versions["FIBONACCI"], "FIB_V1")
        self.assertEqual(versions["ELLIOTT"], "ELLIOTT_V1")
        self.assertEqual(versions["CONFLUENCE"], "CONFLUENCE_V1")
        self.assertEqual(versions["TARGET"], "TARGET_V1")

    def test_report_to_dict_serializable(self):
        """Verify report can be serialized to JSON-compatible dict."""
        report = analyze_symbol(
            bars=self.ohlcv_bars,
            symbol="MSFT",
            timeframe="1D",
            current_price=440.0,
        )

        report_dict = report_to_dict(report)

        # Verify dict structure
        self.assertIsInstance(report_dict, dict)
        self.assertIn("symbol", report_dict)
        self.assertIn("generated_at", report_dict)
        self.assertIn("algorithm_versions", report_dict)

        # Verify timestamps are ISO formatted strings
        self.assertIsInstance(report_dict["generated_at"], str)
        # Should be parseable as datetime
        datetime.fromisoformat(report_dict["generated_at"])

    def test_insufficient_bars_error(self):
        """Test error handling for insufficient bars."""
        with self.assertRaises(ValueError) as ctx:
            analyze_symbol(
                bars=[self.ohlcv_bars[0]],  # Only 1 bar
                symbol="QQQ",
                timeframe="1D",
                current_price=420.0,
            )

        self.assertIn("Insufficient bars", str(ctx.exception))

    def test_invalid_price_error(self):
        """Test error handling for invalid prices."""
        with self.assertRaises(ValueError) as ctx:
            analyze_symbol(
                bars=self.ohlcv_bars,
                symbol="QQQ",
                timeframe="1D",
                current_price=-100.0,  # Invalid price
            )

        self.assertIn("Invalid current_price", str(ctx.exception))

    def test_determinism_identical_runs(self):
        """Verify pipeline is deterministic: same input produces same output."""
        report1 = analyze_symbol(
            bars=self.ohlcv_bars,
            symbol="QQQ",
            timeframe="1D",
            current_price=420.0,
        )

        report2 = analyze_symbol(
            bars=self.ohlcv_bars,
            symbol="QQQ",
            timeframe="1D",
            current_price=420.0,
        )

        # Compare key outputs
        self.assertEqual(
            report1["swings"]["total_swings_found"],
            report2["swings"]["total_swings_found"]
        )
        self.assertEqual(
            report1["targets"]["total_targets"],
            report2["targets"]["total_targets"]
        )
        self.assertEqual(
            report1["confluence"]["high_confluence_zones"],
            report2["confluence"]["high_confluence_zones"]
        )


if __name__ == "__main__":
    unittest.main()
