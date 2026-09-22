"""
SOCrates V2 Phase 1 — Target Engine (TARGET_V1)

Derives trading targets (entry/exit levels) from all technical engines.

Depends on: SWING_V1, STRUCTURE_V1, FIB_V1, ELLIOTT_V1, CONFLUENCE_V1 outputs

Algorithm: TARGET_V1
- Target derivation from Fibonacci, Elliott Wave, Structure, Socrates
- Target ranking: 1 (nearest), 2 (mid-term), 3 (long-term)
- Distance calculation (% move, ATR multiples)
- Confidence scoring
- Confluence support linkage
"""

from typing import List, Optional
from datetime import datetime

from .types import (
    SwingDetectionOutput,
    MarketStructureOutput,
    FibonacciOutput,
    ElliottWaveOutput,
    ConfluenceOutput,
    TradingTarget,
    TargetOutput,
)


ALGORITHM_VERSION = "TARGET_V1"


# ============================================================================
# TARGET DERIVATION
# ============================================================================

def derive_trading_targets(
    swings: SwingDetectionOutput,
    structure: MarketStructureOutput,
    fibonacci: FibonacciOutput,
    elliott: ElliottWaveOutput,
    confluence: ConfluenceOutput,
    symbol: str,
    timeframe: str,
    current_price: float,
) -> TargetOutput:
    """
    Derive trading targets from all technical engines.

    Algorithm:
    1. Extract candidate prices from each engine (fib levels, elliott targets, structure breaks)
    2. Rank by proximity to current price and confluence support
    3. Assign ranks: 1 (nearest), 2 (mid), 3 (long-term)
    4. Calculate distances (% and ATR)
    5. Determine target type (FIB/ELLIOTT/STRUCTURE/CONFLUENCE/COMPOSITE)
    6. Score confidence based on evidence support

    Args:
        swings: SwingDetectionOutput (for ATR data)
        structure: MarketStructureOutput (structure breaks as targets)
        fibonacci: FibonacciOutput (fib levels as targets)
        elliott: ElliottWaveOutput (wave projections as targets)
        confluence: ConfluenceOutput (high-confluence zones as targets)
        symbol: Trading symbol
        timeframe: Timeframe (1D, 1W, 1M)
        current_price: Current market price

    Returns:
        TargetOutput with ranked trading targets
    """

    candidates: List[TradingTarget] = []

    # Get current ATR for distance calculation
    current_atr = _get_current_atr(swings)

    # Extract Fibonacci targets (retracements + extensions)
    fib_targets = _extract_fib_targets(
        fibonacci, symbol, timeframe, current_price, current_atr
    )
    candidates.extend(fib_targets)

    # Extract Elliott Wave targets (wave projections, invalidation levels)
    elliott_targets = _extract_elliott_targets(
        elliott, symbol, timeframe, current_price, current_atr
    )
    candidates.extend(elliott_targets)

    # Extract Structure targets (break prices, support/resistance)
    structure_targets = _extract_structure_targets(
        structure, symbol, timeframe, current_price, current_atr
    )
    candidates.extend(structure_targets)

    # Extract Confluence targets (high-confluence zones as support/resistance)
    confluence_targets = _extract_confluence_targets(
        confluence, symbol, timeframe, current_price, current_atr
    )
    candidates.extend(confluence_targets)

    # Rank targets by distance and link to confluence
    ranked_targets = _rank_and_link_targets(
        candidates, confluence, current_price
    )

    # Classify high vs medium vs low confidence
    high_confidence = [t for t in ranked_targets if t["confluence_state"] == "HIGH"]
    medium_confidence = [t for t in ranked_targets if t["confluence_state"] == "MEDIUM"]

    return TargetOutput(
        success=True,
        error=None,
        symbol=symbol,
        timeframe=timeframe,
        targets=ranked_targets,
        total_targets=len(ranked_targets),
        high_confidence_targets=len(high_confidence),
        medium_confidence_targets=len(medium_confidence),
    )


def _get_current_atr(swings: SwingDetectionOutput) -> float:
    """Extract current ATR from swings output."""
    if swings.get("swings") and len(swings["swings"]) > 0:
        last_swing = swings["swings"][-1]
        return last_swing.get("atr_at_swing", 1.0)
    return 1.0


