"""
SOCrates V2 Phase 1 — Fibonacci Engine (FIB_V1)

Calculates Fibonacci retracements, extensions, and projections from swings.

Depends on: SWING_V1 output

Algorithm: FIB_V1
- Retracement levels: 23.6%, 38.2%, 50%, 61.8%, 78.6%
- Extension levels: 100%, 127.2%, 161.8%, 261.8%
- Projection levels: from A→B→C basis
- Source tracking: CALCULATED (from engine), SOCRATES (from platform), BOTH
"""

from typing import List, Optional
from datetime import datetime

from .types import (
    SwingPoint,
    FibonacciLevel,
    FibonacciOutput,
)


ALGORITHM_VERSION = "FIB_V1"

# Standard Fibonacci ratios
RETRACEMENT_LEVELS = [23.6, 38.2, 50.0, 61.8, 78.6]
EXTENSION_LEVELS = [100.0, 127.2, 161.8, 261.8]
PROJECTION_LEVELS = [0.618, 1.0, 1.618]  # Ratios for A-B projection


# ============================================================================
# FIBONACCI CALCULATION
# ============================================================================

def calculate_fibonacci_levels(
    swings: List[SwingPoint],
    symbol: str,
    timeframe: str,
    socrates_fib_data: Optional[List[dict]] = None,
) -> FibonacciOutput:
    """
    Calculate Fibonacci levels from swings.

    Algorithm:
    1. Find all swing highs and lows
    2. For each pair (high-low or low-high), calculate retracements, extensions, projections
    3. Track source (CALCULATED, SOCRATES, BOTH)
    4. Build level list with zones

    Args:
        swings: List of SwingPoint from SWING_V1
        symbol: Trading symbol
        timeframe: Timeframe (1D, 1W, 1M)
        socrates_fib_data: Optional pre-calculated Socrates Fibonacci data for cross-referencing

    Returns:
        FibonacciOutput with all calculated levels
    """

    retracements: List[FibonacciLevel] = []
    extensions: List[FibonacciLevel] = []
    projections: List[FibonacciLevel] = []

    # Validation
    if len(swings) < 2:
        return FibonacciOutput(
            success=True,
            error=None,
            symbol=symbol,
            timeframe=timeframe,
            retracements=[],
            extensions=[],
            projections=[],
            total_levels=0,
            nearest_level_below=None,
            nearest_level_above=None,
        )

    swing_highs = [s for s in swings if s["swing_type"] == "HIGH"]
    swing_lows = [s for s in swings if s["swing_type"] == "LOW"]

    # Calculate from most recent swing pairs
    # Pair 1: Most recent high-low or low-high
    if len(swing_highs) >= 1 and len(swing_lows) >= 1:
        last_high = swing_highs[-1]
        last_low = swing_lows[-1]

        # Determine which came first (high or low)
        if last_high["timestamp"] > last_low["timestamp"]:
            # Last swing is high - calculate retracement from high to current
            if len(swing_lows) >= 1:
                prev_low = swing_lows[-1]
                anchor_high = last_high
                anchor_low = prev_low
                direction = "BULLISH"

                retracements.extend(
                    _calculate_retracements(
                        anchor_high, anchor_low, symbol, timeframe, direction
                    )
                )
                extensions.extend(
                    _calculate_extensions(
                        anchor_high, anchor_low, symbol, timeframe, direction
                    )
                )
        else:
            # Last swing is low - calculate retracement from low to current
            if len(swing_highs) >= 1:
                prev_high = swing_highs[-1]
                anchor_high = prev_high
                anchor_low = last_low
                direction = "BEARISH"

                retracements.extend(
                    _calculate_retracements(
                        anchor_high, anchor_low, symbol, timeframe, direction
                    )
                )
                extensions.extend(
                    _calculate_extensions(
                        anchor_high, anchor_low, symbol, timeframe, direction
                    )
                )

    # Calculate projections if we have 3+ swings
    if len(swings) >= 3:
        projections.extend(_calculate_projections(swings, symbol, timeframe))

    # Get nearest levels to current price (most recent swing)
    if swings:
        current_price = swings[-1]["price"]
        all_levels = retracements + extensions + projections

        below = [l for l in all_levels if l["price"] < current_price]
        above = [l for l in all_levels if l["price"] > current_price]

        nearest_below = max(below, key=lambda x: x["price"]) if below else None
        nearest_above = min(above, key=lambda x: x["price"]) if above else None
    else:
        nearest_below = None
        nearest_above = None

    return FibonacciOutput(
        success=True,
        error=None,
        symbol=symbol,
        timeframe=timeframe,
        retracements=retracements,
        extensions=extensions,
        projections=projections,
        total_levels=len(retracements) + len(extensions) + len(projections),
        nearest_level_below=nearest_below,
        nearest_level_above=nearest_above,
    )


