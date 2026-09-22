"""
SOCrates V2 Phase 1 — Shared Type Definitions

All engines use these TypedDicts to ensure consistent data structures
across the technical analysis pipeline.

Algorithm versioning is immutable — once a calculation is made with SWING_V1,
it is labeled SWING_V1 forever. This enables historical reproducibility.
"""

from typing import TypedDict, Literal, Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# OHLCV Input Format
# ============================================================================

class OHLCV(TypedDict):
    """Market bar data (Open, High, Low, Close, Volume)."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


# ============================================================================
# SWING DETECTION OUTPUT
# ============================================================================

class SwingPoint(TypedDict):
    """A single swing high or low with quantitative metrics."""
    symbol: str
    timeframe: Literal["1D", "1W", "1M"]
    timestamp: datetime
    price: float
    swing_type: Literal["HIGH", "LOW"]
    bar_index: int

    # ATR & Movement Metrics
    atr_at_swing: float  # ATR value at time of swing
    move_from_previous_swing: float  # Absolute price distance
    move_pct: float  # % move from previous swing
    move_atr: float  # Move expressed as multiple of ATR

    # Significance Classification
    significance: Literal["MINOR", "INTERMEDIATE", "MAJOR"]
    # MINOR: move_atr < 1.5, INTERMEDIATE: 1.5-3.5, MAJOR: > 3.5

    # Previous Swing Reference
    previous_swing_id: Optional[str]  # Foreign key to prior swing

    # Algorithm Versioning
    algorithm_version: Literal["SWING_V1"]

    # Metadata
    created_at: datetime


class SwingDetectionOutput(TypedDict):
    """Output from Swing Detection Engine."""
    success: bool
    error: Optional[str]
    symbol: str
    timeframe: Literal["1D", "1W", "1M"]

    swings: List[SwingPoint]

    # Statistics
    total_bars_analyzed: int
    total_swings_found: int
    minor_swings: int
    intermediate_swings: int
    major_swings: int

    last_swing_time: Optional[datetime]
    last_swing_price: Optional[float]


# ============================================================================
# MARKET STRUCTURE OUTPUT
# ============================================================================

class StructurePoint(TypedDict):
    """High or low point in the structure sequence."""
    price: float
    timestamp: datetime
    swing_type: Literal["HIGH", "LOW"]


class MarketStructure(TypedDict):
    """Current market structure state with HH/HL/LH/LL pattern analysis."""
    symbol: str
    timeframe: Literal["1D", "1W", "1M"]
    as_of: datetime

    # Structure Classification
    structure_state: Literal[
        "BULLISH",         # Making HH/HL
        "BEARISH",         # Making LL/LH
        "RANGE",           # Oscillating without clear direction
        "TRANSITION",      # Ambiguous; could break either way
        "MIXED",           # Conflicting signals
        "INSUFFICIENT_DATA"
    ]

    # Last 2 Highs (for HH/LH detection)
    last_high: Optional[float]
    last_high_time: Optional[datetime]
    previous_high: Optional[float]
    previous_high_time: Optional[datetime]

    # Last 2 Lows (for HL/LL detection)
    last_low: Optional[float]
    last_low_time: Optional[datetime]
    previous_low: Optional[float]
    previous_low_time: Optional[datetime]

    # Structure Break Detection
    structure_break: bool  # Did structure transition occur?
    structure_break_type: Optional[Literal["BULLISH", "BEARISH"]]
    structure_break_price: Optional[float]
    structure_break_date: Optional[datetime]

    # Algorithm Versioning
    algorithm_version: Literal["STRUCTURE_V1"]

    # Metadata
    created_at: datetime


class MarketStructureOutput(TypedDict):
    """Output from Market Structure Engine."""
    success: bool
    error: Optional[str]
    symbol: str
    timeframe: Literal["1D", "1W", "1M"]

    structure: MarketStructure

    # Summary for quick reference
    is_bullish: bool
    is_bearish: bool
    is_transitioning: bool


# ============================================================================
# FIBONACCI LEVELS OUTPUT
# ============================================================================

class FibonacciLevel(TypedDict):
    """A single Fibonacci retracement, extension, or projection level."""
    symbol: str
    timeframe: Literal["1D", "1W", "1M"]

    # Fibonacci Type
    fib_type: Literal["RETRACEMENT", "EXTENSION", "PROJECTION"]
    direction: Literal["BULLISH", "BEARISH"]
    # BULLISH: upward retracement or upward extension
    # BEARISH: downward retracement or downward extension

    # Anchor Points (price move from which Fib is calculated)
    anchor_high: float
    anchor_high_date: datetime
    anchor_low: float
    anchor_low_date: datetime

    # Level Configuration
    level: float  # E.g., 23.6, 38.2, 50.0, 61.8, 78.6, 100, 127.2, 161.8, 261.8
    price: float  # Calculated level price

    # Source Tracking
    source: Literal["CALCULATED", "SOCRATES", "BOTH"]
    # CALCULATED: from engine's own swing detection
    # SOCRATES: from Socrates platform data
    # BOTH: cross-referenced between sources

    # Algorithm Versioning
    algorithm_version: Literal["FIB_V1"]

    # Metadata
    created_at: datetime


class FibonacciOutput(TypedDict):
    """Output from Fibonacci Engine."""
    success: bool
    error: Optional[str]
    symbol: str
    timeframe: Literal["1D", "1W", "1M"]

    retracements: List[FibonacciLevel]
    extensions: List[FibonacciLevel]
    projections: List[FibonacciLevel]

    # Statistics
    total_levels: int

    # Most relevant level for current price (optional)
    nearest_level_below: Optional[FibonacciLevel]
    nearest_level_above: Optional[FibonacciLevel]


# ============================================================================
# ELLIOTT WAVE CANDIDATES OUTPUT
# ============================================================================

class WaveStructure(TypedDict):
    """Complete Elliott Wave count (primary or alternate)."""
    wave_count: str  # E.g., "5-3-5-3-5" for impulse, "5-3-5" for correction

    # Wave Boundaries (nullable until identified)
    wave_1_start: Optional[float]
    wave_1_end: Optional[float]
    wave_2_end: Optional[float]
    wave_3_end: Optional[float]
    wave_4_end: Optional[float]
    wave_5_end: Optional[float]

    # Wave Relationships (Fibonacci ratios)
    wave_3_vs_1: Optional[float]  # Ratio of wave 3 to wave 1
    wave_5_vs_1: Optional[float]  # Ratio of wave 5 to wave 1
    wave_5_vs_3: Optional[float]  # Ratio of wave 5 to wave 3
    wave_2_vs_1: Optional[float]  # % retracement of wave 1
    wave_4_vs_3: Optional[float]  # % retracement of wave 3

    description: str  # Human-readable count description


class ElliottWaveCandidate(TypedDict):
    """A single Elliott Wave impulse or correction candidate."""
    symbol: str
    timeframe: Literal["1D", "1W", "1M"]

    # Pattern Classification
    pattern_type: Literal["IMPULSE", "CORRECTION"]
    direction: Literal["BULLISH", "BEARISH"]

    # Wave Sequence
    waves: List[SwingPoint]  # List of swings forming this wave pattern
    wave_labels: List[str]  # ["WAVE_1", "WAVE_2", "WAVE_3", "WAVE_4", "WAVE_5"] or ["WAVE_A", "WAVE_B", "WAVE_C"]

    # Quality Metrics
    confidence: float  # 0.0 to 1.0 score based on Fibonacci ratio alignment
    fibonacci_ratios: Dict[str, float]  # Wave ratios (e.g., {"wave_2_to_1": 0.5})

    # Invalidation Logic
    invalidation_price: float  # Price level that invalidates this count
    invalidation_type: Literal["WAVE_2_BREACH", "WAVE_B_BREACH"]

    # Ranking
    primary: bool  # True if this is the primary count

    # Algorithm Versioning
    algorithm_version: Literal["ELLIOTT_V1"]

    # Metadata
    created_at: datetime


class ElliottWaveOutput(TypedDict):
    """Output from Elliott Wave Engine."""
    success: bool
    error: Optional[str]
    symbol: str
    timeframe: Literal["1D", "1W", "1M"]

    # Wave Candidates
    impulse_candidates: List[ElliottWaveCandidate]
    correction_candidates: List[ElliottWaveCandidate]

    # Primary Analysis
    primary_count: Optional[ElliottWaveCandidate]  # Highest confidence candidate
    alternate_count: Optional[ElliottWaveCandidate]  # Second highest confidence

    # Current Wave Phase
    current_phase: Optional[Literal[
        "WAVE_1", "WAVE_2", "WAVE_3", "WAVE_4", "WAVE_5",
        "WAVE_A", "WAVE_B", "WAVE_C"
    ]]

    # Statistics
    total_candidates: int


# ============================================================================
# CONFLUENCE ZONE OUTPUT
# ============================================================================

class ConfluenceZone(TypedDict):
    """A price zone where multiple technical indicators converge."""
    symbol: str
    timeframe: Literal["1D", "1W", "1M"]
    as_of: datetime

    # Zone Boundaries
    zone_low: float
    zone_high: float
    zone_midpoint: float  # (low + high) / 2
    zone_width_pct: float  # (high - low) / midpoint * 100

    # Evidence Sources (which indicators support this zone?)
    has_structure_support: bool
    has_fibonacci_support: bool
    has_elliott_support: bool
    has_socrates_support: bool
    has_sr_support: bool  # Support/Resistance

    evidence_count: int  # Total number of supporting sources
    evidence_list: List[str]  # ["structure_break", "fib_161.8", "elliott_w3_target"]

    # Confluence State Classification
    confluence_state: Literal["HIGH", "MEDIUM", "LOW"]
    # HIGH: 4+ evidence sources, MEDIUM: 2-3, LOW: 1

    # Algorithm Versioning
    algorithm_version: Literal["CONFLUENCE_V1"]

    # Metadata
    created_at: datetime


class ConfluenceOutput(TypedDict):
    """Output from Confluence Engine."""
    success: bool
    error: Optional[str]
    symbol: str
    timeframe: Literal["1D", "1W", "1M"]

    zones: List[ConfluenceZone]

    # Statistics
    high_confluence_zones: int
    medium_confluence_zones: int
    low_confluence_zones: int


# ============================================================================
# TARGET OUTPUT
# ============================================================================

class TradingTarget(TypedDict):
    """A potential price target derived from technical analysis."""
    symbol: str
    timeframe: Literal["1D", "1W", "1M"]
    as_of: datetime

    # Target Ranking
    target_number: int  # 1 (nearest), 2 (mid-term), 3 (long-term)

    # Price & Distance
    price: float
    distance_pct: float  # % from current price to target
    distance_atr: float  # Distance expressed as multiple of ATR

    # Target Origin (what calculation produced this?)
    target_type: Literal["FIB", "ELLIOTT", "STRUCTURE", "SOCRATES", "COMPOSITE"]

    # Supporting Bases (which indicators produced this target?)
    fib_basis: Optional[str]  # E.g., "161.8% extension from $430-$420"
    elliott_basis: Optional[str]  # E.g., "Wave 5 = Wave 1 projection"
    structure_basis: Optional[str]  # E.g., "Previous resistance at $750"
    socrates_basis: Optional[str]  # E.g., "Socrates target"

    # Confluence Support
    confluence_state: Literal["HIGH", "MEDIUM", "LOW"]
    confluence_reasons: List[str]  # Evidence supporting this target

    # Algorithm Versioning
    algorithm_version: Literal["TARGET_V1"]

    # Metadata
    created_at: datetime


class TargetOutput(TypedDict):
    """Output from Target Engine."""
    success: bool
    error: Optional[str]
    symbol: str
    timeframe: Literal["1D", "1W", "1M"]

    targets: List[TradingTarget]

    # Statistics
    total_targets: int
    high_confidence_targets: int
    medium_confidence_targets: int


# ============================================================================
# UNIFIED PIPELINE OUTPUT
# ============================================================================

class TechnicalIntelligenceReport(TypedDict):
    """Complete Phase 1 technical intelligence for one symbol/timeframe."""
    symbol: str
    timeframe: Literal["1D", "1W", "1M"]
    generated_at: datetime

    # All Engine Outputs
    swings: SwingDetectionOutput
    structure: MarketStructureOutput
    fibonacci: FibonacciOutput
    elliott: ElliottWaveOutput
    confluence: ConfluenceOutput
    targets: TargetOutput

    # Overall Pipeline Status
    all_engines_successful: bool
    errors: List[str]

    # Algorithm Versions (metadata)
    algorithm_versions: Dict[str, str]  # {"SWING": "SWING_V1", "STRUCTURE": "STRUCTURE_V1", ...}
