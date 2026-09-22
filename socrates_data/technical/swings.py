"""
SOCrates V2 Phase 1 — Swing Detection Engine (SWING_V1)

Canonical swing detection using ATR-normalized movement analysis.
This is the load-bearing component; all downstream engines depend on it.

Algorithm: SWING_V1
- ATR period: 14 bars (standard)
- Swing requirement: movement >= ATR multiplier
- Significance: classified by move_atr multiple
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
import statistics

from .types import (
    OHLCV,
    SwingPoint,
    SwingDetectionOutput,
)


# ============================================================================
# CONSTANTS
# ============================================================================

ALGORITHM_VERSION = "SWING_V1"
ATR_PERIOD = 14
SWING_THRESHOLD_ATR = 0.8  # Minimum movement to be considered a swing

# Significance thresholds (expressed as multiples of ATR)
SIGNIFICANCE_MINOR_THRESHOLD = 1.5  # < 1.5 ATR
SIGNIFICANCE_INTERMEDIATE_THRESHOLD = 3.5  # 1.5-3.5 ATR
# >= 3.5 ATR is MAJOR


# ============================================================================
# ATR CALCULATION
# ============================================================================

def calculate_atr(bars: List[OHLCV], period: int = ATR_PERIOD) -> List[float]:
    """
    Calculate Average True Range (ATR) for a series of bars.

    Args:
        bars: OHLCV data sorted chronologically (oldest to newest)
        period: ATR lookback period (default 14)

    Returns:
        List of ATR values aligned with input bars.
        First (period-1) values are NaN-equivalent (returned as 0).
    """
    if len(bars) < 2:
        return [0.0] * len(bars)

    # Calculate True Range for each bar
    tr_values = []
    for i in range(len(bars)):
        if i == 0:
            # First bar: TR = high - low
            tr = bars[i]["high"] - bars[i]["low"]
        else:
            # TR = max(high - low, abs(high - close_prev), abs(low - close_prev))
            high_low = bars[i]["high"] - bars[i]["low"]
            high_close_prev = abs(bars[i]["high"] - bars[i - 1]["close"])
            low_close_prev = abs(bars[i]["low"] - bars[i - 1]["close"])
            tr = max(high_low, high_close_prev, low_close_prev)

        tr_values.append(tr)

    # Calculate ATR using SMA
    atr_values = []
    for i in range(len(tr_values)):
        if i < period - 1:
            atr_values.append(0.0)  # Insufficient data
        elif i == period - 1:
            # First ATR: simple average of first 'period' TR values
            atr = statistics.mean(tr_values[:period])
            atr_values.append(atr)
        else:
            # Subsequent ATR: smoothed with exponential average
            prev_atr = atr_values[i - 1]
            current_atr = (prev_atr * (period - 1) + tr_values[i]) / period
            atr_values.append(current_atr)

    return atr_values


# ============================================================================
# SWING DETECTION
# ============================================================================

def detect_swings(
    bars: List[OHLCV],
    symbol: str,
    timeframe: str,
    atr_multiplier: float = SWING_THRESHOLD_ATR,
) -> SwingDetectionOutput:
    """
    Detect swing highs and lows from OHLCV bars using ATR-normalized thresholds.

    Algorithm (SWING_V1):
    1. Calculate ATR over all bars
    2. Scan bars from oldest to newest
    3. Identify local highs and lows that exceed ATR-based threshold
    4. Classify significance based on move_atr multiple
    5. Tag all swings with SWING_V1 version

    Args:
        bars: OHLCV data (must be sorted chronologically, oldest to newest)
        symbol: Trading symbol (e.g., "QQQ", "SPY")
        timeframe: Timeframe code (e.g., "1D", "1W", "1M")
        atr_multiplier: Minimum swing height in ATR multiples (default 0.8)

    Returns:
        SwingDetectionOutput with swings list, statistics, and version tag
    """

    # Validation
    if not bars or len(bars) < ATR_PERIOD + 2:
        return SwingDetectionOutput(
            success=False,
            error=f"Insufficient bars: need at least {ATR_PERIOD + 2}, got {len(bars)}",
            symbol=symbol,
            timeframe=timeframe,
            swings=[],
            total_bars_analyzed=len(bars),
            total_swings_found=0,
            minor_swings=0,
            intermediate_swings=0,
            major_swings=0,
            last_swing_time=None,
            last_swing_price=None,
        )

    # Calculate ATR
    atr_values = calculate_atr(bars, ATR_PERIOD)

    swings: List[SwingPoint] = []
    swing_highs: List[Tuple[int, float]] = []  # (bar_index, price)
    swing_lows: List[Tuple[int, float]] = []   # (bar_index, price)

    # Identify local extremes (potential swings)
    # We need at least 2 bars before and after to confirm
    for i in range(2, len(bars) - 2):
        if atr_values[i] == 0:  # ATR not yet calculated
            continue

        current_high = bars[i]["high"]
        current_low = bars[i]["low"]

        # Check for swing high (local maximum)
        is_swing_high = (
            current_high > bars[i - 1]["high"]
            and current_high > bars[i - 2]["high"]
            and current_high > bars[i + 1]["high"]
            and current_high > bars[i + 2]["high"]
        )

        # Check for swing low (local minimum)
        is_swing_low = (
            current_low < bars[i - 1]["low"]
            and current_low < bars[i - 2]["low"]
            and current_low < bars[i + 1]["low"]
            and current_low < bars[i + 2]["low"]
        )

        if is_swing_high:
            swing_highs.append((i, current_high))

        if is_swing_low:
            swing_lows.append((i, current_low))

    # Build swing sequence alternating high/low
    # Filter by minimum ATR movement
    all_extremes = []
    for idx, price in swing_highs:
        all_extremes.append(("HIGH", idx, price))
    for idx, price in swing_lows:
        all_extremes.append(("LOW", idx, price))

    # Sort by bar index
    all_extremes.sort(key=lambda x: x[1])

    # Filter: remove consecutive same types and apply ATR threshold
    filtered_extremes = []
    for swing_type, bar_idx, price in all_extremes:
        if filtered_extremes:
            prev_swing_type, prev_bar_idx, prev_price = filtered_extremes[-1]

            # Skip if same direction (keep only the most extreme)
            if swing_type == prev_swing_type:
                if (swing_type == "HIGH" and price > prev_price) or \
                   (swing_type == "LOW" and price < prev_price):
                    filtered_extremes[-1] = (swing_type, bar_idx, price)
                continue

            # Check ATR threshold
            price_diff = abs(price - prev_price)
            atr_at_swing = atr_values[bar_idx]

            if atr_at_swing > 0 and price_diff < atr_multiplier * atr_at_swing:
                continue  # Movement too small

        filtered_extremes.append((swing_type, bar_idx, price))

    # Convert to SwingPoint objects with proper metadata
    previous_swing_id = None
    for swing_idx, (swing_type, bar_idx, price) in enumerate(filtered_extremes):
        atr_at_swing = atr_values[bar_idx]

        # Calculate move from previous swing
        if swing_idx == 0:
            move_from_prev = 0.0
            move_pct = 0.0
            move_atr = 0.0
        else:
            prev_swing = filtered_extremes[swing_idx - 1]
            prev_price = prev_swing[2]
            move_from_prev = abs(price - prev_price)
            move_pct = (move_from_prev / prev_price) * 100 if prev_price != 0 else 0
            move_atr = move_from_prev / atr_at_swing if atr_at_swing > 0 else 0

        # Classify significance
        if move_atr < SIGNIFICANCE_MINOR_THRESHOLD:
            significance = "MINOR"
        elif move_atr < SIGNIFICANCE_INTERMEDIATE_THRESHOLD:
            significance = "INTERMEDIATE"
        else:
            significance = "MAJOR"

        swing = SwingPoint(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=bars[bar_idx]["timestamp"],
            price=price,
            swing_type=swing_type,  # type: ignore
            bar_index=bar_idx,
            atr_at_swing=atr_at_swing,
            move_from_previous_swing=move_from_prev,
            move_pct=move_pct,
            move_atr=move_atr,
            significance=significance,  # type: ignore
            previous_swing_id=previous_swing_id,
            algorithm_version="SWING_V1",  # type: ignore
            created_at=datetime.utcnow(),
        )

        swings.append(swing)
        previous_swing_id = str(swing_idx)  # Simple ID for testing

    # Calculate statistics
    minor_count = sum(1 for s in swings if s["significance"] == "MINOR")
    intermediate_count = sum(1 for s in swings if s["significance"] == "INTERMEDIATE")
    major_count = sum(1 for s in swings if s["significance"] == "MAJOR")

    last_swing_time = swings[-1]["timestamp"] if swings else None
    last_swing_price = swings[-1]["price"] if swings else None

    return SwingDetectionOutput(
        success=True,
        error=None,
        symbol=symbol,
        timeframe=timeframe,
        swings=swings,
        total_bars_analyzed=len(bars),
        total_swings_found=len(swings),
        minor_swings=minor_count,
        intermediate_swings=intermediate_count,
        major_swings=major_count,
        last_swing_time=last_swing_time,
        last_swing_price=last_swing_price,
    )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_last_swing_high(swings: List[SwingPoint]) -> Optional[SwingPoint]:
    """Get the most recent swing high."""
    for swing in reversed(swings):
        if swing["swing_type"] == "HIGH":
            return swing
    return None


def get_last_swing_low(swings: List[SwingPoint]) -> Optional[SwingPoint]:
    """Get the most recent swing low."""
    for swing in reversed(swings):
        if swing["swing_type"] == "LOW":
            return swing
    return None


def get_swing_sequence_direction(swings: List[SwingPoint]) -> Optional[str]:
    """
    Determine direction from last swing.

    Returns:
        "UP" if last swing is a high (making higher lows/highs)
        "DOWN" if last swing is a low (making lower highs/lows)
        None if insufficient swings
    """
    if not swings:
        return None

    last_swing = swings[-1]
    if last_swing["swing_type"] == "HIGH":
        return "UP"
    else:
        return "DOWN"
