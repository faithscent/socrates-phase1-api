"""
SOCrates V2 Phase 1 — Market Structure Engine (STRUCTURE_V1)

Analyzes high/low sequence (HH/HL/LH/LL) from swing points.
Classifies market direction state and detects structure breaks.

Depends on: SWING_V1 output

Algorithm: STRUCTURE_V1
- Analyzes last 2 highs and last 2 lows from swing sequence
- Classifies states: BULLISH, BEARISH, RANGE, TRANSITION, MIXED, INSUFFICIENT_DATA
- Detects structure breaks (when HH becomes LL, etc.)
"""

from typing import Optional, List
from datetime import datetime

from .types import (
    SwingPoint,
    MarketStructure,
    MarketStructureOutput,
)


ALGORITHM_VERSION = "STRUCTURE_V1"


# ============================================================================
# STRUCTURE DETECTION
# ============================================================================

def analyze_market_structure(
    swings: List[SwingPoint],
    symbol: str,
    timeframe: str,
) -> MarketStructureOutput:
    """
    Analyze market structure from swing sequence.

    Algorithm:
    1. Extract last 2 swing highs and lows
    2. Classify structure state based on HH/HL/LH/LL pattern
    3. Detect structure breaks (transitions)

    Args:
        swings: List of SwingPoint from SWING_V1
        symbol: Trading symbol
        timeframe: Timeframe (1D, 1W, 1M)

    Returns:
        MarketStructureOutput with classified structure state
    """

    if not swings or len(swings) < 2:
        structure = MarketStructure(
            symbol=symbol,
            timeframe=timeframe,
            as_of=datetime.utcnow(),
            structure_state="INSUFFICIENT_DATA",
            last_high=None,
            last_high_time=None,
            previous_high=None,
            previous_high_time=None,
            last_low=None,
            last_low_time=None,
            previous_low=None,
            previous_low_time=None,
            structure_break=False,
            structure_break_type=None,
            structure_break_price=None,
            structure_break_date=None,
            algorithm_version=ALGORITHM_VERSION,  # type: ignore
            created_at=datetime.utcnow(),
        )

        return MarketStructureOutput(
            success=True,
            error=None,
            symbol=symbol,
            timeframe=timeframe,
            structure=structure,
            is_bullish=False,
            is_bearish=False,
            is_transitioning=False,
        )

    # Extract all highs and lows from swing sequence
    swing_highs = [s for s in swings if s["swing_type"] == "HIGH"]
    swing_lows = [s for s in swings if s["swing_type"] == "LOW"]

    # Get last 2 of each
    last_high: Optional[SwingPoint] = swing_highs[-1] if swing_highs else None
    prev_high: Optional[SwingPoint] = swing_highs[-2] if len(swing_highs) >= 2 else None

    last_low: Optional[SwingPoint] = swing_lows[-1] if swing_lows else None
    prev_low: Optional[SwingPoint] = swing_lows[-2] if len(swing_lows) >= 2 else None

    # Classify structure
    structure_state, structure_break, break_type = _classify_structure(
        last_high, prev_high, last_low, prev_low, swings
    )

    # Build structure object
    structure = MarketStructure(
        symbol=symbol,
        timeframe=timeframe,
        as_of=datetime.utcnow(),
        structure_state=structure_state,  # type: ignore
        last_high=last_high["price"] if last_high else None,
        last_high_time=last_high["timestamp"] if last_high else None,
        previous_high=prev_high["price"] if prev_high else None,
        previous_high_time=prev_high["timestamp"] if prev_high else None,
        last_low=last_low["price"] if last_low else None,
        last_low_time=last_low["timestamp"] if last_low else None,
        previous_low=prev_low["price"] if prev_low else None,
        previous_low_time=prev_low["timestamp"] if prev_low else None,
        structure_break=structure_break,
        structure_break_type=break_type,  # type: ignore
        structure_break_price=_get_break_price(swings, break_type),
        structure_break_date=_get_break_date(swings, break_type),
        algorithm_version=ALGORITHM_VERSION,  # type: ignore
        created_at=datetime.utcnow(),
    )

    return MarketStructureOutput(
        success=True,
        error=None,
        symbol=symbol,
        timeframe=timeframe,
        structure=structure,
        is_bullish=(structure_state == "BULLISH"),
        is_bearish=(structure_state == "BEARISH"),
        is_transitioning=(structure_state == "TRANSITION"),
    )


