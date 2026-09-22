# SOCrates V2 Phase 1 — Technical Intelligence Foundation

## Architecture Diagram: Data Flow & Dependencies

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MARKET DATA INPUT                             │
│              (OHLCV bars from market_data.py)                        │
│              Timeframes: 1D, 1W, 1M (independent)                    │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │   SWING DETECTION ENGINE (V1)      │  ← CANONICAL SOURCE
        │  (swings.py)                       │
        ├────────────────────────────────────┤
        │ Input:  bars[] + ATR               │
        │ Output: swing_highs[], swing_lows[]│
        │         significance (MINOR/INT/MAJ)
        │         algorithm_version: SWING_V1│
        │ Store:  market_swings table        │
        │         (immutable, version-tagged)│
        └──┬─────────────────────────────────┘
           │
      ┌────┴──────────────────────────────────────┐
      │                                             │
      ▼                                             ▼
┌──────────────────────┐              ┌──────────────────────────┐
│ MARKET STRUCTURE (V1)│              │  FIBONACCI ENGINE (V1)   │
│ (structure.py)       │              │  (fibonacci.py)          │
├──────────────────────┤              ├──────────────────────────┤
│ Input:  swings[]     │              │ Input:  swings[]         │
│ Output: BULLISH      │              │         structure (opt)  │
│         BEARISH      │              │ Output: retracements[]   │
│         RANGE        │              │         extensions[]     │
│         TRANSITION   │              │         projections[]    │
│ Store:  market_      │              │ Source: CALCULATED/      │
│         structure tbl│              │         SOCRATES/BOTH    │
│                      │              │ Store:  fibonacci_levels │
└──────┬───────────────┘              │         table            │
       │                              └──────────┬────────────────┘
       │                                         │
       │                 ┌───────────────────────┘
       │                 │
       │                 ▼
       │        ┌────────────────────────┐
       │        │  ELLIOTT WAVE (V1)     │
       │        │  (elliott.py)          │
       │        ├────────────────────────┤
       │        │ Input:  swings[]       │
       │        │         structure      │
       │        │         fibonacci      │
       │        │ Output: IMPULSE cands  │
       │        │         CORRECT cands  │
       │        │         phase tracking │
       │        │ Store:  elliott_counts │
       │        │         table          │
       └────────┤                        │
                └────────┬───────────────┘
                         │
                         ▼
                ┌────────────────────────┐
                │ CONFLUENCE ENGINE (V1) │
                │ (confluence.py)        │
                ├────────────────────────┤
                │ Input:  structure      │
                │         fibonacci      │
                │         elliott        │
                │ Output: zones[]        │
                │         evidence[]     │
                │         HIGH/MED/LOW   │
                │ Store:  technical_     │
                │         confluence tbl │
                └────────┬───────────────┘
                         │
                         ▼
                ┌────────────────────────┐
                │  TARGET ENGINE (V1)    │
                │  (targets.py)          │
                ├────────────────────────┤
                │ Input:  structure      │
                │         fibonacci      │
                │         elliott        │
                │         confluence     │
                │ Output: targets[]      │
                │         distance_pct   │
                │         distance_atr   │
                │ Store:  technical_     │
                │         targets table  │
                └────────┬───────────────┘
                         │
                         ▼
                ┌────────────────────────┐
                │  PIPELINE ORCHESTRATOR │
                │  (technical_pipeline)  │
                ├────────────────────────┤
                │ Calls all engines in   │
                │ dependency order       │
                │ Returns unified report │
                │ Pushes to Supabase     │
                └────────────────────────┘
```

## Engine Dependencies & Calling Order

```
1. SWING DETECTION (no deps)
   ↓
2. MARKET STRUCTURE (depends on SWINGS)
   ↓ ↘
3. ├→ FIBONACCI (depends on SWINGS)
   │
   ├→ ELLIOTT (depends on SWINGS, STRUCTURE, FIBONACCI)
   │
4. CONFLUENCE (depends on STRUCTURE, FIBONACCI, ELLIOTT)
   ↓
5. TARGETS (depends on STRUCTURE, FIBONACCI, ELLIOTT, CONFLUENCE)
   ↓