def _extract_fib_targets(
    fibonacci: FibonacciOutput,
    symbol: str,
    timeframe: str,
    current_price: float,
    current_atr: float,
) -> List[TradingTarget]:
    """Extract Fibonacci levels as trading targets."""

    targets: List[TradingTarget] = []

    # Retracements
    for level in fibonacci.get("retracements", []):
        target_price = level["price"]
        distance_pct = abs(target_price - current_price) / current_price * 100
        distance_atr = abs(target_price - current_price) / current_atr if current_atr > 0 else 0

        target = TradingTarget(
            symbol=symbol,
            timeframe=timeframe,
            as_of=datetime.utcnow(),
            target_number=0,  # Will be reassigned during ranking
            price=target_price,
            distance_pct=distance_pct,
            distance_atr=distance_atr,
            target_type="FIB",  # type: ignore
            fib_basis=f"{level['level']}% retracement",
            elliott_basis=None,
            structure_basis=None,
            socrates_basis=None,
            confluence_state="LOW",  # type: ignore
            confluence_reasons=[],
            algorithm_version=ALGORITHM_VERSION,  # type: ignore
            created_at=datetime.utcnow(),
        )
        targets.append(target)

    # Extensions
    for level in fibonacci.get("extensions", []):
        target_price = level["price"]
        distance_pct = abs(target_price - current_price) / current_price * 100
        distance_atr = abs(target_price - current_price) / current_atr if current_atr > 0 else 0

        target = TradingTarget(
            symbol=symbol,
            timeframe=timeframe,
            as_of=datetime.utcnow(),
            target_number=0,
            price=target_price,
            distance_pct=distance_pct,
            distance_atr=distance_atr,
            target_type="FIB",  # type: ignore
            fib_basis=f"{level['level']}% extension",
            elliott_basis=None,
            structure_basis=None,
            socrates_basis=None,
            confluence_state="LOW",  # type: ignore
            confluence_reasons=[],
            algorithm_version=ALGORITHM_VERSION,  # type: ignore
            created_at=datetime.utcnow(),
        )
        targets.append(target)

    return targets


def _extract_elliott_targets(
    elliott: ElliottWaveOutput,
    symbol: str,
    timeframe: str,
    current_price: float,
    current_atr: float,
) -> List[TradingTarget]:
    """Extract Elliott Wave targets (invalidation levels, wave projections)."""

    targets: List[TradingTarget] = []

    # Use primary count if available
    primary = elliott.get("primary_count")
    if primary:
        invalidation_price = primary.get("invalidation_price")
        if invalidation_price:
            distance_pct = abs(invalidation_price - current_price) / current_price * 100
            distance_atr = abs(invalidation_price - current_price) / current_atr if current_atr > 0 else 0

            target = TradingTarget(
                symbol=symbol,
                timeframe=timeframe,
                as_of=datetime.utcnow(),
                target_number=0,
                price=invalidation_price,
                distance_pct=distance_pct,
                distance_atr=distance_atr,
                target_type="ELLIOTT",  # type: ignore
                fib_basis=None,
                elliott_basis=f"{primary['pattern_type']} invalidation",
                structure_basis=None,
                socrates_basis=None,
                confluence_state="LOW",  # type: ignore
                confluence_reasons=[],
                algorithm_version=ALGORITHM_VERSION,  # type: ignore
                created_at=datetime.utcnow(),
            )
            targets.append(target)

    return targets


def _extract_structure_targets(
    structure: MarketStructureOutput,
    symbol: str,
    timeframe: str,
    current_price: float,
    current_atr: float,
) -> List[TradingTarget]:
    """Extract Structure targets (break prices, support/resistance)."""

    targets: List[TradingTarget] = []

    struct = structure.get("structure", {})
    break_price = struct.get("structure_break_price")

    if break_price:
        distance_pct = abs(break_price - current_price) / current_price * 100
        distance_atr = abs(break_price - current_price) / current_atr if current_atr > 0 else 0

        target = TradingTarget(
            symbol=symbol,
            timeframe=timeframe,
            as_of=datetime.utcnow(),
            target_number=0,
            price=break_price,
            distance_pct=distance_pct,
            distance_atr=distance_atr,
            target_type="STRUCTURE",  # type: ignore
            fib_basis=None,
            elliott_basis=None,
            structure_basis="Structure break level",
            socrates_basis=None,
            confluence_state="LOW",  # type: ignore
            confluence_reasons=[],
            algorithm_version=ALGORITHM_VERSION,  # type: ignore
            created_at=datetime.utcnow(),
        )
        targets.append(target)

    return targets