def _classify_structure(
    last_high: Optional[SwingPoint],
    prev_high: Optional[SwingPoint],
    last_low: Optional[SwingPoint],
    prev_low: Optional[SwingPoint],
    swings: List[SwingPoint],
) -> tuple:
    """
    Classify market structure and detect breaks.

    Returns:
        (structure_state, structure_break, break_type)
    """

    # Insufficient data
    if not last_high or not last_low:
        return "INSUFFICIENT_DATA", False, None

    # Single high/low (no history)
    if not prev_high or not prev_low:
        return "INSUFFICIENT_DATA", False, None

    # Extract prices
    last_h_price = last_high["price"]
    prev_h_price = prev_high["price"]
    last_l_price = last_low["price"]
    prev_l_price = prev_low["price"]

    # Determine HH/HL (highs) and HH/LH (lows)
    is_hh = last_h_price > prev_h_price  # Higher high
    is_hh_broken = last_h_price < prev_h_price  # Lower high (HH broken)

    is_hl = last_l_price > prev_l_price  # Higher low
    is_ll = last_l_price < prev_l_price  # Lower low

    # Determine sequence direction (last swing type)
    if swings:
        last_swing_type = swings[-1]["swing_type"]
    else:
        last_swing_type = None

    # Classify structure
    if is_hh and is_hl:
        state = "BULLISH"
        structure_break = False
        break_type = None
    elif is_hh_broken and is_ll:
        state = "BEARISH"
        structure_break = False
        break_type = None
    elif is_hh_broken and is_hl:
        # Mixed signals: HH broken but HL continues - transitioning bearish
        state = "TRANSITION"
        structure_break = True
        break_type = "BEARISH"  # HH broken is the key signal
    elif is_hh and is_ll:
        # Mixed signals: could be transitioning
        state = "TRANSITION"
        structure_break = True
        break_type = "BULLISH" if last_swing_type == "HIGH" else None
    elif is_hh_broken and not is_hl and not is_ll:
        # HH broken, lows still connected
        state = "MIXED"
        structure_break = True
        break_type = "BEARISH"
    elif not is_hh and is_hl:
        # No higher high yet, but higher low - ranging
        state = "RANGE"
        structure_break = False
        break_type = None
    elif is_ll:
        # New low without new high - bearish
        state = "BEARISH"
        structure_break = False
        break_type = None
    else:
        state = "MIXED"
        structure_break = False
        break_type = None

    return state, structure_break, break_type


def _get_break_price(
    swings: List[SwingPoint],
    break_type: Optional[str],
) -> Optional[float]:
    """Get the price level where structure was broken."""

    if not break_type or len(swings) < 2:
        return None

    # For a bearish break, it's below the previous high
    # For a bullish break, it's above the previous low

    swing_highs = [s for s in swings if s["swing_type"] == "HIGH"]
    swing_lows = [s for s in swings if s["swing_type"] == "LOW"]

    if break_type == "BEARISH" and len(swing_highs) >= 2:
        return swing_highs[-2]["price"]  # Previous high (break below this)
    elif break_type == "BULLISH" and len(swing_lows) >= 2:
        return swing_lows[-2]["price"]  # Previous low (break above this)

    return None


def _get_break_date(
    swings: List[SwingPoint],
    break_type: Optional[str],
) -> Optional[datetime]:
    """Get the timestamp when structure was broken."""

    if not break_type or len(swings) < 2:
        return None

    swing_highs = [s for s in swings if s["swing_type"] == "HIGH"]
    swing_lows = [s for s in swings if s["swing_type"] == "LOW"]

    if break_type == "BEARISH" and len(swing_highs) >= 2:
        return swing_highs[-2]["timestamp"]
    elif break_type == "BULLISH" and len(swing_lows) >= 2:
        return swing_lows[-2]["timestamp"]

    return None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def is_bullish_structure(structure: MarketStructure) -> bool:
    """Check if structure is bullish (HH & HL)."""
    return structure["structure_state"] == "BULLISH"


def is_bearish_structure(structure: MarketStructure) -> bool:
    """Check if structure is bearish (LL & LH)."""
    return structure["structure_state"] == "BEARISH"


def has_structure_break(structure: MarketStructure) -> bool:
    """Check if structure has been broken."""
    return structure["structure_break"]


def get_structure_break_direction(structure: MarketStructure) -> Optional[str]:
    """Get direction of structure break (BULLISH/BEARISH)."""
    return structure["structure_break_type"]
