"""
SOCrates V2 Phase 1 — Unified Technical Intelligence Pipeline

Orchestrates all 6 deterministic engines:
1. SWING_V1       — Detect price swings
2. STRUCTURE_V1   — Analyze market structure (HH/HL/LH/LL)
3. FIB_V1         — Calculate Fibonacci retracement/extension/projection levels
4. ELLIOTT_V1     — Identify Elliott Wave impulse/correction patterns
5. CONFLUENCE_V1  — Aggregate zones where multiple indicators converge
6. TARGET_V1      — Derive trading targets ranked by distance

All engines are deterministic: same input always produces identical output.
All outputs tagged with immutable algorithm version.
"""

from datetime import datetime
from typing import List, Dict, Any

from socrates_data.technical.swings import detect_swings
from socrates_data.technical.market_structure import analyze_market_structure
from socrates_data.technical.fibonacci import calculate_fibonacci_levels
from socrates_data.technical.elliott import detect_elliott_waves
from socrates_data.technical.confluence import calculate_confluence_zones
from socrates_data.technical.targets import derive_trading_targets
from socrates_data.technical.types import (
    OHLCV,
    TechnicalIntelligenceReport,
)


def analyze_symbol(
    bars: List[OHLCV],
    symbol: str,
    timeframe: str,
    current_price: float,
) -> TechnicalIntelligenceReport:
    """
    Run complete Phase 1 technical analysis on market data.

    Args:
        bars: OHLCV bars (sorted by timestamp, oldest first)
        symbol: Ticker symbol (e.g., "QQQ", "SPY")
        timeframe: Timeframe string ("1D", "1W", "1M")
        current_price: Current market price for distance calculations

    Returns:
        TechnicalIntelligenceReport with all engine outputs and metadata

    Raises:
        ValueError: If inputs are invalid or insufficient
    """

    if not bars or len(bars) < 3:
        raise ValueError(f"Insufficient bars: need >= 3, got {len(bars)}")

    if current_price <= 0:
        raise ValueError(f"Invalid current_price: {current_price}")

    # ========================================================================
    # ENGINE 1: SWING DETECTION (SWING_V1)
    # ========================================================================
    swings_output = detect_swings(
        symbol=symbol,
        timeframe=timeframe,
        bars=bars,
    )

    if not swings_output["success"]:
        raise ValueError(f"Swing detection failed: {swings_output['error']}")

    # ========================================================================
    # ENGINE 2: MARKET STRUCTURE (STRUCTURE_V1)
    # ========================================================================
    structure_output = analyze_market_structure(
        swings=swings_output["swings"],
        symbol=symbol,
        timeframe=timeframe,
    )

    if not structure_output["success"]:
        raise ValueError(f"Structure detection failed: {structure_output['error']}")

    # ========================================================================
    # ENGINE 3: FIBONACCI LEVELS (FIB_V1)
    # ========================================================================
    fibonacci_output = calculate_fibonacci_levels(
        swings=swings_output["swings"],
        symbol=symbol,
        timeframe=timeframe,
    )

    if not fibonacci_output["success"]:
        raise ValueError(f"Fibonacci calculation failed: {fibonacci_output['error']}")

    # ========================================================================
    # ENGINE 4: ELLIOTT WAVE PATTERNS (ELLIOTT_V1)
    # ========================================================================
    elliott_output = detect_elliott_waves(
        swings=swings_output["swings"],
        symbol=symbol,
        timeframe=timeframe,
    )

    if not elliott_output["success"]:
        raise ValueError(f"Elliott Wave detection failed: {elliott_output['error']}")

    # ========================================================================
    # ENGINE 5: CONFLUENCE ZONES (CONFLUENCE_V1)
    # ========================================================================
    confluence_output = calculate_confluence_zones(
        structure=structure_output,
        fibonacci=fibonacci_output,
        elliott=elliott_output,
        symbol=symbol,
        timeframe=timeframe,
        current_price=current_price,
    )

    if not confluence_output["success"]:
        raise ValueError(f"Confluence calculation failed: {confluence_output['error']}")

    # ========================================================================
    # ENGINE 6: TRADING TARGETS (TARGET_V1)
    # ========================================================================
    targets_output = derive_trading_targets(
        swings=swings_output,
        structure=structure_output,
        fibonacci=fibonacci_output,
        elliott=elliott_output,
        confluence=confluence_output,
        symbol=symbol,
        timeframe=timeframe,
        current_price=current_price,
    )

    if not targets_output["success"]:
        raise ValueError(f"Target derivation failed: {targets_output['error']}")

    # ========================================================================
    # BUILD UNIFIED REPORT
    # ========================================================================
    report: TechnicalIntelligenceReport = {
        "symbol": symbol,
        "timeframe": timeframe,
        "generated_at": datetime.utcnow(),

        "swings": swings_output,
        "structure": structure_output,
        "fibonacci": fibonacci_output,
        "elliott": elliott_output,
        "confluence": confluence_output,
        "targets": targets_output,

        "all_engines_successful": (
            swings_output["success"]
            and structure_output["success"]
            and fibonacci_output["success"]
            and elliott_output["success"]
            and confluence_output["success"]
            and targets_output["success"]
        ),
        "errors": [
            err for err in [
                swings_output.get("error"),
                structure_output.get("error"),
                fibonacci_output.get("error"),
                elliott_output.get("error"),
                confluence_output.get("error"),
                targets_output.get("error"),
            ]
            if err
        ],

        "algorithm_versions": {
            "SWING": "SWING_V1",
            "STRUCTURE": "STRUCTURE_V1",
            "FIBONACCI": "FIB_V1",
            "ELLIOTT": "ELLIOTT_V1",
            "CONFLUENCE": "CONFLUENCE_V1",
            "TARGET": "TARGET_V1",
        },
    }

    return report


