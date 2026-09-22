# Weekly macro trend data

Structured replacement for Section 14 of the old `.txt` database. Two data
sources live here, kept separate because they're different grains:

1. **Your own per-market read** (QQQ, HYG, USO, ...) — `weekly_macro_trends.csv`
   / `weekly_macro_read.csv` / `add_week.py` / `study_trends.py`.
2. **The platform's own whole-market breadth summary** (% of Stocks/
   Currencies/Stock Indices/Bonds/Commodities/ETFs/Crypto showing each
   signal) — `platform_breadth.csv` / `add_breadth_week.py` /
   `study_breadth.py`. This is the one that actually answers "find macro
   trends" at the asset-class level, before narrowing to one ticker.
3. **Scorecard + forward tracker** — turns (2) into a documented, non-fitted
   call per category (`scorecard.py`), maps each category to a real
   instrument you'd check it against, and logs whether that instrument
   actually moved the way the call implied over the following 3 weeks
   (`market_data.py` + `forward_tracker.py` + `study_scorecard.py`). This
   is the backtest-as-it-accumulates layer — see below for why it can't be
   a real fitted model yet and what it becomes as more weeks land.

## Files — scorecard + forward tracker

- **scorecard.py** — reads `platform_breadth.csv`, computes a fixed,
  documented formula per (week_of, category): `score = 0.4×(bearish
  election % − bullish election %) + 0.4×(aggregate-high % − aggregate-low
  %) + 0.2×(panic cycle %)`, and a `call` (`CAUTION` / `NEUTRAL` /
  `CONSTRUCTIVE`, plus a `+VOLATILITY_FLAG` when panic-cycle % > 20). The
  thresholds (±8, 20) are a starting point I picked for being simple and
  symmetric, not fit to your data — there isn't enough of it to fit
  anything to yet. Change them in the script whenever you have a reason
  to. Also maps each category to the instrument(s) you actually trade:
  Stocks/Stock Indices → QQQ, Currencies → EUR/USD spot, Commodities →
  USO + GLD, Bonds → HYG + TLT, Crypto → BTC-USD. (ETFs has no dedicated
  proxy — QQQ/GLD/USO/HYG/TLT are themselves classified as ETFs on the
  platform, so it already overlaps the others.) Writes `scorecard.csv`.
- **market_data.py** — pulls real daily OHLCV (open/high/low/close/volume)
  for the 7 scorecard proxies **plus your full macro watchlist** — the
  instruments from your actual Socrates Watchlist screenshots (PLTR, MU,
  NASDAQ 100/Composite, NQ futures, the 10 global indices, gold/silver/oil
  futures, VIX, US 10yr yield, the dollar index, 10 FX crosses, ETH-USD),
  roughly 40 symbols total. **Run this on your own machine, not in this
  session** — confirmed the sandbox's outbound network doesn't reach Yahoo
  Finance (straight 403 policy denial, not a flaky timeout). Read the
  module docstring before trusting the output: I mapped each Watchlist
  display name to a Yahoo ticker from general knowledge of Yahoo's naming
  conventions, but couldn't verify a single one against live data from
  here. Every entry is tagged high/medium/low confidence; a few (Japan/
  Euro 10yr yield indices, the Binance-specific crypto pairs) have no
  Yahoo equivalent at all and are skipped on purpose, never guessed. The
  script prints a clear WARNING and skips (never fabricates) any symbol
  Yahoo doesn't recognize — read that output the first time you run it.
  Writes `market_prices.csv` (now with open/high/low/volume columns, not
  just close — `forward_tracker.py` and `push_to_supabase.py` still read
  it by column name, so this is additive, not breaking) — copy that file
  back into this folder after running it.
