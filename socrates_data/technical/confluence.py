"""
SOCrates V2 Phase 1 — Confluence Engine (CONFLUENCE_V1)

Aggregates evidence from multiple technical indicators (Structure, Fibonacci, Elliott)
to identify high-confluence price zones where multiple signals align.

Depends on: STRUCTURE_V1, FIB_V1, ELLIOTT_V1 outputs

Algorithm: CONFLUENCE_V1
- Zone generation: Identify price areas where 2+ indicators converge
- Evidence tracking: Which sources support each zone
- Confluence scoring: HIGH (4+), MEDIUM (2-3), LOW (1)
- Zone boundaries: Low/high prices with zone width calculation
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from .types import (
    MarketStructureOutput,
    FibonacciOutput,
    ElliottWaveOutput,
    ConfluenceZone,
    ConfluenceOutput,
)


ALGORITHM_VERSION = "CONFLUENCE_V1"

# Zone width tolerance (in price pips for matching nearby levels)
ZONE_WIDTH_TOLERANCE = 2.0


# ============================================================================
# CONFLUENCE ZONE GENERATION
# ============================================================================

def calculate_confluence_zones(
    structure: MarketStructureOutput,
    fibonacci: FibonacciOutput,
    elliott: ElliottWaveOutput,
    symbol: str,
    timeframe: str,
    current_price: float,
) -> ConfluenceOutput:
    """
    Identify price zones where multiple technical indicators converge.

    Algorithm:
    1. Extract support/resistance levels from each engine
    2. Group nearby levels into zones (within tolerance)
    3. Track evidence sources per zone
    4. Classify confluence state (HIGH/MEDIUM/LOW)
    5. Calculate zone statistics

    Args:
        structure: MarketStructureOutput (structure breaks, support/resistance)
        fibonacci: FibonacciOutput (fib retracements, extensions, projections)
        elliott: ElliottWaveOutput (wave targets, invalidation levels)
        symbol: Trading symbol
        timeframe: Timeframe (1D, 1W, 1M)
        current_price: Current market price

    Returns:
        ConfluenceOutput with zone list and statistics
    """

    # Collect all candidate prices from all sources
    candidate_prices = []

    # Structure evidence: break price, support/resistance levels
    struct_data = structure.get("structure", {})
    if struct_data.get("structure_break_price"):
        candidate_prices.append({
            "price": struct_data["structure_break_price"],
            "source": "structure_break",
            "type": "STRUCTURE",
        })

    # Fibonacci evidence: all levels from output
    for level in fibonacci.get("retracements", []):
        candidate_prices.append({
            "price": level["price"],
            "source": f"fib_{level['level']}_retrace",
            "type": "FIB",
        })

    for level in fibonacci.get("extensions", []):
        candidate_prices.append({
            "price": level["price"],
            "source": f"fib_{level['level']}_ext",
            "type": "FIB",
        })

    for level in fibonacci.get("projections", []):
        candidate_prices.append({
            "price": level["price"],
            "source": f"fib_projection_{level['level']}",
            "type": "FIB",
        })

    # Elliott evidence: invalidation prices and wave targets
    for candidate in elliott.get("impulse_candidates", []) + elliott.get("correction_candidates", []):
        if candidate.get("invalidation_price"):
            candidate_prices.append({
                "price": candidate["invalidation_price"],
                "source": f"elliott_{candidate['pattern_type']}_invalidation",
                "type": "ELLIOTT",
            })

    # Group prices into zones
    if not candidate_prices:
        return ConfluenceOutput(
            success=True,
            error=None,
            symbol=symbol,
            timeframe=timeframe,
            zones=[],
            high_confluence_zones=0,
            medium_confluence_zones=0,
            low_confluence_zones=0,
        )

    zones = _group_prices_into_zones(
        candidate_prices, symbol, timeframe, ZONE_WIDTH_TOLERANCE
    )

    # Classify confluence levels
    high_zones = [z for z in zones if z["confluence_state"] == "HIGH"]
    medium_zones = [z for z in zones if z["confluence_state"] == "MEDIUM"]
    low_zones = [z for z in zones if z["confluence_state"] == "LOW"]

    return ConfluenceOutput(
        success=True,
        error=None,
        symbol=symbol,
        timeframe=timeframe,
        zones=zones,
        high_confluence_zones=len(high_zones),
        medium_confluence_zones=len(medium_zones),
        low_confluence_zones=len(low_zones),
    )


def _group_prices_into_zones(
    prices: List[Dict[str, Any]],
    symbol: str,
    timeframe: str,
    tolerance: float,
) -> List[ConfluenceZone]:
    """
    Group prices that are close together into zones.

    Returns list of ConfluenceZone objects with evidence tracking.
    """

    if not prices:
        return []

    # Sort by price
    sorted_prices = sorted(prices, key=lambda x: x["price"])

    zones: List[ConfluenceZone] = []
    current_zone_prices: List[Dict[str, Any]] = []

    for price_obj in sorted_prices:
        if not current_zone_prices:
            current_zone_prices.append(price_obj)
        else:
            # Check if price is within tolerance of zone
            zone_low = min(p["price"] for p in current_zone_prices)
            zone_high = max(p["price"] for p in current_zone_prices)
            zone_width = zone_high - zone_low

            if price_obj["price"] - zone_high <= tolerance:
                # Add to current zone
                current_zone_prices.append(price_obj)
            else:
                # Close current zone and start new one
                zone = _create_zone_from_prices(
                    current_zone_prices, symbol, timeframe
                )
                zones.append(zone)
                current_zone_prices = [price_obj]

    # Close final zone
    if current_zone_prices:
        zone = _create_zone_from_prices(current_zone_prices, symbol, timeframe)
        zones.append(zone)

    return zones


def _create_zone_from_prices(
    prices: List[Dict[str, Any]],
    symbol: str,
    timeframe: str,
) -> ConfluenceZone:
    """Create a single ConfluenceZone from a group of prices."""

    price_values = [p["price"] for p in prices]
    zone_low = min(price_values)
    zone_high = max(price_values)
    zone_midpoint = (zone_low + zone_high) / 2

    if zone_midpoint > 0:
        zone_width_pct = ((zone_high - zone_low) / zone_midpoint) * 100
    else:
        zone_width_pct = 0.0

    # Identify evidence sources
    sources = set(p["source"] for p in prices)
    types = set(p["type"] for p in prices)
    evidence_count = len(types)

    # Classify confluence state
    if evidence_count >= 4:
        confluence_state = "HIGH"
    elif evidence_count >= 2:
        confluence_state = "MEDIUM"
    else:
        confluence_state = "LOW"

    return ConfluenceZone(
        symbol=symbol,
        timeframe=timeframe,
        as_of=datetime.utcnow(),
        zone_low=zone_low,
        zone_high=zone_high,
        zone_midpoint=zone_midpoint,
        zone_width_pct=zone_width_pct,
        has_structure_support="STRUCTURE" in types,
        has_fibonacci_support="FIB" in types,
        has_elliott_support="ELLIOTT" in types,
        has_socrates_support=False,  # Future: add Socrates data
        evidence_count=evidence_count,
        evidence_list=sorted(list(sources)),
        confluence_state=confluence_state,  # type: ignore
        algorithm_version=ALGORITHM_VERSION,  # type: ignore
        created_at=datetime.utcnow(),
    )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_high_confluence_zones(zones: List[ConfluenceZone]) -> List[ConfluenceZone]:
    """Filter zones with HIGH confluence."""
    return [z for z in zones if z["confluence_state"] == "HIGH"]


def get_medium_confluence_zones(zones: List[ConfluenceZone]) -> List[ConfluenceZone]:
    """Filter zones with MEDIUM confluence."""
    return [z for z in zones if z["confluence_state"] == "MEDIUM"]


def get_low_confluence_zones(zones: List[ConfluenceZone]) -> List[ConfluenceZone]:
    """Filter zones with LOW confluence."""
    return [z for z in zones if z["confluence_state"] == "LOW"]


def get_nearest_zone_below(
    zones: List[ConfluenceZone],
    current_price: float,
) -> Optional[ConfluenceZone]:
    """Get the nearest confluence zone below current price."""
    below = [z for z in zones if z["zone_high"] < current_price]
    return max(below, key=lambda x: x["zone_high"]) if below else None


def get_nearest_zone_above(
    zones: List[ConfluenceZone],
    current_price: float,
) -> Optional[ConfluenceZone]:
    """Get the nearest confluence zone above current price."""
    above = [z for z in zones if z["zone_low"] > current_price]
    return min(above, key=lambda x: x["zone_low"]) if above else None


def has_multiple_evidence_sources(zone: ConfluenceZone) -> bool:
    """Check if zone has support from multiple indicator types."""
    return zone["evidence_count"] >= 2


def get_zone_width(zone: ConfluenceZone) -> float:
    """Get the width of a zone in price points."""
    return zone["zone_high"] - zone["zone_low"]
