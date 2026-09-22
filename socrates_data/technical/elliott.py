"""
SOCrates V2 Phase 1 — Elliott Wave Engine (ELLIOTT_V1)

Detects Elliott Wave impulse (5-wave) and correction (3-wave) patterns from swings.

Depends on: SWING_V1 output (swing sequence)

Algorithm: ELLIOTT_V1
- Impulse patterns: 5-wave (1-2-3-4-5) with Fibonacci ratio validation
- Correction patterns: 3-wave (A-B-C) and variations (zigzag, flat, triangle)
- Primary count + alternate count with invalidation prices
- Wave phase tracking (WAVE_1, WAVE_2, WAVE_3, WAVE_4, WAVE_5, WAVE_A, WAVE_B, WAVE_C)
- Fibonacci ratio validation between waves
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from .types import (
    SwingPoint,
    ElliottWaveCandidate,
    ElliottWaveOutput,
)


ALGORITHM_VERSION = "ELLIOTT_V1"

# Fibonacci ratios for wave relationships
WAVE_RATIO_RANGES = {
    "wave2_retrace_min": 0.236,  # Wave 2 minimum retracement of Wave 1
    "wave2_retrace_max": 0.786,  # Wave 2 maximum retracement (beyond = invalidated)
    "wave3_extension_min": 1.0,  # Wave 3 at least equal to Wave 1
    "wave3_extension_max": 4.0,  # Wave 3 maximum multiplier
    "wave4_retrace_min": 0.0,    # Wave 4 minimum retracement of Wave 3
    "wave4_retrace_max": 0.5,    # Wave 4 maximum retracement
    "wave5_extension_min": 0.618, # Wave 5 minimum (often equals Wave 1 or is 61.8% of 1-3)
    "wave5_extension_max": 2.0,   # Wave 5 maximum multiplier
}

CORRECTION_RATIO_RANGES = {
    "wave_b_retrace_min": 0.5,    # Wave B minimum retracement of Wave A
    "wave_b_retrace_max": 1.236,  # Wave B maximum (beyond = extended correction)
    "wave_c_extension_min": 0.618, # Wave C minimum extension of Wave A
    "wave_c_extension_max": 2.0,   # Wave C maximum extension
}


# ============================================================================
# ELLIOTT WAVE DETECTION
# ============================================================================

def detect_elliott_waves(
    swings: List[SwingPoint],
    symbol: str,
    timeframe: str,
    fib_data: Optional[Dict[str, Any]] = None,
) -> ElliottWaveOutput:
    """
    Detect Elliott Wave patterns from swing sequence.

    Algorithm:
    1. Validate sufficient data (need at least 3 swings)
    2. Identify potential impulse patterns (5-wave sequences)
    3. Identify potential correction patterns (3-wave sequences)
    4. Validate Fibonacci ratios for each pattern
    5. Rank primary vs alternate counts
    6. Track current wave phase and invalidation levels

    Args:
        swings: List of SwingPoint from SWING_V1
        symbol: Trading symbol
        timeframe: Timeframe (1D, 1W, 1M)
        fib_data: Optional Fibonacci data for wave ratio validation

    Returns:
        ElliottWaveOutput with wave candidates and analysis
    """

    candidates: List[ElliottWaveCandidate] = []

    # Validation
    if len(swings) < 3:
        return ElliottWaveOutput(
            success=True,
            error=None,
            symbol=symbol,
            timeframe=timeframe,
            impulse_candidates=[],
            correction_candidates=[],
            primary_count=None,
            alternate_count=None,
            current_phase=None,
            total_candidates=0,
        )

    # Detect impulse patterns (5-wave sequences)
    impulse_candidates = _detect_impulse_patterns(swings, symbol, timeframe)

    # Detect correction patterns (3-wave sequences)
    correction_candidates = _detect_correction_patterns(swings, symbol, timeframe)

    # Rank candidates by confidence (Fibonacci ratio alignment)
    all_candidates = impulse_candidates + correction_candidates
    ranked = sorted(all_candidates, key=lambda x: x["confidence"], reverse=True)

    # Primary count = highest confidence
    primary = ranked[0] if ranked else None

    # Alternate count = second highest confidence
    alternate = ranked[1] if len(ranked) > 1 else None

    # Determine current wave phase from primary count
    current_phase = None
    if primary:
        waves = primary["waves"]
        if len(waves) == 5:
            current_phase = f"WAVE_{len(waves)}"
        elif len(waves) == 3:
            current_phase = f"WAVE_{len(waves) - 1}"  # WAVE_2 for 3-wave

    return ElliottWaveOutput(
        success=True,
        error=None,
        symbol=symbol,
        timeframe=timeframe,
        impulse_candidates=impulse_candidates,
        correction_candidates=correction_candidates,
        primary_count=primary,
        alternate_count=alternate,
        current_phase=current_phase,
        total_candidates=len(all_candidates),
    )


def _detect_impulse_patterns(
    swings: List[SwingPoint],
    symbol: str,
    timeframe: str,
) -> List[ElliottWaveCandidate]:
    """Detect 5-wave impulse patterns."""

    impulses: List[ElliottWaveCandidate] = []

    # Scan all possible 5-swing sequences
    for i in range(len(swings) - 4):
        wave_1 = swings[i]
        wave_2 = swings[i + 1]
        wave_3 = swings[i + 2]
        wave_4 = swings[i + 3]
        wave_5 = swings[i + 4]

        # Validate impulse pattern
        is_valid, confidence, ratios = _validate_impulse_ratios(
            wave_1, wave_2, wave_3, wave_4, wave_5
        )

        if is_valid:
            # Determine direction (up or down)
            direction = "BULLISH" if wave_1["price"] < wave_5["price"] else "BEARISH"

            # Calculate invalidation price (Wave 2 low for bullish impulse)
            if direction == "BULLISH":
                invalidation_price = min(wave_1["price"], wave_2["price"])
            else:
                invalidation_price = max(wave_1["price"], wave_2["price"])

            impulse = ElliottWaveCandidate(
                symbol=symbol,
                timeframe=timeframe,
                pattern_type="IMPULSE",  # type: ignore
                direction=direction,  # type: ignore
                waves=[wave_1, wave_2, wave_3, wave_4, wave_5],
                wave_labels=["WAVE_1", "WAVE_2", "WAVE_3", "WAVE_4", "WAVE_5"],
                confidence=confidence,
                fibonacci_ratios=ratios,
                invalidation_price=invalidation_price,
                invalidation_type="WAVE_2_BREACH" if direction == "BULLISH" else "WAVE_2_BREACH",  # type: ignore
                primary=True if i == len(swings) - 5 else False,
                algorithm_version=ALGORITHM_VERSION,  # type: ignore
                created_at=datetime.utcnow(),
            )
            impulses.append(impulse)

    return impulses


def _detect_correction_patterns(
    swings: List[SwingPoint],
    symbol: str,
    timeframe: str,
) -> List[ElliottWaveCandidate]:
    """Detect 3-wave correction patterns."""

    corrections: List[ElliottWaveCandidate] = []

    # Scan all possible 3-swing sequences
    for i in range(len(swings) - 2):
        wave_a = swings[i]
        wave_b = swings[i + 1]
        wave_c = swings[i + 2]

        # Validate correction pattern
        is_valid, confidence, ratios = _validate_correction_ratios(
            wave_a, wave_b, wave_c
        )

        if is_valid:
            # Determine direction (opposite of correction movement)
            direction = "BEARISH" if wave_a["price"] < wave_c["price"] else "BULLISH"

            # Calculate invalidation price (Wave B high for bearish correction)
            invalidation_price = max(wave_a["price"], wave_b["price"])

            correction = ElliottWaveCandidate(
                symbol=symbol,
                timeframe=timeframe,
                pattern_type="CORRECTION",  # type: ignore
                direction=direction,  # type: ignore
                waves=[wave_a, wave_b, wave_c],
                wave_labels=["WAVE_A", "WAVE_B", "WAVE_C"],
                confidence=confidence,
                fibonacci_ratios=ratios,
                invalidation_price=invalidation_price,
                invalidation_type="WAVE_B_BREACH",  # type: ignore
                primary=True if i == len(swings) - 3 else False,
                algorithm_version=ALGORITHM_VERSION,  # type: ignore
                created_at=datetime.utcnow(),
            )
            corrections.append(correction)

    return corrections


def _validate_impulse_ratios(
    w1: SwingPoint, w2: SwingPoint, w3: SwingPoint, w4: SwingPoint, w5: SwingPoint
) -> tuple[bool, float, dict]:
    """
    Validate impulse pattern Fibonacci ratios.
    
    Returns: (is_valid, confidence_score, ratios_dict)
    """

    # Calculate moves
    move_1 = abs(w2["price"] - w1["price"])
    move_2 = abs(w3["price"] - w2["price"])
    move_3 = abs(w4["price"] - w3["price"])
    move_4 = abs(w5["price"] - w4["price"])

    ratios = {
        "wave_2_to_1": move_2 / move_1 if move_1 > 0 else 0,
        "wave_3_to_1": move_3 / move_1 if move_1 > 0 else 0,
        "wave_4_to_3": move_4 / move_3 if move_3 > 0 else 0,
        "wave_5_to_1": move_4 / move_1 if move_1 > 0 else 0,
    }

    # Check wave 2 retracement (should not exceed 78.6% of wave 1)
    if move_1 > 0:
        wave_2_retrace = move_2 / move_1
        if wave_2_retrace > WAVE_RATIO_RANGES["wave2_retrace_max"]:
            return False, 0.0, ratios

    # Check wave 3 extension (should be > wave 1)
    if move_3 <= move_1:
        return False, 0.0, ratios

    # Check wave 4 retracement (should not exceed 50% of wave 3)
    if move_3 > 0:
        wave_4_retrace = move_4 / move_3
        if wave_4_retrace > WAVE_RATIO_RANGES["wave4_retrace_max"]:
            return False, 0.0, ratios

    # Valid impulse — calculate confidence based on how well ratios align
    confidence = _calculate_impulse_confidence(ratios)

    return True, confidence, ratios


def _validate_correction_ratios(
    wa: SwingPoint, wb: SwingPoint, wc: SwingPoint
) -> tuple[bool, float, dict]:
    """
    Validate correction pattern Fibonacci ratios.
    
    Returns: (is_valid, confidence_score, ratios_dict)
    """

    # Calculate moves
    move_a = abs(wb["price"] - wa["price"])
    move_b = abs(wc["price"] - wb["price"])

    ratios = {
        "wave_b_to_a": move_b / move_a if move_a > 0 else 0,
        "wave_c_to_a": move_b / move_a if move_a > 0 else 0,
    }

    # Check wave B retracement (typically 50-123.6% of wave A)
    if move_a > 0:
        wave_b_retrace = move_b / move_a
        if wave_b_retrace < CORRECTION_RATIO_RANGES["wave_b_retrace_min"]:
            return False, 0.0, ratios

    # Valid correction — calculate confidence
    confidence = _calculate_correction_confidence(ratios)

    return True, confidence, ratios


def _calculate_impulse_confidence(ratios: dict) -> float:
    """Calculate confidence score for impulse pattern (0.0 to 1.0)."""

    score = 0.0

    # Perfect wave 2 retracement (38.2-61.8%)
    wave_2_ratio = ratios.get("wave_2_to_1", 0)
    if 0.382 <= wave_2_ratio <= 0.618:
        score += 0.3
    elif 0.236 <= wave_2_ratio <= 0.786:
        score += 0.15

    # Wave 3 extension (1.618x wave 1 is perfect)
    wave_3_ratio = ratios.get("wave_3_to_1", 0)
    if 1.0 <= wave_3_ratio <= 2.0:
        score += 0.3
    elif 0.5 <= wave_3_ratio <= 4.0:
        score += 0.15

    # Wave 5 extension (often equals wave 1 or is 61.8% of 1-3)
    wave_5_ratio = ratios.get("wave_5_to_1", 0)
    if 0.618 <= wave_5_ratio <= 1.618:
        score += 0.2
    elif 0.5 <= wave_5_ratio <= 2.0:
        score += 0.1

    # Baseline for valid pattern
    score += 0.25

    return min(score, 1.0)


def _calculate_correction_confidence(ratios: dict) -> float:
    """Calculate confidence score for correction pattern (0.0 to 1.0)."""

    score = 0.0

    # Wave B retracement (50-123.6% is typical)
    wave_b_ratio = ratios.get("wave_b_to_a", 0)
    if 0.5 <= wave_b_ratio <= 0.786:
        score += 0.4
    elif 0.382 <= wave_b_ratio <= 1.236:
        score += 0.2

    # Wave C extension (typically equals wave A or extends)
    wave_c_ratio = ratios.get("wave_c_to_a", 0)
    if 0.618 <= wave_c_ratio <= 1.618:
        score += 0.35

    # Baseline for valid pattern
    score += 0.25

    return min(score, 1.0)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def is_impulse_pattern(candidate: ElliottWaveCandidate) -> bool:
    """Check if candidate is an impulse pattern."""
    return candidate["pattern_type"] == "IMPULSE"


def is_correction_pattern(candidate: ElliottWaveCandidate) -> bool:
    """Check if candidate is a correction pattern."""
    return candidate["pattern_type"] == "CORRECTION"


def is_bullish_wave(candidate: ElliottWaveCandidate) -> bool:
    """Check if wave is bullish."""
    return candidate["direction"] == "BULLISH"


def is_bearish_wave(candidate: ElliottWaveCandidate) -> bool:
    """Check if wave is bearish."""
    return candidate["direction"] == "BEARISH"


def get_invalidation_level(candidate: ElliottWaveCandidate) -> Optional[float]:
    """Get invalidation price for wave count."""
    return candidate.get("invalidation_price")


def filter_candidates_by_confidence(
    candidates: List[ElliottWaveCandidate],
    min_confidence: float = 0.5,
) -> List[ElliottWaveCandidate]:
    """Filter wave candidates by minimum confidence threshold."""
    return [c for c in candidates if c["confidence"] >= min_confidence]


def get_highest_confidence_candidate(
    candidates: List[ElliottWaveCandidate],
) -> Optional[ElliottWaveCandidate]:
    """Get the highest-confidence wave candidate."""
    return max(candidates, key=lambda x: x["confidence"]) if candidates else None


def get_wave_label(candidate: ElliottWaveCandidate, wave_index: int) -> str:
    """Get the label for a specific wave in a candidate."""
    labels = candidate.get("wave_labels", [])
    return labels[wave_index] if wave_index < len(labels) else "UNKNOWN"
