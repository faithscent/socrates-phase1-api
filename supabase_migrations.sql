/**
 * SOCrates V2 Phase 1 — Supabase Database Schema
 *
 * Tables for persisting all 6 engine outputs for historical tracking
 * and trend analysis across multiple runs.
 *
 * Design principles:
 * - One table per engine for clear separation of concerns
 * - symbol + timeframe + generated_at as primary key (allows multiple runs per day)
 * - algorithm_version immutable in each record (enables historical reproducibility)
 * - JSONB columns for flexible nested data storage
 */

-- ============================================================================
-- SWING DETECTION TABLE (SWING_V1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS swings_reports (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    algorithm_version TEXT NOT NULL,

    -- Metrics
    total_bars_analyzed INTEGER NOT NULL,
    total_swings_found INTEGER NOT NULL,
    minor_swings INTEGER NOT NULL,
    intermediate_swings INTEGER NOT NULL,
    major_swings INTEGER NOT NULL,

    -- Full swing data (JSONB for flexibility)
    swings JSONB NOT NULL DEFAULT '[]',

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_swings UNIQUE (symbol, timeframe, generated_at),
    CONSTRAINT ck_algorithm_version CHECK (algorithm_version = 'SWING_V1')
);

CREATE INDEX idx_swings_symbol_timeframe ON swings_reports (symbol, timeframe);
CREATE INDEX idx_swings_generated_at ON swings_reports (generated_at DESC);


-- ============================================================================
-- MARKET STRUCTURE TABLE (STRUCTURE_V1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS structure_reports (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    algorithm_version TEXT NOT NULL,

    -- State Classification
    structure_state TEXT NOT NULL,
    is_bullish BOOLEAN NOT NULL,
    is_bearish BOOLEAN NOT NULL,
    is_transitioning BOOLEAN NOT NULL,

    -- High/Low Tracking
    last_high DECIMAL(20, 8),
    last_high_time TIMESTAMP,
    previous_high DECIMAL(20, 8),
    previous_high_time TIMESTAMP,
    last_low DECIMAL(20, 8),
    last_low_time TIMESTAMP,
    previous_low DECIMAL(20, 8),
    previous_low_time TIMESTAMP,

    -- Structure Break Detection
    structure_break BOOLEAN NOT NULL DEFAULT FALSE,
    structure_break_type TEXT,
    structure_break_price DECIMAL(20, 8),
    structure_break_date TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_structure UNIQUE (symbol, timeframe, generated_at),
    CONSTRAINT ck_algorithm_version CHECK (algorithm_version = 'STRUCTURE_V1'),
    CONSTRAINT ck_structure_state CHECK (structure_state IN ('BULLISH', 'BEARISH', 'RANGE', 'TRANSITION', 'MIXED', 'INSUFFICIENT_DATA'))
);

CREATE INDEX idx_structure_symbol_timeframe ON structure_reports (symbol, timeframe);
CREATE INDEX idx_structure_generated_at ON structure_reports (generated_at DESC);
CREATE INDEX idx_structure_state ON structure_reports (structure_state);


-- ============================================================================
-- FIBONACCI LEVELS TABLE (FIB_V1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS fibonacci_reports (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    algorithm_version TEXT NOT NULL,

    -- Level Counts
    total_levels INTEGER NOT NULL,
    retracement_count INTEGER NOT NULL,
    extension_count INTEGER NOT NULL,
    projection_count INTEGER NOT NULL,

    -- All levels stored as JSONB
    levels JSONB NOT NULL DEFAULT '[]',

    -- Nearest levels for quick reference
    nearest_level_below JSONB,
    nearest_level_above JSONB,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_fibonacci UNIQUE (symbol, timeframe, generated_at),
    CONSTRAINT ck_algorithm_version CHECK (algorithm_version = 'FIB_V1')
);

CREATE INDEX idx_fibonacci_symbol_timeframe ON fibonacci_reports (symbol, timeframe);
CREATE INDEX idx_fibonacci_generated_at ON fibonacci_reports (generated_at DESC);


-- ============================================================================
-- ELLIOTT WAVE TABLE (ELLIOTT_V1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS elliott_reports (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    algorithm_version TEXT NOT NULL,

    -- Candidate Counts
    impulse_candidates_count INTEGER NOT NULL,
    correction_candidates_count INTEGER NOT NULL,

    -- Current Analysis
    current_phase TEXT,
    has_primary_count BOOLEAN NOT NULL DEFAULT FALSE,
    has_alternate_count BOOLEAN NOT NULL DEFAULT FALSE,

    -- All candidates stored as JSONB
    impulse_candidates JSONB NOT NULL DEFAULT '[]',
    correction_candidates JSONB NOT NULL DEFAULT '[]',
    primary_count JSONB,
    alternate_count JSONB,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_elliott UNIQUE (symbol, timeframe, generated_at),
    CONSTRAINT ck_algorithm_version CHECK (algorithm_version = 'ELLIOTT_V1'),
    CONSTRAINT ck_current_phase CHECK (current_phase IS NULL OR current_phase IN (
        'WAVE_1', 'WAVE_2', 'WAVE_3', 'WAVE_4', 'WAVE_5',
        'WAVE_A', 'WAVE_B', 'WAVE_C'
    ))
);

CREATE INDEX idx_elliott_symbol_timeframe ON elliott_reports (symbol, timeframe);
CREATE INDEX idx_elliott_generated_at ON elliott_reports (generated_at DESC);


-- ============================================================================
-- CONFLUENCE ZONES TABLE (CONFLUENCE_V1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS confluence_reports (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    algorithm_version TEXT NOT NULL,

    -- Zone Counts by Confidence Level
    total_zones INTEGER NOT NULL,
    high_confluence_zones INTEGER NOT NULL,
    medium_confluence_zones INTEGER NOT NULL,
    low_confluence_zones INTEGER NOT NULL,

    -- All zones stored as JSONB (includes zone_low, zone_high, evidence_count, confluence_state)
    zones JSONB NOT NULL DEFAULT '[]',

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_confluence UNIQUE (symbol, timeframe, generated_at),
    CONSTRAINT ck_algorithm_version CHECK (algorithm_version = 'CONFLUENCE_V1')
);

CREATE INDEX idx_confluence_symbol_timeframe ON confluence_reports (symbol, timeframe);
CREATE INDEX idx_confluence_generated_at ON confluence_reports (generated_at DESC);
CREATE INDEX idx_confluence_high_zones ON confluence_reports (high_confluence_zones DESC);


-- ============================================================================
-- TRADING TARGETS TABLE (TARGET_V1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS targets_reports (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    algorithm_version TEXT NOT NULL,

    -- Target Counts by Confidence Level
    total_targets INTEGER NOT NULL,
    high_confidence_targets INTEGER NOT NULL,
    medium_confidence_targets INTEGER NOT NULL,

    -- All targets stored as JSONB (includes target_number, price, distance_pct, distance_atr, confluence_state)
    targets JSONB NOT NULL DEFAULT '[]',

    -- Nearest target (quickest reference)
    nearest_target JSONB,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_targets UNIQUE (symbol, timeframe, generated_at),
    CONSTRAINT ck_algorithm_version CHECK (algorithm_version = 'TARGET_V1')
);

CREATE INDEX idx_targets_symbol_timeframe ON targets_reports (symbol, timeframe);
CREATE INDEX idx_targets_generated_at ON targets_reports (generated_at DESC);
CREATE INDEX idx_targets_high_confidence ON targets_reports (high_confidence_targets DESC);


-- ============================================================================
-- UNIFIED REPORTS TABLE (Meta-index for all runs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS technical_reports (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    generated_at TIMESTAMP NOT NULL,

    -- Overall Pipeline Status
    all_engines_successful BOOLEAN NOT NULL,
    error_count INTEGER NOT NULL DEFAULT 0,
    errors JSONB,

    -- Linked IDs for querying individual engine results
    swings_report_id BIGINT REFERENCES swings_reports(id),
    structure_report_id BIGINT REFERENCES structure_reports(id),
    fibonacci_report_id BIGINT REFERENCES fibonacci_reports(id),
    elliott_report_id BIGINT REFERENCES elliott_reports(id),
    confluence_report_id BIGINT REFERENCES confluence_reports(id),
    targets_report_id BIGINT REFERENCES targets_reports(id),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_technical_reports UNIQUE (symbol, timeframe, generated_at)
);

CREATE INDEX idx_technical_reports_symbol_timeframe ON technical_reports (symbol, timeframe);
CREATE INDEX idx_technical_reports_generated_at ON technical_reports (generated_at DESC);
CREATE INDEX idx_technical_reports_success ON technical_reports (all_engines_successful);


-- ============================================================================
-- GRANTS (if using role-based access control)
-- ============================================================================

-- For service role (API server):
-- GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO service_role;
--
-- For anon role (dashboard viewers):
-- GRANT SELECT ON swings_reports, structure_reports, fibonacci_reports,
--       elliott_reports, confluence_reports, targets_reports, technical_reports
-- TO anon;


-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

/*
-- Get latest report for a symbol
SELECT * FROM technical_reports
WHERE symbol = 'QQQ' AND timeframe = '1D'
ORDER BY generated_at DESC
LIMIT 1;

-- Get targets from latest run
SELECT targets FROM targets_reports
WHERE symbol = 'QQQ' AND timeframe = '1D'
ORDER BY generated_at DESC
LIMIT 1;

-- Get high confluence zones from latest run
SELECT zones FROM confluence_reports
WHERE symbol = 'QQQ' AND timeframe = '1D'
AND high_confluence_zones > 0
ORDER BY generated_at DESC
LIMIT 1;

-- Get all runs for a symbol in the last 7 days
SELECT symbol, timeframe, generated_at, all_engines_successful
FROM technical_reports
WHERE symbol = 'QQQ'
AND generated_at > NOW() - INTERVAL '7 days'
ORDER BY generated_at DESC;
*/