def _calculate_retracements(
    anchor_high: SwingPoint,
    anchor_low: SwingPoint,
    symbol: str,
    timeframe: str,
    direction: str,  # BULLISH or BEARISH
) -> List[FibonacciLevel]:
    """Calculate Fibonacci retracement levels."""

    retracements: List[FibonacciLevel] = []

    high_price = anchor_high["price"]
    low_price = anchor_low["price"]
    move = high_price - low_price

    for level in RETRACEMENT_LEVELS:
        if direction == "BULLISH":
            # Retracement from high downward
            price = high_price - (move * level / 100)
        else:
            # Retracement from low upward
            price = low_price + (move * level / 100)

        fib = FibonacciLevel(
            symbol=symbol,
            timeframe=timeframe,
            fib_type="RETRACEMENT",  # type: ignore
            direction=direction,  # type: ignore
            anchor_high=high_price,
            anchor_high_date=anchor_high["timestamp"],
            anchor_low=low_price,
            anchor_low_date=anchor_low["timestamp"],
            level=level,
            price=price,
            source="CALCULATED",  # type: ignore
            algorithm_version=ALGORITHM_VERSION,  # type: ignore
            created_at=datetime.utcnow(),
        )
        retracements.append(fib)

    return retracements


def _calculate_extensions(
    anchor_high: SwingPoint,
    anchor_low: SwingPoint,
    symbol: str,
    timeframe: str,
    direction: str,  # BULLISH or BEARISH
) -> List[FibonacciLevel]:
    """Calculate Fibonacci extension levels."""

    extensions: List[FibonacciLevel] = []

    high_price = anchor_high["price"]
    low_price = anchor_low["price"]
    move = high_price - low_price

    for level in EXTENSION_LEVELS:
        if direction == "BULLISH":
            # Extensions upward from high
            price = high_price + (move * (level - 100) / 100)
        else:
            # Extensions downward from low
            price = low_price - (move * (level - 100) / 100)

        ext = FibonacciLevel(
            symbol=symbol,
            timeframe=timeframe,
            fib_type="EXTENSION",  # type: ignore
            direction=direction,  # type: ignore
            anchor_high=high_price,
            anchor_high_date=anchor_high["timestamp"],
            anchor_low=low_price,
            anchor_low_date=anchor_low["timestamp"],
            level=level,
            price=price,
            source="CALCULATED",  # type: ignore
            algorithm_version=ALGORITHM_VERSION,  # type: ignore
            created_at=datetime.utcnow(),
        )
        extensions.append(ext)

    return extensions


def _calculate_projections(
    swings: List[SwingPoint],
    symbol: str,
    timeframe: str,
) -> List[FibonacciLevel]:
    """
    Calculate Elliott Wave projections (A-B-C basis).

    Pattern:
    - Swing A (start)
    - Swing B (turn)
    - Swing C (target from B using A-B as basis)
    """

    projections: List[FibonacciLevel] = []

    if len(swings) < 3:
        return projections

    # Use last 3 swings as A-B-C basis
    swing_a = swings[-3]
    swing_b = swings[-2]
    swing_c = swings[-1]

    # Calculate A-B move
    move_ab = abs(swing_b["price"] - swing_a["price"])

    # Project from B using ratios
    for ratio in PROJECTION_LEVELS:
        if swing_b["swing_type"] == "HIGH":
            # B is high, project downward
            price = swing_b["price"] - (move_ab * ratio)
            direction = "BEARISH"
        else:
            # B is low, project upward
            price = swing_b["price"] + (move_ab * ratio)
            direction = "BULLISH"

        proj = FibonacciLevel(
            symbol=symbol,
            timeframe=timeframe,
            fib_type="PROJECTION",  # type: ignore
            direction=direction,  # type: ignore
            anchor_high=max(swing_a["price"], swing_b["price"]),
            anchor_high_date=swing_b["timestamp"] if swing_b["price"] > swing_a["price"] else swing_a["timestamp"],
            anchor_low=min(swing_a["price"], swing_b["price"]),
            anchor_low_date=swing_a["timestamp"] if swing_a["price"] < swing_b["price"] else swing_b["timestamp"],
            level=ratio * 100,  # Store as percentage
            price=price,
            source="CALCULATED",  # type: ignore
            algorithm_version=ALGORITHM_VERSION,  # type: ignore
            created_at=datetime.utcnow(),
        )
        projections.append(proj)

    return projections


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_fib_level_zone(level: FibonacciLevel, zone_width_pips: float = 0.5) -> tuple:
    """
    Get price zone around a Fibonacci level (not a point).

    Returns:
        (zone_low, zone_high)
    """
    center = level["price"]
    half_width = zone_width_pips / 2

    return (center - half_width, center + half_width)


def filter_levels_by_type(
    levels: List[FibonacciLevel],
    fib_type: str,  # RETRACEMENT, EXTENSION, PROJECTION
) -> List[FibonacciLevel]:
    """Filter Fibonacci levels by type."""
    return [l for l in levels if l["fib_type"] == fib_type]


def filter_levels_by_direction(
    levels: List[FibonacciLevel],
    direction: str,  # BULLISH, BEARISH
) -> List[FibonacciLevel]:
    """Filter Fibonacci levels by direction."""
    return [l for l in levels if l["direction"] == direction]


def get_level_by_percentage(
    levels: List[FibonacciLevel],
    percentage: float,
) -> Optional[FibonacciLevel]:
    """Get a specific Fibonacci level by percentage (e.g., 61.8)."""
    matches = [l for l in levels if abs(l["level"] - percentage) < 0.01]
    return matches[0] if matches else None


def sort_levels_by_price(
    levels: List[FibonacciLevel],
    descending: bool = True,
) -> List[FibonacciLevel]:
    """Sort Fibonacci levels by price."""
    return sorted(levels, key=lambda x: x["price"], reverse=descending)