def _extract_confluence_targets(
    confluence: ConfluenceOutput,
    symbol: str,
    timeframe: str,
    current_price: float,
    current_atr: float,
) -> List[TradingTarget]:
    """Extract Confluence zones as high-probability targets."""

    targets: List[TradingTarget] = []

    # High-confluence zones as primary targets
    for zone in confluence.get("zones", []):
        if zone["confluence_state"] in ["HIGH", "MEDIUM"]:
            zone_mid = zone["zone_midpoint"]
            distance_pct = abs(zone_mid - current_price) / current_price * 100
            distance_atr = abs(zone_mid - current_price) / current_atr if current_atr > 0 else 0

            target = TradingTarget(
                symbol=symbol,
                timeframe=timeframe,
                as_of=datetime.utcnow(),
                target_number=0,
                price=zone_mid,
                distance_pct=distance_pct,
                distance_atr=distance_atr,
                target_type="COMPOSITE",  # type: ignore
                fib_basis=None,
                elliott_basis=None,
                structure_basis=None,
                socrates_basis=None,
                confluence_state=zone["confluence_state"],  # type: ignore
                confluence_reasons=zone["evidence_list"],
                algorithm_version=ALGORITHM_VERSION,  # type: ignore
                created_at=datetime.utcnow(),
            )
            targets.append(target)

    return targets


def _rank_and_link_targets(
    candidates: List[TradingTarget],
    confluence: ConfluenceOutput,
    current_price: float,
) -> List[TradingTarget]:
    """
    Rank targets by proximity and link to confluence zones.

    Target ranking:
    - Rank 1: Nearest (closest distance)
    - Rank 2: Mid-term (intermediate distance)
    - Rank 3: Long-term (farthest distance)
    """

    if not candidates:
        return []

    # Sort by distance
    sorted_targets = sorted(candidates, key=lambda t: t["distance_pct"])

    # Assign ranks
    ranked = []
    for i, target in enumerate(sorted_targets):
        if i < len(sorted_targets) // 3:
            target_number = 1
        elif i < (2 * len(sorted_targets)) // 3:
            target_number = 2
        else:
            target_number = 3

        target_copy = dict(target)
        target_copy["target_number"] = target_number

        # Link to confluence zone if available
        if target["confluence_state"] == "LOW":
            for zone in confluence.get("zones", []):
                if zone["zone_low"] <= target["price"] <= zone["zone_high"]:
                    target_copy["confluence_state"] = zone["confluence_state"]  # type: ignore
                    target_copy["confluence_reasons"] = zone["evidence_list"]
                    break

        ranked.append(target_copy)

    return ranked


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_nearest_target(targets: List[TradingTarget]) -> Optional[TradingTarget]:
    """Get the nearest trading target (rank 1)."""
    rank_1 = [t for t in targets if t["target_number"] == 1]
    return rank_1[0] if rank_1 else None


def get_mid_term_targets(targets: List[TradingTarget]) -> List[TradingTarget]:
    """Get mid-term targets (rank 2)."""
    return [t for t in targets if t["target_number"] == 2]


def get_long_term_targets(targets: List[TradingTarget]) -> List[TradingTarget]:
    """Get long-term targets (rank 3)."""
    return [t for t in targets if t["target_number"] == 3]


def filter_high_confidence_targets(targets: List[TradingTarget]) -> List[TradingTarget]:
    """Get targets with HIGH confluence support."""
    return [t for t in targets if t["confluence_state"] == "HIGH"]


def get_targets_by_type(
    targets: List[TradingTarget],
    target_type: str,  # FIB, ELLIOTT, STRUCTURE, COMPOSITE
) -> List[TradingTarget]:
    """Filter targets by type."""
    return [t for t in targets if t["target_type"] == target_type]