6. PIPELINE OUTPUT (all results collected & versioned)
```

## Module Structure

```
socrates_data/technical/
├── __init__.py                      # Exports all engines
├── types.py                         # Shared TypedDicts/dataclasses
├── swings.py                        # Swing Detection Engine
├── market_structure.py              # Market Structure Engine
├── fibonacci.py                     # Fibonacci Engine
├── elliott.py                       # Elliott Wave Engine
├── confluence.py                    # Confluence Engine
├── targets.py                       # Target Engine
├── technical_pipeline.py            # Orchestrator
├── supabase_migrations.sql          # Schema definitions
├── tests/
│   ├── __init__.py
│   ├── test_swings.py               # Unit tests for SWING_V1
│   ├── test_structure.py            # Unit tests for STRUCTURE_V1
│   ├── test_fibonacci.py            # Unit tests for FIB_V1
│   ├── test_elliott.py              # Unit tests for ELLIOTT_V1
│   ├── test_confluence.py           # Unit tests for CONFLUENCE_V1
│   ├── test_targets.py              # Unit tests for TARGET_V1
│   ├── fixtures/
│   │   ├── sample_ohlcv.py          # Synthetic OHLCV data
│   │   ├── sample_swings.py         # Pre-calculated swings
│   │   └── socrates_samples.py      # Real Socrates data
│   └── integration/
│       └── test_full_pipeline.py    # End-to-end tests
└── README.md                        # Documentation
```

## Algorithm Versioning Strategy

Every engine output carries an immutable `algorithm_version` field:
- `SWING_V1` — initial swing detection thresholds & ATR normalization
- `STRUCTURE_V1` — HH/HL/LH/LL pattern analysis
- `FIB_V1` — retracement/extension/projection calculations
- `ELLIOTT_V1` — impulse/correction candidates & Fibonacci relationships
- `CONFLUENCE_V1` — evidence aggregation logic
- `TARGET_V1` — target derivation & distance calculations

**Purpose:**
- Historical reproducibility (can recalculate any past analysis with SWING_V1 thresholds even after upgrading to SWING_V2)
- Audit trail for tuning decisions
- A/B testing of algorithm improvements
- Deterministic backtesting

**Implementation:**
- Every calculation function returns `{..., algorithm_version: 'ENGINE_V1'}`
- Database stores immutable historical rows (never overwrites, only appends)
- Pipeline tags all outputs with version at creation time

## Data Immutability Pattern

```
market_prices (raw, immutable)
    ↓ (never directly modified)
    └─→ market_swings (v1)
    └─→ market_structure (v1)
    └─→ fibonacci_levels (v1)
    └─→ elliott_counts (v1)
    └─→ technical_confluence (v1)
    └─→ technical_targets (v1)

When upgrading to V2:
    market_prices (unchanged)
    ├─→ market_swings (v1) — archived but readable
    ├─→ market_swings (v2) — new rows added
    ├─→ market_structure (v1) — archived
    ├─→ market_structure (v2) — new rows added
    └─ ... (all engines maintain separate v1 & v2 rows)

Backtesting query: SELECT * FROM market_swings WHERE algorithm_version='SWING_V1'
```

## Phase 1 Test Coverage Strategy

**Each engine must pass:**
1. **Unit tests** — isolated logic with synthetic inputs
2. **Integration tests** — with outputs from upstream engines
3. **Regression tests** — against known reference data (Socrates samples)
4. **Edge case tests** — insufficient data, gaps, extreme volatility, flat markets
5. **Determinism tests** — same input always produces same output

**Test data sources:**
- Synthetic OHLCV (generated with known swings for controlled testing)
- Real historical QQQ/SPY/DXY (from market_data.py)
- Socrates reference output (for validation against platform)

## Supabase Table Definitions

See `supabase_migrations.sql` for complete schema.

**Key characteristics:**
- Partitioning by symbol + timeframe for query performance
- Version tags on all calculated rows for historical tracking
- Foreign keys linking child tables to parent swings (ensures consistency)
- Read-only views for common queries (e.g., `v_latest_swings`, `v_latest_structure`)

## CLI Interface (Entry Point)

```bash
python -m socrates_data.technical.technical_pipeline \
  --symbol QQQ \
  --timeframe 1D \
  --output json \
  --push-to-supabase false

# Output:
# {
#   "success": true,
#   "symbol": "QQQ",
#   "timeframe": "1D",
#   "swings": {...},
#   "structure": {...},
#   "fibonacci": {...},
#   "elliott": {...},
#   "confluence": {...},
#   "targets": {...}
# }
```

## Next Steps (Implementation Order)

1. ✅ Architecture Diagram (this file)
2. ⬜ types.py — Shared type definitions
3. ⬜ swings.py — Swing Detection (+ unit tests)
4. ⬜ market_structure.py — Structure Analysis (+ unit tests)
5. ⬜ fibonacci.py — Fibonacci Calculations (+ unit tests)
6. ⬜ elliott.py — Elliott Wave Candidates (+ unit tests)
7. ⬜ confluence.py — Evidence Aggregation (+ unit tests)
8. ⬜ targets.py — Target Derivation (+ unit tests)
9. ⬜ technical_pipeline.py — Orchestrator + CLI (+ integration tests)
10. ⬜ supabase_migrations.sql — Database schema
11. ⬜ Full end-to-end testing against real data

---

## Design Principles

1. **One canonical source for swings** — All downstream engines use market_swings. No re-inventing swing detection per engine.
2. **Deterministic, not probabilistic** — Every calculation is repeatable and auditable. No hidden ML/AI reasoning.
3. **Observable facts, not opinions** — Engines report what the market structure SHOWS, not what it MEANS (interpretation comes in Phase 2).
4. **Versioned for auditability** — Algorithm changes don't erase historical calculations. v1 and v2 coexist in data.
5. **Immutable raw data** — market_prices table is never modified. Derived tables only append new rows.
6. **Comprehensive testing** — Every engine tested in isolation, integration, and against real data before Phase 2 integration.
7. **Clear error states** — No silent failures. Insufficient data explicitly states reason (not enough bars, not enough swings, conflicting signals).