- **fred_data.py** — pulls point-in-time macro series from the St. Louis
  Fed (10yr/2yr Treasury, Fed funds rate, VIX, the dollar index, CPI, and
  — filling a gap `market_data.py` couldn't — Japan and Euro area 10-year
  government bond yields, via FRED's OECD-sourced series) using FRED's
  free public `fredgraph.csv` endpoint, no API key needed. **Also run this
  on your own machine, not in this session** — same network restriction
  as Yahoo Finance, confirmed directly (403 from this sandbox). Same
  confidence-tagging discipline as `market_data.py`: six series are "high"
  confidence (standard, well-known FRED IDs), the two OECD yield series
  are "medium" (a plausible, well-established ID pattern I couldn't verify
  live) — read the module docstring before trusting those two. Skips (does
  NOT write a fabricated row for) any FRED "." reading — a date with no
  observation posted yet, common for the most recent month of a monthly
  series. Writes `fred_series.csv` — copy back into this folder after
  running it, same as `market_prices.csv`.
- **forward_tracker.py** — joins `scorecard.csv` against
  `market_prices.csv`: for each week/category/proxy, finds the price at
  the signal date and ~21 days later ("3 weeks," matching Socrates' own
  language), computes the realized return, and marks each row `RESOLVED`
  (window has passed and we have the price) or `PENDING` (too soon) —
  never guesses a future price. Writes `tracker_results.csv`.
- **study_scorecard.py** — open in VS Code, run cell-by-cell. Average
  realized return by call, split by proxy symbol, a check on whether
  volatility-flagged weeks actually saw a wider price range, and a
  directional hit rate for CAUTION/CONSTRUCTIVE calls. It prints an
  explicit sample-size warning below 20 resolved rows and again below 50 —
  read those, don't skip past them once the numbers start looking tidy.
- **iv_snapshot.py** — the MVP for "is this still cheap?" (the gap the
  6-week report flagged: breadth can tell you direction, not whether
  options premium already prices it in). Pulls today's real implied
  volatility and put/call skew for the instrument you'd actually trade
  each category with — same run-on-your-own-machine rule as
  `market_data.py`, same reason (Yahoo Finance isn't reachable from this
  session). Appends to `iv_snapshot.csv`. Full detail — including why the
  proxy list swaps EURUSD=X→FXE and BTC-USD→IBIT for this script only, and
  why "OTM" here means ~5% away from spot rather than a real delta — is in
  the module's own docstring; read it before trusting the numbers.
  Currencies covers five real, optionable ETFs now (FXE/Euro, FXY/Yen,
  FXB/Pound, FXF/Franc, FXC/Canadian Dollar), not just FXE — added this
  round specifically because the old single-symbol read gave no way to
  compare, say, a Euro view against a Yen view under the same category
  breadth call. `market_data.py`'s `INSTRUMENT_UNIVERSE` carries the same
  five symbols now too, so each one also gets its own real price/SMA
  history, not just IV.
- **iv_vs_breadth.py** — the payoff: prints each category's latest breadth
  call next to today's IV/skew for its proxy, side by side. No file I/O
  besides reading the two CSVs above, so it runs anywhere, including in
  this session. Deliberately doesn't compute a cheap/rich verdict — there's
  no IV history yet to rank today's reading against. Once `iv_snapshot.csv`
  has a few weeks in it, that becomes a real extension (an IV Rank), not a
  guess dressed up as one.

### Why this isn't a "forecast model" yet, and when it can become one

You asked for a model that forecasts. With 2 weeks of paired Socrates+
market data (going to 6, plus whatever you backfill further), there's no
honest way to fit one — any regression or ML model trained on that few
points would just be memorizing noise and would look confident while
being wrong. What's built instead is a fixed rule (`scorecard.py`) that
never changes based on the data, plus a tracker that scores that fixed
rule against reality every week. Once `tracker_results.csv` has on the
order of 50+ RESOLVED rows spanning more than one kind of market week (not
50 rows from the same 7-week calm stretch), that's the point where fitting
actual weights — instead of the arbitrary 0.4/0.4/0.2 split — starts being
defensible rather than decorative. Until then, treat every number
`study_scorecard.py` prints as "what happened so far," not "what will
happen."

## Files — per-market read

- **weekly_macro_trends.csv** — long format, one row per market per week:
  `week_of, market, weekly_lwave, daily_lwave, pc_flag_date, reversal_above,
  reversal_below, source, notes`. Starts empty — no Jun–Aug 2026 backfill,
  by design.
- **weekly_macro_read.csv** — one row per week: `week_of, macro_read,
  drivers` — your own one-line narrative call, logged alongside the numbers
  so you can check your read against the alignment score later.
- **add_week.py** — edit the `WEEK_OF` / `WEEK_DATA` / `MACRO_READ` block at
  the top, then `python add_week.py`. Appends to both CSVs.
- **study_trends.py** — open in VS Code (Python extension installed),
  run cell-by-cell (`# %%` blocks). Pivots color by week × market, scores
  alignment, lists Panic-Cycle weeks and near-reversal rows, and draws a
  green/purple heatmap.

## Files — per-instrument Premium Overview Commentary

A third, different-grain data source: one specific market (e.g. "US
Dollar v Euro Adjusted Spot"), not a whole-category statistic, and a much
richer narrative report with dozens of numeric fields buried in fixed
template sentences.

- **parse_premium_commentary.py** — paste each report as a triple-quoted
  string into `RAW_REPORTS` (same pattern as `add_breadth_week.py`), run
  `python parse_premium_commentary.py`. Regex-matches against the exact
  template wording for each field (reversal levels, trend-change points,
  the full risk table, last close, YoY change, ECM target date) — tested
  against the real EUR/USD report you pasted, all 35 extractable fields
  came back correct. A field that doesn't match its expected sentence
  comes back blank, not guessed; the entire report's raw text is always
  kept in full regardless, in `instrument_commentary.csv`'s `raw_text`
  column, so nothing is ever lost even for what isn't parsed yet.
- **instrument_commentary.csv** — one row per (market, report_date).

**What isn't parsed, on purpose:** the Monthly Timing Table grid and the
Reversal Map / Fibonacci price-level tables from the same report (lower
value for a first pass, structurally different from sentence-matching —
they're sitting in `raw_text` if you need them). And separately, the
Weekly Timing Array color grid and Watchlist tables from the screenshots
you shared aren't parsed at all yet — two different reasons: the
Watchlist tables are only in a screenshot, and OCR-guessing numbers out of
an image isn't something I'll do (breaks the same "no inference" rule
everything else here follows) — if you can copy that table as text from
wherever it's rendered, it'll parse the same reliable way this does. The
color grid is different: I don't have a source for what each color means
per row (Aggregate/L-Wave/Empirical/Long Term/Trading Cycle/Direction
Change/Panic Cycle/Internal Volatility/Overnight Volatility each seem to
use their own blue/magenta/green/purple/yellow/red/cyan/grey scheme, not
the single GREEN=up/PURPLE=down rule the old Section 12 database used) —
tell me the legend and I'll build that parser properly instead of
guessing at it.

## Files — platform breadth summary

- **platform_breadth.csv** — long/tidy format, one row per
  (week_of, section, category, metric): `week_of, section, category,
  metric, count, pct`. `section` is one of `headline`, `reversal_system`,
  `timing_array`, `stochastics`, `indicating_ranges`, `gmw` — matching the
  automated email's own sections. Already seeded with the week of
  2026-09-11 you supplied.
- **add_breadth_week.py** — paste each week's full automated summary text
  as a triple-quoted string into `RAW_REPORTS` (you said you have 6 weeks
  of these), run `python add_breadth_week.py`. It's regex-based against
  the `"<N> Markets (or <pct>%)"` pattern, not position-based, so pasting
  straight from the email should parse cleanly; it skips (doesn't
  overwrite) a `week_of` already in the CSV. I ran it against the week you
  gave and cross-checked the implied per-category totals (count ÷ pct)
  come out consistent across every metric in a section — that's the
  signal the columns lined up with the right category and nothing got
  mis-parsed.
- **study_breadth.py** — open in VS Code, run cell-by-cell. Computes net
  bearish-vs-bullish reversal bias per category per week, Panic-Cycle
  exposure per category, aggregate-high-vs-low balance (broadly topping vs
  bottoming), the biggest week-over-week swing once you've got 2+ weeks
  in, and a line chart of net bearish bias by category over time.

## Rules `add_breadth_week.py` enforces

- Refuses to parse a report if it can't find the `close for Weekly
  YYYY-MM-DD` line — no guessing the week from the email's send-date text.
- A data row is only accepted if it finds exactly 7 `"N Markets (or P%)"`
  cells (one per category) — a malformed or partial row is skipped, not
  partially written.
- Won't duplicate a `week_of` already in the CSV; tells you it skipped
  rather than silently re-appending.

## Rules `add_week.py` enforces (carried over from Section 12 of the txt)

- `weekly_lwave` / `daily_lwave` must be `GREEN`, `PURPLE`, or blank — no
  other value. This is the absolute color rule; the script rejects
  anything else rather than guessing what you meant.
- Any row with real data must carry a `source` (image number, module, or
  premium-text date). A data-but-no-source row is rejected, not written.
- Blank means blank. Don't backfill a market's row from last week's value
  or from another market's read — leave it `""` and move on.
- Re-running for a `week_of` already in the file appends rather than
  overwrites, so you don't lose a prior entry by accident — dedupe by hand
  in the CSV or in VS Code if that happens.

## Weekly routine

1. Log this week's GMW / stress gauges / arrays wherever you're keeping
   that (the reference `.md` doc, or your own notes) — same as before.
2. Fill in `add_week.py`'s `WEEK_DATA` from that read, one dict per market,
   citing the source for each.
3. Set `MACRO_READ` to your one-line call (`"aligned risk-off"`, `"mixed"`,
   `"insufficient data"`, etc.) and `DRIVERS` to what drove it.
4. `python add_week.py`.
5. Open `study_trends.py`, run the cells, see whether the alignment score
   and heatmap agree with your `MACRO_READ` call — that's the check on
   your own read, not just a data entry step.
6. Paste that week's platform breadth email into `add_breadth_week.py`'s
   `RAW_REPORTS`, run it, then run `study_breadth.py` to see which asset
   class actually moved — that's the macro-trend scan pointing you at
   which market to pull specific data for next (per-market table above).
7. `python scorecard.py` to refresh the rule-based call for every week on
   file. On your own machine: `python market_data.py` (pulls fresh
   prices), copy `market_prices.csv` back into this folder, then
   `python forward_tracker.py` here to refresh `tracker_results.csv`.
   Open `study_scorecard.py` to see where the calls stand.
8. On your own machine: `python iv_snapshot.py` (needs `yfinance`, same as
   `market_data.py`), copy `iv_snapshot.csv` back into this folder, then
   `python iv_vs_breadth.py` here to see breadth and options pricing side
   by side for every category.

## Setup (once)

```
pip install pandas matplotlib
```
`market_data.py` and `iv_snapshot.py` additionally need `pip install
yfinance` — on your own machine, per the notes above.

Any spreadsheet tool or `pandas.read_csv` also opens these directly if you
want to look without running the script.
