-- Supabase schema for the Socrates breadth + market price pipeline.
-- Run this once in the Supabase SQL editor before importing the n8n
-- workflows — both workflows write into these tables.
--
-- Every view below is preceded by "drop view if exists ... cascade".
-- Reason: Postgres's CREATE OR REPLACE VIEW can only ADD trailing
-- columns to an existing view — it refuses to reorder, rename, or
-- insert a column in the middle (error 42P16, "cannot change name of
-- view column"). This file has grown several views' column lists
-- across rounds (e.g. v_price_moving_averages_latest gaining a
-- `confidence` column ahead of `date`), so re-running this file
-- against a database that already has an older view definition live
-- would otherwise hit that error. Dropping each view right before
-- recreating it sidesteps the restriction entirely and is safe here
-- because every view this file's own views depend on is itself
-- created earlier in this same file, in dependency order — so a
-- CASCADE drop only ever removes objects this script goes on to
-- recreate a few lines later. Tables are unaffected (they use
-- `create table if not exists` + `alter table ... add column if not
-- exists`, which don't have this restriction). This makes the file
-- safe to re-run any number of times, from any prior state.

create table if not exists platform_breadth (
  id           bigint generated always as identity primary key,
  week_of      date not null,
  section      text not null,   -- headline | reversal_system | timing_array | stochastics | indicating_ranges | gmw
  category     text not null,   -- Stocks | Currencies | Stock Indices | Bonds | Commodities | ETFs | Crypto
  metric       text not null,
  count        integer not null,
  pct          numeric not null,
  inserted_at  timestamptz not null default now(),
  unique (week_of, section, category, metric)
);

create index if not exists idx_platform_breadth_week on platform_breadth (week_of);
create index if not exists idx_platform_breadth_category on platform_breadth (category);

create table if not exists market_prices (
  id           bigint generated always as identity primary key,
  date         date not null,
  symbol       text not null,   -- see the `instruments` table below for the full current list
  close        numeric not null,
  source       text not null default 'yahoo_finance',
  inserted_at  timestamptz not null default now(),
  -- Added when market_data.py grew from "close only, 7 proxies" to real
  -- OHLCV across a much wider instrument universe. Nullable on purpose:
  -- rows written by the older pipeline (workflow_2, or an older CSV) only
  -- ever had close, and backfilling open/high/low/volume for those would
  -- mean fabricating numbers that were never actually pulled. NULL here
  -- means "not collected for this row", never "zero" or "unknown but
  -- probably close to close".
  open         numeric,
  high         numeric,
  low          numeric,
  volume       bigint,
  unique (date, symbol)
);
alter table market_prices add column if not exists open numeric;
alter table market_prices add column if not exists high numeric;
alter table market_prices add column if not exists low numeric;
alter table market_prices add column if not exists volume bigint;

create index if not exists idx_market_prices_symbol on market_prices (symbol);
create index if not exists idx_market_prices_date on market_prices (date);

-- iv_snapshot.py's output — one row per (date, symbol), same idempotency
-- pattern as market_prices (safe to re-run same day, upserts rather than
-- duplicating). No category column here on purpose: QQQ alone represents
-- two breadth categories (Stocks and Stock Indices), so "one row per
-- category" would mean fetching and storing the same instrument's IV
-- twice for no reason. iv_proxy_map below is what maps a symbol to
-- however many categories it stands in for; join through it, same as
-- v_iv_vs_breadth does.
create table if not exists iv_snapshots (
  id                   bigint generated always as identity primary key,
  date                 date not null,
  symbol               text not null,   -- QQQ | FXE | USO | GLD | HYG | TLT | IBIT — see iv_snapshot.py docstring for why these differ from market_prices.symbol
  spot                 numeric not null,
  expiry_used          date not null,
  dte                  integer not null,
  atm_call_iv          numeric,
  atm_put_iv           numeric,
  atm_iv_avg           numeric,
  otm_call_iv_5pct     numeric,
  otm_put_iv_5pct      numeric,
  put_call_skew_5pct   numeric,
  inserted_at          timestamptz not null default now(),
  unique (date, symbol)
);

create index if not exists idx_iv_snapshots_symbol on iv_snapshots (symbol);
create index if not exists idx_iv_snapshots_date on iv_snapshots (date);

-- ---------------------------------------------------------------------
-- Trend views — the "start tracking trends" layer. Query these directly
-- (Supabase's table editor, a BI tool, or another n8n node) rather than
-- recomputing this logic elsewhere.
-- ---------------------------------------------------------------------

-- Net bearish-vs-bullish reversal election bias per category per week.
-- Positive = more of the category elected a bearish reversal than a
-- bullish one that week (net bearish breadth).
drop view if exists v_net_reversal_bias cascade;
create or replace view v_net_reversal_bias as
select
  week_of,
  category,
  max(pct) filter (where metric = 'Elected a Bearish Reversal')
    - max(pct) filter (where metric = 'Elected a Bullish Reversal') as net_bearish_pct
from platform_breadth
where section = 'reversal_system'
group by week_of, category
order by week_of, category;

-- Aggregate-high vs aggregate-low signal balance per category per week —
-- positive = category is broadly topping, negative = broadly bottoming.
drop view if exists v_high_low_balance cascade;
create or replace view v_high_low_balance as
select
  week_of,
  category,
  max(pct) filter (where metric = 'Aggregate High Signal Within 3 weeks')
    - max(pct) filter (where metric = 'Aggregate Low Signal Within 3 weeks') as high_minus_low_pct
from platform_breadth
where section = 'timing_array'
group by week_of, category
order by week_of, category;

-- Panic Cycle exposure per category per week (volatility, not direction).
drop view if exists v_panic_cycle_exposure cascade;
create or replace view v_panic_cycle_exposure as
select week_of, category, pct as panic_cycle_pct
from platform_breadth
where section = 'timing_array' and metric = 'Panic Cycle Signal Within 3 weeks'
order by week_of, category;

-- Week-over-week change in net reversal bias per category — the "what
-- moved most" scan.
drop view if exists v_reversal_bias_wow_change cascade;
create or replace view v_reversal_bias_wow_change as
select
  week_of,
  category,
  net_bearish_pct,
  net_bearish_pct - lag(net_bearish_pct) over (partition by category order by week_of) as change_from_prior_week
from v_net_reversal_bias
order by week_of, category;

-- Realized N-day-forward return per market_prices row, for eyeballing how
-- price moved after any given date — join this against platform_breadth's
-- week_of manually per category/proxy when you're checking a specific
-- read, rather than trying to encode the category->symbol mapping in SQL.
drop view if exists v_price_forward_return cascade;
create or replace view v_price_forward_return as
select
  symbol,
  date,
  close,
  lead(close, 15) over (partition by symbol order by date) as close_15_sessions_later,
  round(
    (lead(close, 15) over (partition by symbol order by date) / close - 1) * 100,
    2
  ) as forward_return_pct_15_sessions  -- ~21 calendar days of trading sessions
from market_prices
order by symbol, date;

-- ---------------------------------------------------------------------
-- Scorecard views — the SAME fixed formula as scorecard.py, moved into
-- the database so the live dashboard and the n8n alert workflow read one
-- shared number instead of two implementations that could drift apart.
-- If you ever change the weights/thresholds, change them in BOTH places
-- (scorecard.py's constants at the top of the file, and here) — nothing
-- enforces that automatically.
-- ---------------------------------------------------------------------

drop view if exists v_scorecard cascade;
create or replace view v_scorecard as
select
  b.week_of,
  b.category,
  b.net_bearish_pct as net_reversal_bias,
  h.high_minus_low_pct as net_high_low,
  p.panic_cycle_pct,
  round((0.4 * b.net_bearish_pct + 0.4 * h.high_minus_low_pct + 0.2 * p.panic_cycle_pct)::numeric, 2) as score,
  case
    when (0.4 * b.net_bearish_pct + 0.4 * h.high_minus_low_pct + 0.2 * p.panic_cycle_pct) > 8.0 then 'CAUTION'
    when (0.4 * b.net_bearish_pct + 0.4 * h.high_minus_low_pct + 0.2 * p.panic_cycle_pct) < -8.0 then 'CONSTRUCTIVE'
    else 'NEUTRAL'
  end as call,
  (p.panic_cycle_pct > 20.0) as volatility_flag
from v_net_reversal_bias b
join v_high_low_balance h using (week_of, category)
join v_panic_cycle_exposure p using (week_of, category)
order by b.week_of, b.category;

-- Adds week-over-week deltas so a consumer can tell a NEW signal (this
-- week's call/flag differs from last week's) from a call that's just
-- still sitting where it was — that distinction is what the alert
-- workflow filters on, not just "is this category currently CAUTION".
drop view if exists v_scorecard_wow cascade;
create or replace view v_scorecard_wow as
select
  s.*,
  lag(call) over (partition by category order by week_of) as prior_call,
  lag(volatility_flag) over (partition by category order by week_of) as prior_volatility_flag,
  round((s.score - lag(score) over (partition by category order by week_of))::numeric, 2) as score_change_from_prior_week
from v_scorecard s
order by s.week_of, s.category;

-- Reference table for market_prices.symbol — display name, broad group,
-- and how confident the ticker mapping actually is. Mirrors
-- market_data.py's INSTRUMENT_UNIVERSE exactly (same symbols, same
-- confidence tier) — if you add/change an instrument there, update this
-- table too. confidence is deliberately just 'high'/'medium'/'low': the
-- full reasoning for medium/low entries (why the ticker might be wrong)
-- lives in market_data.py's docstring, not duplicated here.
create table if not exists instruments (
  symbol        text primary key,
  display_name  text not null,
  group_label   text not null,
  confidence    text not null check (confidence in ('high', 'medium', 'low'))
);

insert into instruments (symbol, display_name, group_label, confidence) values
  ('QQQ', 'Invesco QQQ Trust', 'Tech/Momentum', 'high'),
  ('EURUSD=X', 'Euro Adjusted Spot (EUR/USD)', 'FX', 'high'),
  ('USO', 'United States Oil Fund LP', 'Commodities', 'high'),
  ('GLD', 'SPDR Gold Shares', 'Commodities', 'high'),
  ('HYG', 'iShares iBoxx $ High Yield Corporate Bond ETF', 'Bonds', 'high'),
  ('TLT', 'iShares 20+ Year Treasury Bond', 'Bonds', 'high'),
  ('BTC-USD', 'Bitcoin Per USD (Coinbase)', 'Crypto', 'high'),
  ('PLTR', 'Palantir Technologies Inc', 'Tech/Momentum', 'high'),
  ('MU', 'Micron Technology', 'Tech/Momentum', 'high'),
  ('^NDX', 'NASDAQ 100 Index', 'Tech/Momentum', 'high'),
  ('NQ=F', 'NASDAQ 100 Index Futures', 'Tech/Momentum', 'high'),
  ('^IXIC', 'NASDAQ Composite Index', 'Tech/Momentum', 'high'),
  ('^GSPC', 'S&P 500 Index', 'Global Indices', 'high'),
  ('^DJI', 'Dow Jones Industrials Index', 'Global Indices', 'high'),
  ('^FTSE', 'FTSE 100 Index', 'Global Indices', 'high'),
  ('^N225', 'NIKKEI 225 Index', 'Global Indices', 'high'),
  ('^HSI', 'Hang Seng Index', 'Global Indices', 'high'),
  ('^GDAXI', 'DAX Performance Index', 'Global Indices', 'high'),
  ('^FCHI', 'CAC-40 Index', 'Global Indices', 'high'),
  ('000001.SS', 'Shanghai Composite', 'Global Indices', 'medium'),
  ('^OEX', 'S&P Global 100 Index', 'Global Indices', 'low'),
  ('EEM', 'MSCI Emerging Markets $ Index', 'Global Indices', 'low'),
  ('FTSEMIB.MI', 'Milano Italia Borsa (MIB) Index', 'Global Indices', 'medium'),
  ('GC=F', 'Gold Futures (COMEX, continuous front-month)', 'Commodities', 'high'),
  ('SI=F', 'Silver Futures (COMEX, continuous front-month)', 'Commodities', 'high'),
  ('CL=F', 'NY Crude Oil Futures', 'Commodities', 'high'),
  ('^TNX', 'US BMK 10 Yr Index', 'Rates', 'medium'),
  ('^VIX', 'CBOE VIX Index', 'Volatility', 'high'),
  ('^VVIX', 'CBOE VVIX Index (volatility of VIX)', 'Volatility', 'medium'),
  ('^COR1M', 'Cboe 1-Month Implied Correlation Index', 'Volatility', 'medium'),
  ('V2TX.DE', 'EURO STOXX 50 Volatility (VSTOXX)', 'Volatility', 'medium'),
  ('DX-Y.NYB', 'US Dollar Index', 'FX', 'medium'),
  ('SGD=X', 'Singapore Dollar Spot (USD/SGD)', 'FX', 'high'),
  ('TWD=X', 'Taiwanese Dollar Spot (USD/TWD)', 'FX', 'medium'),
  ('CAD=X', 'Canadian Dollar Spot (USD/CAD)', 'FX', 'high'),
  ('CHF=X', 'Swiss Franc Spot (USD/CHF)', 'FX', 'high'),
  ('INR=X', 'Indian Rupee Spot (USD/INR)', 'FX', 'high'),
  ('CNY=X', 'Chinese Yuan Spot (USD/CNY)', 'FX', 'high'),
  ('GBPUSD=X', 'British Pound Spot (GBP/USD)', 'FX', 'high'),
  ('JPY=X', 'Japanese Yen Spot (USD/JPY)', 'FX', 'high'),
  ('6E=F', 'Euro Adjusted Futures (EUR/USD futures)', 'FX', 'medium'),
  ('ETH-USD', 'Ethereum Per USD (Coinbase)', 'Crypto', 'high'),
  ('IBIT', 'iShares Bitcoin Trust ETF', 'Crypto', 'high'),
  -- FX ETFs (this round): the tradeable/optionable instrument behind each
  -- spot pair above — see market_data.py's INSTRUMENT_UNIVERSE comment.
  ('FXE', 'Invesco CurrencyShares Euro Trust', 'FX-ETF', 'high'),
  ('FXY', 'Invesco CurrencyShares Japanese Yen Trust', 'FX-ETF', 'high'),
  ('FXB', 'Invesco CurrencyShares British Pound Sterling Trust', 'FX-ETF', 'high'),
  ('FXF', 'Invesco CurrencyShares Swiss Franc Trust', 'FX-ETF', 'high'),
  ('FXC', 'Invesco CurrencyShares Canadian Dollar Trust', 'FX-ETF', 'high')
on conflict (symbol) do update set
  display_name = excluded.display_name,
  group_label = excluded.group_label,
  confidence = excluded.confidence;

-- Moving averages, computed over however many real observations exist per
-- symbol (not a calendar window) — works the same whether market_data.py
-- is run daily or weekly. observations_N tells you whether an average is
-- backed by enough real data to mean anything; a "20-period" average
-- built from 4 real rows is labeled as such, not hidden.
drop view if exists v_price_moving_averages cascade;
create or replace view v_price_moving_averages as
select
  symbol,
  date,
  close,
  volume,
  round(avg(close) over (partition by symbol order by date rows between 9 preceding and current row)::numeric, 4) as sma_10,
  least(10, count(*) over (partition by symbol order by date rows between 9 preceding and current row)) as observations_10,
  round(avg(close) over (partition by symbol order by date rows between 19 preceding and current row)::numeric, 4) as sma_20,
  least(20, count(*) over (partition by symbol order by date rows between 19 preceding and current row)) as observations_20,
  -- 50-session SMA, same "however much real history actually exists"
  -- discipline as sma_10/sma_20 — this is what the dashboard's trend-
  -- direction read (price vs its own 50d average) is built on. With only
  -- a couple of real sessions pushed so far, observations_50 will show
  -- that honestly (e.g. "2 of 50") rather than a 50-day average computed
  -- from 2 real points pretending to be a real 50-day read.
  round(avg(close) over (partition by symbol order by date rows between 49 preceding and current row)::numeric, 4) as sma_50,
  least(50, count(*) over (partition by symbol order by date rows between 49 preceding and current row)) as observations_50
from market_prices
order by symbol, date;

-- Weekly (~5 trading sessions) and monthly (~21 trading sessions) % change
-- per symbol — the "weekly and monthly pattern" read, computed the same
-- way v_reversal_bias_wow_change computes week-over-week breadth change.
-- nullif guards a symbol whose lookback window doesn't exist yet (a
-- newly-added instrument with under a week/month of history) rather than
-- dividing by null and erroring.
drop view if exists v_price_change_windows cascade;
create or replace view v_price_change_windows as
select
  symbol,
  date,
  close,
  round(((close / nullif(lag(close, 5) over (partition by symbol order by date), 0)) - 1) * 100, 2) as pct_change_1wk,
  round(((close / nullif(lag(close, 21) over (partition by symbol order by date), 0)) - 1) * 100, 2) as pct_change_1mo
from market_prices
order by symbol, date;

-- Latest moving-average + weekly/monthly-change reading per symbol,
-- joined to its display name and group — what the dashboard actually
-- queries for the instrument watchlist.
drop view if exists v_price_moving_averages_latest cascade;
create or replace view v_price_moving_averages_latest as
select distinct on (m.symbol)
  m.symbol, i.display_name, i.group_label, i.confidence,
  m.date, m.close, m.volume, m.sma_10, m.observations_10, m.sma_20, m.observations_20,
  m.sma_50, m.observations_50,
  w.pct_change_1wk, w.pct_change_1mo
from v_price_moving_averages m
left join instruments i using (symbol)
left join v_price_change_windows w on w.symbol = m.symbol and w.date = m.date
order by m.symbol, m.date desc;

-- Which listed-options symbol(s) stand in for each breadth category, for
-- iv_snapshots. Kept as a real table (not hardcoded in SQL) so it's one
-- place to edit if the proxy list ever changes — iv_snapshot.py and
-- iv_vs_breadth.py have their own copy of this same mapping (OPTIONABLE_PROXIES)
-- since those need to run standalone without Supabase; if you change one,
-- change all three.
create table if not exists iv_proxy_map (
  category  text not null,
  symbol    text not null,
  primary key (category, symbol)
);

insert into iv_proxy_map (category, symbol) values
  ('Stocks', 'QQQ'), ('Stock Indices', 'QQQ'),
  ('Currencies', 'FXE'), ('Currencies', 'FXY'), ('Currencies', 'FXB'), ('Currencies', 'FXF'), ('Currencies', 'FXC'),
  ('Commodities', 'USO'), ('Commodities', 'GLD'),
  ('Bonds', 'HYG'), ('Bonds', 'TLT'), ('Crypto', 'IBIT')
on conflict (category, symbol) do nothing;

-- "Is this actually cheap right now?" needs IV compared against its OWN
-- recent history, not just today's level in isolation — that's what
-- iv_snapshot.py's docstring means by "no IV Rank on day one." This view
-- computes it directly from whatever history has accumulated in
-- iv_snapshots so far: percent_rank() gives each reading's percentile
-- among all readings for that symbol (0 = cheapest IV seen, 100 =
-- richest). It updates itself automatically as more days/weeks of
-- iv_snapshot.py runs land in the table — no separate backfill step.
-- observations tells you how much to trust the number: with only 2-3
-- readings a percentile is close to meaningless, which is why the
-- dashboard shows the observation count next to it rather than a bare
-- percentile that looks more precise than it is.
drop view if exists v_iv_rank cascade;
create or replace view v_iv_rank as
select
  symbol,
  date,
  atm_iv_avg,
  put_call_skew_5pct,
  count(*) over (partition by symbol) as observations,
  round((percent_rank() over (partition by symbol order by atm_iv_avg))::numeric * 100, 1) as iv_percentile
from iv_snapshots
order by symbol, date;

-- Latest reading per symbol, with its percentile rank against all history
-- collected so far — what the dashboard actually queries.
drop view if exists v_iv_rank_latest cascade;
create or replace view v_iv_rank_latest as
select distinct on (symbol)
  symbol, date, atm_iv_avg, put_call_skew_5pct, observations, iv_percentile
from v_iv_rank
order by symbol, date desc;

-- Same join iv_vs_breadth.py does locally, as a live view — breadth's
-- latest call/score next to that proxy's latest IV/skew, per category.
drop view if exists v_iv_vs_breadth cascade;
create or replace view v_iv_vs_breadth as
select
  m.category,
  m.symbol,
  b.week_of as breadth_week,
  b.call as breadth_call,
  b.score as breadth_score,
  i.date as iv_date,
  i.atm_iv_avg,
  i.put_call_skew_5pct
from iv_proxy_map m
left join lateral (
  select s.week_of, s.call, s.score
  from v_scorecard_wow s
  where s.category = m.category
  order by s.week_of desc
  limit 1
) b on true
left join lateral (
  select iv.date, iv.atm_iv_avg, iv.put_call_skew_5pct
  from iv_snapshots iv
  where iv.symbol = m.symbol
  order by iv.date desc
  limit 1
) i on true
order by m.category, m.symbol;

-- ---------------------------------------------------------------------
-- Price proxy map — the SAME category->instrument mapping as
-- scorecard.py's CATEGORY_PROXIES, now also in the database so a SQL view
-- (v_signal_backtest below) can join on it without re-encoding the
-- mapping in JS a third time. If you change scorecard.py's
-- CATEGORY_PROXIES, update this table too — same "keep N places in sync"
-- discipline as iv_proxy_map/OPTIONABLE_PROXIES elsewhere in this
-- project. ETFs is intentionally absent, same reason scorecard.py leaves
-- it unmapped: QQQ/GLD/USO/HYG/TLT are themselves classified as ETFs on
-- the platform, so that category substantially overlaps the others
-- already covered.
-- ---------------------------------------------------------------------

create table if not exists price_proxy_map (
  category  text not null,
  symbol    text not null,
  primary key (category, symbol)
);

insert into price_proxy_map (category, symbol) values
  ('Stocks', 'QQQ'), ('Stock Indices', 'QQQ'), ('Currencies', 'EURUSD=X'),
  ('Commodities', 'USO'), ('Commodities', 'GLD'),
  ('Bonds', 'HYG'), ('Bonds', 'TLT'), ('Crypto', 'BTC-USD')
on conflict (category, symbol) do nothing;

-- ---------------------------------------------------------------------
-- Signal backtest scaffolding — "when this category's breadth call was
-- X, what did its price proxy actually do over the following ~15
-- trading sessions (~21 calendar days)?" Built now so it's ready, but
-- read v_signal_backtest_summary's own comment before trusting its
-- numbers: at 6 weeks of platform_breadth history, n per (category,
-- call) is tiny, and a backtest on a handful of observations is noise
-- dressed up as a finding, not evidence. This view does NOT get
-- reinterpreted or gated in SQL — that honesty check belongs in
-- whatever reads it (the dashboard gates display behind a minimum n,
-- same as v_iv_rank does for IV percentile).
-- ---------------------------------------------------------------------

-- One row per (week_of, category, price-proxy symbol): the call in
-- force that week, and the forward return of the FIRST market_prices
-- row on or after week_of for that symbol (breadth weeks and daily
-- price dates don't share a fixed offset, so this takes the nearest
-- available trading day at/after week_of rather than assuming an exact
-- match).
drop view if exists v_signal_backtest cascade;
create or replace view v_signal_backtest as
select
  s.week_of,
  s.category,
  s.call,
  s.score,
  s.volatility_flag,
  pm.symbol,
  f.date as price_date,
  f.close,
  f.forward_return_pct_15_sessions
from v_scorecard_wow s
join price_proxy_map pm on pm.category = s.category
join lateral (
  select p.date, p.close, p.forward_return_pct_15_sessions
  from v_price_forward_return p
  where p.symbol = pm.symbol and p.date >= s.week_of
  order by p.date asc
  limit 1
) f on true
order by s.category, s.week_of, pm.symbol;

-- Aggregated by category+call: average/stddev/min/max forward return and
-- n (observation count). n is the whole point of this view — read it
-- before the average. A handful of observations can show a striking
-- average purely by chance; there's no fixed n at which a backtest
-- becomes trustworthy, but single digits should be treated as "not yet
-- informative" rather than a pattern.
drop view if exists v_signal_backtest_summary cascade;
create or replace view v_signal_backtest_summary as
select
  category,
  call,
  count(*) as n,
  round(avg(forward_return_pct_15_sessions)::numeric, 2) as avg_forward_return_pct,
  round(stddev_samp(forward_return_pct_15_sessions)::numeric, 2) as stddev_forward_return_pct,
  round(min(forward_return_pct_15_sessions)::numeric, 2) as min_forward_return_pct,
  round(max(forward_return_pct_15_sessions)::numeric, 2) as max_forward_return_pct
from v_signal_backtest
where forward_return_pct_15_sessions is not null
group by category, call
order by category, call;

-- ---------------------------------------------------------------------
-- Per-instrument backtest — same idea as v_signal_backtest above, but
-- keyed off iv_proxy_map (every optionable instrument, e.g. all five
-- Currencies ETFs) instead of price_proxy_map (one canonical instrument
-- per category). v_signal_backtest_summary answers "when Currencies was
-- CAUTION, what did the category's single reference instrument do";
-- this answers "when Currencies was CAUTION, what did FXY specifically
-- do" vs "what did FXE specifically do" — the two can and do diverge,
-- since a Euro ETF and a Yen ETF don't move the same way even under the
-- same category-level breadth call. Same n-gating discipline applies:
-- read v_instrument_backtest_summary's n before its average, same as
-- v_signal_backtest_summary's own comment says.
-- ---------------------------------------------------------------------

drop view if exists v_instrument_backtest cascade;
create or replace view v_instrument_backtest as
select
  s.week_of,
  s.category,
  s.call,
  s.score,
  s.volatility_flag,
  m.symbol,
  f.date as price_date,
  f.close,
  f.forward_return_pct_15_sessions
from v_scorecard_wow s
join iv_proxy_map m on m.category = s.category
join lateral (
  select p.date, p.close, p.forward_return_pct_15_sessions
  from v_price_forward_return p
  where p.symbol = m.symbol and p.date >= s.week_of
  order by p.date asc
  limit 1
) f on true
order by s.category, m.symbol, s.week_of;

drop view if exists v_instrument_backtest_summary cascade;
create or replace view v_instrument_backtest_summary as
select
  category,
  symbol,
  call,
  count(*) as n,
  round(avg(forward_return_pct_15_sessions)::numeric, 2) as avg_forward_return_pct,
  round(stddev_samp(forward_return_pct_15_sessions)::numeric, 2) as stddev_forward_return_pct,
  round(min(forward_return_pct_15_sessions)::numeric, 2) as min_forward_return_pct,
  round(max(forward_return_pct_15_sessions)::numeric, 2) as max_forward_return_pct
from v_instrument_backtest
where forward_return_pct_15_sessions is not null
group by category, symbol, call
order by category, symbol, call;

-- ---------------------------------------------------------------------
-- FRED macro series — point-in-time rates/inflation/dollar/vol data
-- fred_data.py pulls from the St. Louis Fed's public fredgraph.csv
-- endpoint (no API key needed). Fills a real gap: yfinance/Yahoo had no
-- usable ticker for Japan/Euro area 10-year government yields (see
-- market_data.py's docstring) — FRED does, via OECD-sourced series. Two
-- of the eight series below are flagged 'medium' confidence for the same
-- reason market_data.py flags some tickers that way: I could not verify
-- their exact series IDs against a live fetch from this sandbox (FRED is
-- also outside this sandbox's network allowlist — same restriction as
-- Yahoo). See fred_data.py's docstring for the full reasoning per series.
-- ---------------------------------------------------------------------

create table if not exists fred_series_meta (
  series_id    text primary key,
  description  text not null,
  frequency    text not null,   -- daily | monthly
  confidence   text not null check (confidence in ('high', 'medium', 'low'))
);

insert into fred_series_meta (series_id, description, frequency, confidence) values
  ('DGS10', '10-Year Treasury Constant Maturity Rate (US)', 'daily', 'high'),
  ('DGS2', '2-Year Treasury Constant Maturity Rate (US)', 'daily', 'high'),
  ('DFF', 'Federal Funds Effective Rate', 'daily', 'high'),
  ('VIXCLS', 'CBOE Volatility Index (VIX) — FRED''s own copy, longer/more reliable history than a Yahoo pull', 'daily', 'high'),
  ('DTWEXBGS', 'Trade Weighted US Dollar Index: Broad, Goods and Services', 'daily', 'high'),
  ('CPIAUCSL', 'CPI for All Urban Consumers: All Items, seasonally adjusted', 'monthly', 'high'),
  ('IRLTLT01JPM156N', 'Japan 10-Year Government Bond Yield (OECD, via FRED)', 'monthly', 'medium'),
  ('IRLTLT01EZM156N', 'Euro Area 10-Year Government Bond Yield (OECD, via FRED)', 'monthly', 'medium'),
  -- Market stress gauges — added to fred_data.py's FRED_SERIES a round
  -- ago but missed here, which would have made push_to_supabase.py fail
  -- on fred_series' foreign key to this table the moment you actually
  -- pushed them. Caught and fixed this round.
  ('BAMLH0A0HYM2', 'ICE BofA US High Yield Index Option-Adjusted Spread (credit stress, high-yield)', 'daily', 'high'),
  ('NFCI', 'Chicago Fed National Financial Conditions Index', 'weekly', 'high'),
  ('STLFSI4', 'St. Louis Fed Financial Stress Index', 'weekly', 'high'),
  -- Added this round, from your pasted stress-gauge/credit/sovereign
  -- table — see fred_data.py's docstring for the full reasoning on which
  -- of your pasted rows have a free source and which don't (CDX IG/HY,
  -- iTraxx Europe Main, and a true Euribor-OIS spread do not).
  ('BAMLC0A0CM', 'ICE BofA US Corporate Index Option-Adjusted Spread — investment-grade credit stress; same family as BAMLH0A0HYM2 but IG not HY. Closest free equivalent to a CDX IG-style read (a bond-index OAS, not the same instrument as the CDX swap index itself)', 'daily', 'high'),
  ('IRLTLT01DEM156N', 'Germany 10-Year Government Bond Yield (Bund, OECD via FRED)', 'monthly', 'medium'),
  ('IRLTLT01FRM156N', 'France 10-Year Government Bond Yield (OECD via FRED)', 'monthly', 'medium'),
  ('IRLTLT01ITM156N', 'Italy 10-Year Government Bond Yield (OECD via FRED) — this plus the Germany/France series above is what v_fred_spreads computes the France-Germany and Italy-Germany 10Y spreads from', 'monthly', 'medium'),
  ('IR3TIB01EZM156N', '3-Month Euro Area Interbank Offered Rate — the raw rate only, NOT a Euribor-OIS spread (no free daily €STR/OIS leg was found to subtract against it; see fred_data.py)', 'monthly', 'medium')
on conflict (series_id) do update set
  description = excluded.description, frequency = excluded.frequency, confidence = excluded.confidence;

create table if not exists fred_series (
  series_id    text not null references fred_series_meta(series_id),
  date         date not null,
  value        numeric,   -- nullable: FRED marks some dates "." (no reading yet, e.g. a monthly series' most recent month) — kept as null, never fabricated
  inserted_at  timestamptz not null default now(),
  primary key (series_id, date)
);

create index if not exists idx_fred_series_series on fred_series (series_id);
create index if not exists idx_fred_series_date on fred_series (date);

-- Latest reading per series plus the simple change from its prior
-- reading (not a %, since a rate can cross zero) — what the dashboard's
-- FRED panel queries.
drop view if exists v_fred_latest cascade;
create or replace view v_fred_latest as
select distinct on (f.series_id)
  f.series_id, m.description, m.frequency, m.confidence,
  f.date, f.value,
  round((f.value - lag(f.value) over (partition by f.series_id order by f.date))::numeric, 4) as change_from_prior_reading
from fred_series f
join fred_series_meta m using (series_id)
where f.value is not null
order by f.series_id, f.date desc;

-- Percentile rank of each FRED reading against that SAME series' own
-- history — same method as v_iv_rank, applied here so VIX (or any other
-- FRED series) can be read as "cheap/rich right now vs its own normal
-- range" rather than eyeballing a raw level. Deliberately NOT compared
-- against a symbol's own IV rank from iv_snapshots — VIX measures S&P 500
-- volatility specifically, and FX/commodity/bond implied vol sits on a
-- structurally different scale, so a direct "FXE IV vs VIX" comparison
-- would look like a cheap/expensive read while actually just reflecting
-- that different asset classes are naturally more or less volatile. Two
-- separate regime gauges, read side by side, never against each other.
drop view if exists v_fred_series_rank cascade;
create or replace view v_fred_series_rank as
select
  series_id,
  date,
  value,
  count(*) over (partition by series_id) as observations,
  round((percent_rank() over (partition by series_id order by value))::numeric * 100, 1) as value_percentile
from fred_series
where value is not null
order by series_id, date;

drop view if exists v_fred_series_rank_latest cascade;
create or replace view v_fred_series_rank_latest as
select distinct on (r.series_id)
  r.series_id, m.description, m.frequency, m.confidence,
  r.date, r.value, r.observations, r.value_percentile
from v_fred_series_rank r
join fred_series_meta m using (series_id)
order by r.series_id, r.date desc;

-- Computed sovereign/rate spreads, in basis points — the "insight" layer
-- on top of raw FRED levels, same idea as v_price_change_windows turning
-- raw closes into a %. Every spread here is a plain subtraction of two
-- already-tracked series (no fitted weights, nothing invented): US
-- 2s10s (DGS10 - DGS2, positive = normal/upward-sloping curve), and the
-- two sovereign risk-premium spreads from your pasted table — France vs
-- Germany and Italy vs Germany 10-year yields (both OECD monthly series,
-- so this updates monthly, not daily, honestly reflecting the source
-- data's real frequency rather than a fabricated daily interpolation). A
-- row is only produced for a date where BOTH legs of that spread have a
-- real reading — no half-computed spread from one real and one missing
-- value.
drop view if exists v_fred_spreads cascade;
create or replace view v_fred_spreads as
with pivoted as (
  select
    date,
    max(value) filter (where series_id = 'DGS10') as us_10y,
    max(value) filter (where series_id = 'DGS2') as us_2y,
    max(value) filter (where series_id = 'IRLTLT01DEM156N') as de_10y,
    max(value) filter (where series_id = 'IRLTLT01FRM156N') as fr_10y,
    max(value) filter (where series_id = 'IRLTLT01ITM156N') as it_10y
  from fred_series
  where series_id in ('DGS10', 'DGS2', 'IRLTLT01DEM156N', 'IRLTLT01FRM156N', 'IRLTLT01ITM156N')
    and value is not null
  group by date
)
select
  date,
  case when us_10y is not null and us_2y is not null
    then round(((us_10y - us_2y) * 100)::numeric, 1) end as us_2s10s_bps,
  case when fr_10y is not null and de_10y is not null
    then round(((fr_10y - de_10y) * 100)::numeric, 1) end as fr_de_10y_bps,
  case when it_10y is not null and de_10y is not null
    then round(((it_10y - de_10y) * 100)::numeric, 1) end as it_de_10y_bps
from pivoted
where (us_10y is not null and us_2y is not null)
   or (fr_10y is not null and de_10y is not null)
   or (it_10y is not null and de_10y is not null)
order by date;

-- Each spread's own latest reading, independently — NOT just the latest
-- row of v_fred_spreads. The US leg updates daily and the two European
-- legs update monthly, so "the latest combined row" would routinely show
-- a real us_2s10s_bps next to a blank fr_de/it_de (today isn't the 1st
-- of the month) even though a real, still-current monthly reading exists
-- a few weeks back — same one-series-at-a-time honesty as v_fred_latest.
drop view if exists v_fred_spreads_latest cascade;
create or replace view v_fred_spreads_latest as
select
  (select date from v_fred_spreads where us_2s10s_bps is not null order by date desc limit 1) as us_2s10s_date,
  (select us_2s10s_bps from v_fred_spreads where us_2s10s_bps is not null order by date desc limit 1) as us_2s10s_bps,
  (select date from v_fred_spreads where fr_de_10y_bps is not null order by date desc limit 1) as fr_de_10y_date,
  (select fr_de_10y_bps from v_fred_spreads where fr_de_10y_bps is not null order by date desc limit 1) as fr_de_10y_bps,
  (select date from v_fred_spreads where it_de_10y_bps is not null order by date desc limit 1) as it_de_10y_date,
  (select it_de_10y_bps from v_fred_spreads where it_de_10y_bps is not null order by date desc limit 1) as it_de_10y_bps;

-- ---------------------------------------------------------------------
-- Per-instrument Premium Overview Commentary — a different grain (one
-- specific market, e.g. "US Dollar v Euro Adjusted Spot") and a much
-- richer report than platform_breadth's whole-category statistics.
-- raw_text always keeps the full report verbatim, even for fields not
-- (yet) pulled into their own column — see parse_premium_commentary.py
-- for what's actually extracted today and why the Weekly Timing Array
-- color grid and Watchlist tables aren't in here yet.
-- ---------------------------------------------------------------------

create table if not exists instrument_commentary (
  id                              bigint generated always as identity primary key,
  market                          text not null,
  report_date                     date not null,
  last_close                      numeric,
  prior_year_close                numeric,
  pct_change_yoy                  numeric,
  reversal_daily_bull             numeric,
  reversal_daily_bear             numeric,
  reversal_weekly_bull            numeric,
  reversal_weekly_bear            numeric,
  reversal_monthly_bull           numeric,
  reversal_monthly_bear           numeric,
  trend_change_daily              numeric,
  trend_change_weekly             numeric,
  trend_change_monthly            numeric,
  trend_change_quarterly          numeric,
  trend_change_yearly             numeric,
  risk_daily_upside_price         numeric,
  risk_daily_upside_pct           numeric,
  risk_daily_downside_price       numeric,
  risk_daily_downside_pct         numeric,
  risk_weekly_upside_price        numeric,
  risk_weekly_upside_pct          numeric,
  risk_weekly_downside_price      numeric,
  risk_weekly_downside_pct        numeric,
  risk_monthly_upside_price       numeric,
  risk_monthly_upside_pct         numeric,
  risk_monthly_downside_price     numeric,
  risk_monthly_downside_pct       numeric,
  risk_quarterly_upside_price     numeric,
  risk_quarterly_upside_pct       numeric,
  risk_quarterly_downside_price   numeric,
  risk_quarterly_downside_pct     numeric,
  risk_yearly_upside_price        numeric,
  risk_yearly_upside_pct          numeric,
  risk_yearly_downside_price      numeric,
  risk_yearly_downside_pct        numeric,
  ecm_next_target_date            date,
  raw_text                        text not null,
  inserted_at                     timestamptz not null default now(),
  unique (market, report_date)
);

create index if not exists idx_instrument_commentary_market on instrument_commentary (market);

-- ---------------------------------------------------------------------
-- Alert dedup — one row per (week_of, category) once the n8n alert
-- workflow has sent a Telegram message for it. Since a given week's
-- breadth data never changes after it's inserted, "already have a row
-- here" is exactly "already alerted on this week's signal for this
-- category" — that's what lets the workflow poll daily without spamming
-- the same signal every day.
-- ---------------------------------------------------------------------

create table if not exists alerts_sent (
  id               bigint generated always as identity primary key,
  week_of          date not null,
  category         text not null,
  call             text,
  volatility_flag  boolean,
  sent_at          timestamptz not null default now(),
  unique (week_of, category)
);

-- ---------------------------------------------------------------------
-- Your own trade log — what you actually bought/sold, open/closed, at
-- what price, and when. This is the piece the rest of this file doesn't
-- have: everything else here is proxy-level backtesting (what a category's
-- CANONICAL instrument did after a breadth call, per v_signal_backtest —
-- an instrument you may not have actually traded, at a size you didn't
-- actually take). This table is your real, point-in-time record, so
-- v_position_pnl below can answer "what did MY positions actually do,"
-- not just "what would the proxy have done."
--
-- position_id is any unique string you choose (a ticket number, or just
-- "FXE-2026-09-22" — whatever's unique to you); this table doesn't
-- generate one for you because IBKR (or wherever you're pulling entries
-- from) already has its own ID and re-using that avoids a second mapping
-- to keep straight. linked_week_of/linked_category are optional but
-- worth filling in — they're what let v_position_pnl join this position
-- back to the exact v_scorecard_wow row (call, panic_cycle_pct) that was
-- live when you opened it, which is the actual backtest: did a position
-- taken under a CAUTION call / high panic-cycle reading work out or not.
-- instrument_type is free text (shares, call option, put option, call
-- spread, ...) rather than a fixed options-chain schema, since this
-- dashboard doesn't track strikes/expiries anywhere else either — put
-- whatever's useful to you in notes.
-- ---------------------------------------------------------------------

create table if not exists positions (
  position_id      text primary key,
  symbol           text not null,
  category         text,
  instrument_type  text not null default 'shares',
  direction        text not null check (direction in ('long', 'short')),
  status           text not null check (status in ('open', 'closed')),
  open_date        date not null,
  open_price       numeric not null,
  quantity         numeric not null,
  close_date       date,
  close_price      numeric,
  linked_week_of   date,
  linked_category  text,
  notes            text,
  updated_at       timestamptz not null default now()
);

create index if not exists idx_positions_symbol on positions (symbol);
create index if not exists idx_positions_status on positions (status);

-- Realized P&L for closed positions (from your own close_price), an
-- unrealized mark for open positions (today's latest market_prices close
-- for that symbol — only meaningful for symbols market_data.py actually
-- tracks; null otherwise, never a fabricated estimate), and, when you
-- filled in linked_week_of/linked_category, the breadth call and
-- panic_cycle_pct that were live at entry — so you can group your own
-- trade history by "positions I took under a CAUTION call" or "under a
-- flagged panic-cycle week" and see how those actually performed, not
-- just what the generic proxy backtest says.
drop view if exists v_position_pnl cascade;
create or replace view v_position_pnl as
select
  p.*,
  case when p.status = 'closed' and p.close_price is not null then
    round((((p.close_price / p.open_price) - 1) * 100 * (case when p.direction = 'short' then -1 else 1 end))::numeric, 2)
  end as realized_return_pct,
  case when p.status = 'open' then mp.close end as latest_mark,
  case when p.status = 'open' then mp.date end as latest_mark_date,
  case when p.status = 'open' and mp.close is not null then
    round((((mp.close / p.open_price) - 1) * 100 * (case when p.direction = 'short' then -1 else 1 end))::numeric, 2)
  end as unrealized_return_pct,
  sc.call as call_at_entry,
  sc.panic_cycle_pct as panic_cycle_pct_at_entry,
  sc.volatility_flag as volatility_flag_at_entry
from positions p
left join lateral (
  select m.close, m.date
  from market_prices m
  where m.symbol = p.symbol
  order by m.date desc
  limit 1
) mp on true
left join v_scorecard_wow sc
  on sc.week_of = p.linked_week_of and sc.category = p.linked_category
order by p.open_date desc;

-- ---------------------------------------------------------------------
-- Read-only access for the dashboard (anon key, used client-side in the
-- browser — never the service_role key, which stays server-side in n8n
-- only). All writes still go through n8n using the service_role key,
-- which bypasses RLS entirely, so none of this grants anon any write
-- path. This data isn't sensitive (it's breadth statistics and prices
-- you're already pulling from public sources) — the point of RLS here
-- is just to make "anon can SELECT, nothing else" explicit rather than
-- accidentally wide open or accidentally blocked.
-- ---------------------------------------------------------------------

alter table platform_breadth enable row level security;
alter table market_prices enable row level security;
alter table alerts_sent enable row level security;
alter table iv_snapshots enable row level security;
alter table iv_proxy_map enable row level security;
alter table instrument_commentary enable row level security;
alter table instruments enable row level security;
alter table price_proxy_map enable row level security;
alter table fred_series enable row level security;
alter table fred_series_meta enable row level security;
alter table positions enable row level security;

drop policy if exists "anon can read platform_breadth" on platform_breadth;
create policy "anon can read platform_breadth" on platform_breadth for select to anon using (true);

drop policy if exists "anon can read market_prices" on market_prices;
create policy "anon can read market_prices" on market_prices for select to anon using (true);

drop policy if exists "anon can read alerts_sent" on alerts_sent;
create policy "anon can read alerts_sent" on alerts_sent for select to anon using (true);

drop policy if exists "anon can read iv_snapshots" on iv_snapshots;
create policy "anon can read iv_snapshots" on iv_snapshots for select to anon using (true);

drop policy if exists "anon can read iv_proxy_map" on iv_proxy_map;
create policy "anon can read iv_proxy_map" on iv_proxy_map for select to anon using (true);

drop policy if exists "anon can read instrument_commentary" on instrument_commentary;
create policy "anon can read instrument_commentary" on instrument_commentary for select to anon using (true);

drop policy if exists "anon can read instruments" on instruments;
create policy "anon can read instruments" on instruments for select to anon using (true);

drop policy if exists "anon can read price_proxy_map" on price_proxy_map;
create policy "anon can read price_proxy_map" on price_proxy_map for select to anon using (true);

drop policy if exists "anon can read fred_series" on fred_series;
create policy "anon can read fred_series" on fred_series for select to anon using (true);

drop policy if exists "anon can read fred_series_meta" on fred_series_meta;
create policy "anon can read fred_series_meta" on fred_series_meta for select to anon using (true);

-- Read-only for the dashboard, same as everything above — your positions
-- are written by push_positions.py using the service_role key (from your
-- own CSV), never by the browser/anon key.
drop policy if exists "anon can read positions" on positions;
create policy "anon can read positions" on positions for select to anon using (true);

grant select on
  platform_breadth, market_prices, alerts_sent, iv_snapshots, iv_proxy_map, instrument_commentary,
  instruments, price_proxy_map, fred_series, fred_series_meta, positions,
  v_net_reversal_bias, v_high_low_balance, v_panic_cycle_exposure,
  v_reversal_bias_wow_change, v_price_forward_return, v_scorecard, v_scorecard_wow, v_iv_vs_breadth,
  v_iv_rank, v_iv_rank_latest, v_price_moving_averages, v_price_moving_averages_latest,
  v_price_change_windows, v_signal_backtest, v_signal_backtest_summary,
  v_instrument_backtest, v_instrument_backtest_summary, v_fred_latest,
  v_fred_series_rank, v_fred_series_rank_latest, v_fred_spreads, v_fred_spreads_latest, v_position_pnl
  to anon;

-- ---------------------------------------------------------------------
-- A note on Supabase's newer key naming: if your project shows
-- "publishable key" / "secret key" instead of "anon key" / "service_role
-- key", these are the same roles under new names — publishable key
-- authenticates as `anon` (use it in dashboard.html), secret key has full
-- access bypassing RLS (use it in push_to_supabase.py and the n8n
-- workflows' SUPABASE_SERVICE_KEY). Worth confirming against Supabase's
-- own docs for your project rather than taking my word for it, since key
-- systems like this do change.
-- ---------------------------------------------------------------------