def report_to_dict(report: TechnicalIntelligenceReport) -> Dict[str, Any]:
    """
    Convert TechnicalIntelligenceReport to JSON-serializable dictionary.

    Handles datetime conversion to ISO strings.
    """
    return {
        "symbol": report["symbol"],
        "timeframe": report["timeframe"],
        "generated_at": report["generated_at"].isoformat(),

        "swings": {
            "success": report["swings"]["success"],
            "symbol": report["swings"]["symbol"],
            "timeframe": report["swings"]["timeframe"],
            "total_bars_analyzed": report["swings"]["total_bars_analyzed"],
            "total_swings_found": report["swings"]["total_swings_found"],
            "minor_swings": report["swings"]["minor_swings"],
            "intermediate_swings": report["swings"]["intermediate_swings"],
            "major_swings": report["swings"]["major_swings"],
        },

        "structure": {
            "success": report["structure"]["success"],
            "symbol": report["structure"]["symbol"],
            "timeframe": report["structure"]["timeframe"],
            "structure_state": report["structure"]["structure"]["structure_state"],
            "is_bullish": report["structure"]["is_bullish"],
            "is_bearish": report["structure"]["is_bearish"],
            "is_transitioning": report["structure"]["is_transitioning"],
        },

        "fibonacci": {
            "success": report["fibonacci"]["success"],
            "symbol": report["fibonacci"]["symbol"],
            "timeframe": report["fibonacci"]["timeframe"],
            "total_levels": report["fibonacci"]["total_levels"],
            "retracement_count": len(report["fibonacci"]["retracements"]),
            "extension_count": len(report["fibonacci"]["extensions"]),
            "projection_count": len(report["fibonacci"]["projections"]),
        },

        "elliott": {
            "success": report["elliott"]["success"],
            "symbol": report["elliott"]["symbol"],
            "timeframe": report["elliott"]["timeframe"],
            "impulse_candidates": len(report["elliott"]["impulse_candidates"]),
            "correction_candidates": len(report["elliott"]["correction_candidates"]),
            "has_primary_count": report["elliott"]["primary_count"] is not None,
            "current_phase": report["elliott"]["current_phase"],
        },

        "confluence": {
            "success": report["confluence"]["success"],
            "symbol": report["confluence"]["symbol"],
            "timeframe": report["confluence"]["timeframe"],
            "total_zones": len(report["confluence"]["zones"]),
            "high_confluence_zones": report["confluence"]["high_confluence_zones"],
            "medium_confluence_zones": report["confluence"]["medium_confluence_zones"],
            "low_confluence_zones": report["confluence"]["low_confluence_zones"],
        },

        "targets": {
            "success": report["targets"]["success"],
            "symbol": report["targets"]["symbol"],
            "timeframe": report["targets"]["timeframe"],
            "total_targets": report["targets"]["total_targets"],
            "high_confidence_targets": report["targets"]["high_confidence_targets"],
            "medium_confidence_targets": report["targets"]["medium_confidence_targets"],
        },

        "all_engines_successful": report["all_engines_successful"],
        "errors": report["errors"],
        "algorithm_versions": report["algorithm_versions"],
    }
