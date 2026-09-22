# Socrates → Supabase → Yahoo Finance, in n8n

Replaces the local Python/CSV pipeline entirely, per what you asked for.
Three importable workflows, one Supabase schema, a self-contained
dashboard file, and a loader to get that dashboard showing real data
today. What's genuinely tested below vs. what I could only test the shape
of — read that section before trusting this in production.

## See the dashboard today (do this first)

You already have a Supabase project. This is the fast path — it doesn't
need any n8n workflow running yet:

1. Run `supabase_schema.sql` in your Supabase project's SQL editor (once).
2. Open `push_to_supabase.py` in a text editor, fill in `SUPABASE_URL` and
   `SUPABASE_SECRET_KEY` near the top (Project Settings → API — the
   **secret** key, not publishable; see the key-naming note in
   `supabase_schema.sql` if your project shows different names than that).
   **Never paste that key into chat with me or anyone** — fill it in
   locally only.
3. `python push_to_supabase.py` — pushes your existing
   `platform_breadth.csv` and `iv_snapshot.csv` into Supabase. Safe to
   re-run any time you add more weeks or snapshots to those CSVs. It now
   prints the row count and date range of what it's about to push, right
   before pushing — check that line matches what you expect before
   trusting the run.
4. Open `dashboard.html` in a text editor, fill in `SUPABASE_URL` and the
   **publishable** key (same page, the other key) near the top of the
   `<script>` block. Save, open the file in a browser, leave the tab open.
5. Going forward, run `update_iv.sh` regularly (daily if you want tight
   resolution, weekly at minimum) to build up real IV history — that's
   what the dashboard's "IV rank" needs to become meaningful. See
   "IV rank — why it needs repetition, not a bigger pull" below.

The n8n workflows below are what keeps this updating automatically going
forward — set those up when you're ready; the dashboard doesn't need them
to show you something real right now.

## IV rank — why it needs repetition, not a bigger pull

"Is this still cheap?" is a relative question — today's IV against its own
recent range — and there's no shortcut to that history. Yahoo Finance
doesn't expose historical option chains, so `iv_snapshot.py` can only ever
tell you *today's* IV; the only way to get a real history is to actually
run it on enough different days. `v_iv_rank_latest` (new view in
`supabase_schema.sql`) computes a genuine percentile from whatever
`iv_snapshots` history has accumulated so far, and updates itself
automatically as more days land — no separate backfill step, and nothing
fabricated in between. Until a symbol has at least 4 readings, the
dashboard shows "building history (n=…)" instead of a percentile, on
purpose, rather than a number that looks more precise than it is.

`update_iv.sh` is a one-command wrapper: it runs `iv_snapshot.py` (pulls
today's IV/skew) then `push_to_supabase.py` (pushes everything) in one
go. Safe to run more than once the same day — it just skips what's
already there. The more consistently you run it, the sooner IV rank
becomes something you can actually trust.

## What's here

- **supabase_schema.sql** — run once in the Supabase SQL editor. Creates
  `platform_breadth`, `market_prices` (now with `open`/`high`/`low`/
  `volume` columns, added via `alter table ... add column if not exists`
  so it's safe on a table you already have), `alerts_sent`, `iv_snapshots`,
  `iv_proxy_map` (now covering all five Currencies ETFs — FXE, FXY, FXB,
  FXF, FXC — not just FXE, see "FX ETFs" below), `instrument_commentary`,
  `instruments` (a reference table of ~45 symbols — display name, broad
  group, and a high/medium/low confidence tag on the ticker mapping,
  mirroring `market_data.py`'s `INSTRUMENT_UNIVERSE`), `price_proxy_map`
  (the same category→instrument mapping as `scorecard.py`'s
  `CATEGORY_PROXIES`, now in the database so SQL can join on it too), and
  `fred_series`/`fred_series_meta` (point-in-time macro data — see the
  FRED section below) tables, plus eighteen views — the "start tracking
  trends" layer, including `v_price_moving_averages`/
  `v_price_moving_averages_latest` (10- and 20-observation SMAs, computed
  over however many real rows exist per symbol rather than a fixed
  calendar window — an `observations_N` column says how much history
  actually backs each average), `v_price_change_windows` (weekly/monthly %
  change per symbol via `lag(close, 5)`/`lag(close, 21)`, joined into
  `v_price_moving_averages_latest` as `pct_change_1wk`/`pct_change_1mo`),
  `v_signal_backtest`/`v_signal_backtest_summary` (what a category's ONE
  canonical price proxy actually did over the ~15 sessions following each
  breadth call), `v_instrument_backtest`/`v_instrument_backtest_summary`
  (the same idea, but per OPTIONABLE instrument via `iv_proxy_map` instead
  of one proxy per category — see "Instrument decision panel" below, read
  the comment in this file before trusting its numbers, same n-gating
  discipline as `v_signal_backtest_summary`), `v_fred_latest` (latest
  reading + change per FRED series), and `v_fred_series_rank`/
  `v_fred_series_rank_latest` (any FRED series' current reading as a
  percentile of its OWN history — same `percent_rank()` formula as
  `v_iv_rank`/`v_iv_rank_latest`, just applied to `fred_series` instead of
  `iv_snapshots`; this is what powers the VIX headline card — see "VIX
  headline & Opportunity Finder" below). Query these directly rather than
  recomputing the logic elsewhere. Also enables RLS and grants the
  `anon`/publishable key read-only access, which is what `dashboard.html`
  uses. **If you already ran an earlier version of this file**, re-run
  it — it's safe to run again from any prior state and will add the new
  tables/views/policies.

  One real bug from an earlier round, now fixed: every view in this file
  is preceded by `drop view if exists ... cascade;`. That's there because
  Postgres's `create or replace view` can only *add trailing columns* to
  an existing view — it refuses to reorder or insert a column in the
  middle (error `42P16`, "cannot change name of view column"). This
  file's views have grown their column lists across rounds (for example
  `v_price_moving_averages_latest` gained a `confidence` column ahead of
  `date`), so re-running an earlier version of this file without the
  `drop view` guard hit exactly that error for anyone re-running it
  against a database that already had an older view live. I reproduced
  the exact error locally (built a throwaway Postgres database seeded
  with the older view shape, then re-applied the newer file on top of it
  to confirm the same `42P16` error), then added the `drop view ...
  cascade` guards and re-verified the fixed file applies cleanly three
  ways: on a fresh empty database, re-applied on top of the simulated
  older state, and re-applied a second time on top of itself. Tables are
  unaffected by any of this — they use `create table if not exists` +
  `alter table ... add column if not exists`, which don't have this
  restriction. Net effect: this file is now safe to re-run any number of
  times, from any prior state, going forward.

  I ran the entire file against a real local Postgres (not just
  eyeballed it) before shipping this round, including hand-verifying the
  backtest and FRED views' math against synthetic data — see the testing
  section below.
- **push_to_supabase.py** — one-time (and safely re-runnable) loader that
  pushes `platform_breadth.csv`, `iv_snapshot.csv`, `market_prices.csv`,
  and now `fred_series.csv` into your Supabase project, so the dashboard
  has real data today without waiting on the n8n workflows. Runs locally
  so your secret key never leaves your machine. Prints the row count and
  date range it's about to push before pushing, as a sanity check.
  `market_prices` rows tolerate blank open/high/low/volume (some symbols
  legitimately won't have all of them) — blank stays `null`, never a
  guessed value. `fred_series` rows with a blank value (FRED's "." — no
  reading posted yet) are dropped entirely rather than pushed as a
  fabricated null row. Detail above and in the file's own docstring.
- **fred_data.py** (in the `socrates_data` folder, alongside
  `market_data.py`) — pulls point-in-time macro series (10-year Treasury,
  Fed funds rate, VIX, dollar index, CPI, and — filling a real gap
  `market_data.py` couldn't — Japan and Euro area 10-year government
  yields) from the St. Louis Fed's free `fredgraph.csv` endpoint. No API
  key needed. Same confidence-tagging discipline as `market_data.py`:
  the two OECD-sourced yield series are flagged "medium" confidence since
  their exact FRED series IDs weren't verified against live data from
  this sandbox (FRED is outside its network allowlist, same restriction
  as Yahoo Finance). Run it the same way: `python fred_data.py`, then
  `push_to_supabase.py` picks up its output automatically.
  **On "the FRED data isn't working, I didn't use my API key":**
  `fred_data.py` doesn't use or need an API key — it pulls from FRED's
  free, public `fredgraph.csv` endpoint (no auth at all), so a missing key
  isn't the cause. If a card shows "No reading yet" or the panel is blank,
  the two most likely causes are (1) `fred_data.py` hasn't actually been
  run + pushed yet on this machine — run `python fred_data.py` from the
  `socrates_data` folder and check its own stdout for a per-series row
  count before assuming it's broken, or (2) this sandbox's network
  allowlist blocked `fred.stlouisfed.org` when I tested it here (see
  above) — your own machine may not have that restriction, but if it
  does, that's an environment/firewall issue, not a code bug. Tell me the
  actual error text or exact symptom (blank card vs. Python traceback vs.
  stale date) and I can narrow it further.
- **update_iv.sh** — one command that runs `iv_snapshot.py` then
  `push_to_supabase.py`, so building real IV history (and therefore IV
  rank) is one line instead of two. Run it regularly — see "IV rank" above.
- **FX ETFs (this round) — market_data.py and iv_snapshot.py**: Currencies
  used to mean one instrument, FXE (Euro), for IV/skew, while price/trend
  only ever tracked the spot rate (`EURUSD=X`), never an ETF at all. Now
  `market_data.py`'s `INSTRUMENT_UNIVERSE` and `iv_snapshot.py`'s
  `OPTIONABLE_PROXIES` both carry the same five real, liquid, optionable
  Invesco CurrencyShares ETFs — FXE (Euro), FXY (Yen), FXB (Pound), FXF
  (Franc), FXC (Canadian Dollar) — so each one gets its own real price
  history AND its own real IV/skew, not a borrowed spot-rate read. This is
  what makes the Instrument Decision Panel's FXE-vs-FXY comparison
  possible — before this round, FXY had no data anywhere in this system.
  SGD, TWD, INR, and CNY don't have a comparably liquid listed-options
  ETF, so they stay spot-only, same as before.
- **Instrument decision panel (dashboard.html, this round)** — answers
  "is this specific instrument worth a look" for one symbol at a time:
  pick it from a dropdown (defaults to FXE) and see its category's breadth
  call, today's IV/skew/rank, its own price trend, and what this exact
  symbol has actually done historically after this same call — side by
  side, instead of cross-referencing four separate panels by hand. Reads
  `v_instrument_backtest_summary` (see above) for the per-symbol backtest,
  and gracefully shows what's actually missing (e.g. "no price history
  tracked" for FXY until you run `market_data.py` with it added) rather
  than a blank or a crash. Like every other panel on this page, it states
  facts and never recommends a trade.
- **VIX headline & Opportunity Finder (dashboard.html, this round)** —
  built directly off your "where's the next opportunity to buy premium
  cheap, I'm looking for ~2, for a 2-4 week trade" question.
  - **VIX headline**: one card, promoted to the very top of the page
    (above the trend chart, above everything), showing VIX's own reading
    against its OWN history's percentile (`v_fred_series_rank_latest`) —
    e.g. "62nd pct (n=11)" — never against any single instrument's IV,
    because different asset classes sit on structurally different
    volatility scales and comparing them directly is misleading (the
    card's own caption says this explicitly). Read this as "is the
    overall market regime calm or stressed right now," separate from "is
    FXE's or FXY's own premium cheap right now" (that's the Decision
    Panel / Opportunity Finder's job, per-instrument). Shows "building
    history (n=…)" instead of a fabricated percentile below 4
    observations, same discipline as IV rank, and "No VIX reading yet"
    with a pointer to `fred_data.py` when there's no data at all rather
    than a blank card.
  - **Opportunity Finder**: ranks every instrument that currently has BOTH
    a live/fresh breadth signal (its category's call just crossed, or
    tripped the panic-cycle volatility flag this week) AND real IV data,
    combining three things into one score so all three actually matter
    (see the "composite score, not lexicographic sort" note below):
    1. **Cheap IV, cross-sectionally** — its rank (1 = cheapest) among
       every symbol currently tracked on IV, same ranking the Cheapest IV
       panel already uses.
    2. **Freshness** — a small penalty if the category's call didn't
       actually change this week (an "active but stale" call ranks worse
       than one that just crossed or tripped the volatility flag).
    3. **Trend exhaustion** — a small penalty if price is already >5%
       away from its own 20-day moving average
       (`OPP_EXTENDED_THRESHOLD_PCT` in the code) — a plain "has this
       already run, may be less room left" flag, not a scientific
       reversal signal.
    The top 2 are shown as full cards (skew, translated into which side —
    calls or puts — is currently the cheaper one to buy convexity on;
    trend; that exact instrument's own backtest evidence where enough
    history exists); the rest of the field that still qualifies is listed
    below in a compact table so you can see what almost made the cut. A
    symbol mapped to more than one signal-passing category (rare, but
    possible) is de-duplicated to its higher-priority category rather
    than shown twice. Like every other panel here, it narrows the field
    and states facts — it does not pick a trade, and says so in its own
    caveat line.
  - **Design note — composite score, not a lexicographic sort:** the
    first draft of the ranking used cheap-IV-rank as the primary sort key
    with freshness and trend-exhaustion as tiebreakers, only applied when
    two candidates had the exact same rank. Since the cheap-IV rank is a
    dense 1..N ranking (no ties are possible across real symbols), that
    made the other two criteria dead code — they could never actually
    change the order, silently failing to deliver "combine three
    factors" the way you asked for it. I caught this before it shipped
    and replaced it with an additive score (rank + a small freshness
    penalty + a small trend-exhaustion penalty, lower is better,
    alphabetical as the final tiebreak) so all three criteria genuinely
    influence the result — this is unit-tested directly
    (`test_opportunities.js`'s Scenario A is built specifically to prove
    a worse-raw-rank symbol can still outrank a better-raw-rank one
    purely because of the freshness penalty).
- **workflow_1_socrates_breadth_ingestion.json** — Webhook → parse → insert.
  POST `{ "report_text": "<the full pasted weekly summary>" }` to the
  webhook and it lands in `platform_breadth`.
- **workflow_2_yahoo_finance_price_sync.json** — Schedule (Fridays) →
  Yahoo Finance chart API per symbol → reshape → upsert into
  `market_prices`. Symbols: QQQ, EURUSD=X, USO, GLD, HYG, TLT, BTC-USD —
  same category→instrument mapping as before (Stocks/Stock Indices→QQQ,
  Currencies→EUR/USD spot, Commodities→USO+GLD, Bonds→HYG+TLT,
  Crypto→BTC-USD).
- **workflow_3_pattern_alerts.json** — Daily schedule → reads the latest
  week's `v_scorecard_wow` → diffs against `alerts_sent` → sends a Telegram
  message for any category with a genuinely NEW signal (a regime flip, a
  freshly-triggered volatility flag, or a big single-week score swing) →
  records what it sent so it never repeats itself. Detail in its own
  section below.
- **dashboard.html** — a live, auto-refreshing desk view. Not a Claude
  Artifact (see "Why this isn't a published Claude page" below) — a plain
  HTML file you open in a browser and keep open, or host yourself. Polls
  Supabase directly every 60 seconds using the read-only `anon`/
  publishable key. Now also shows each category's ATM IV, put/call skew,
  and IV rank (from `iv_snapshots`/`v_iv_rank_latest`) right under its
  breadth call and score — "what's the call" and "is it still cheap"
  side by side, same pairing `iv_vs_breadth.py` does locally. Above the
  category cards, a real 6-week trend chart (one line per category, with
  CAUTION/CONSTRUCTIVE reference lines) plus a "biggest movers this week"
  list — the actual trend/convexity-scan view, not just the small
  per-card sparkline. Below that, a "Convexity watch" panel — the first
  panel that combines breadth and IV rather than showing them side by
  side: a category is flagged "watch" only when its breadth call crossed
  a threshold (or tripped the panic-cycle volatility flag) THIS week AND
  its optionable proxy is in the cheaper half of everything currently
  tracked on IV, cross-sectionally (reuses the Cheapest IV panel's own
  ranking, so it works even before enough history exists for a real IV
  rank). It's deliberately descriptive, not a trade recommendation — the
  breadth score is a composite (net reversal bias + net high/low +
  panic-cycle exposure), not a price-direction forecast, so this panel
  never asserts which way price should move, only that a pattern worth a
  closer look is sitting there. Below the category cards, an instrument watchlist
  (from `v_price_moving_averages_latest`) covering the ~40-symbol macro
  universe extracted from your Watchlist screenshots — grouped by
  Tech/Momentum, Global Indices, Commodities, Rates, Volatility, FX, and
  Crypto, each row sorted within its group by biggest 1-week move first,
  showing close, 1-week/1-month % change, price vs. its own 10-/20-session
  moving average (honestly flagged "thin" when less history backs it than
  the window needs), and volume. A non-"high" confidence ticker mapping
  (see `market_data.py`'s docstring) shows inline on its row rather than
  being hidden. A **VIX headline card** now sits at the very top of the
  page, above everything else (see "VIX headline & Opportunity Finder"
  below) — the market-wide volatility read, promoted to the most prominent
  spot rather than buried inside the FRED panel below. A Macro Series (FRED) panel sits above the category cards,
  one card per series from `v_fred_latest` with its latest reading and
  change from its prior reading (no up/down color judgment — a yield
  rising isn't "good" or "bad" the way a price gain is, so this stays
  neutral unlike the price-change coloring elsewhere on the page). A
  Signal Backtest panel sits below the watchlist, reading
  `v_signal_backtest_summary` — dimmed, unsorted rows below 8 observations
  ("n=…, building") rather than a misleadingly confident average. **Click
  any row** in the Instrument Watchlist, Cheapest IV panel, or a FRED
  card to expand its full history as a chart, fetched on demand (never
  loaded upfront for all ~50 symbols/series at once) — price and volume
  render as two separate charts, never combined on one axis with two
  scales, same for IV and skew; a symbol's own price + its 10d/20d moving
  averages DO share one chart, since those are all the same unit (price),
  not a dual-axis violation. An expanded row stays open across the
  60-second auto-refresh instead of silently collapsing on you mid-review.
- **parse_breadth_report.js**, **reshape_yahoo_response.js**,
  **detect_new_alerts.js** — the standalone versions of the Code nodes'
  logic, kept alongside the workflow JSON so you can re-test them with
  plain `node` if you ever change the rules, without needing n8n running
  to check your work.

## Why this isn't a published Claude page

I looked into building the live dashboard as a Claude Artifact (a hosted
page with its own claude.ai link) instead of a file you run yourself —
it would've meant no setup on your end. It doesn't work for this: a
published Artifact's browser sandbox blocks it from calling arbitrary
external services like your Supabase project directly (it can only reach
a small CDN allowlist, plus your own claude.ai-connected connectors,
which Supabase isn't). `dashboard.html` is the honest version — a file
that runs in your own browser, with no such restriction, so it can poll
your database directly. The tradeoff is it only updates while you keep
that tab open, and there's no shareable link unless you host the file
yourself somewhere.

**On "shareable — publish as a hosted page":** this is what you picked
when I asked about sharing intent, so to be direct about the actual
tradeoff — a Claude-hosted link (claude.ai/...) is off the table for the
reason above, not a policy choice I could configure around. What does
work, since `dashboard.html` is a single self-contained file that only
talks to Supabase from the browser (no server-side code of its own to
run): drop it on any static host — Vercel, Netlify, GitHub Pages, or even
Supabase's own Storage — and you get a real, always-on shareable URL,
with the same 60-second auto-refresh, that works for anyone you send it
to without them needing to run anything locally. Since it uses the
read-only `anon`/publishable Supabase key (never your secret key), it's
safe to put on a public host as-is. I can walk you through whichever of
those you'd prefer once you confirm you want to go that route.

## What I actually tested vs. what I could only shape-test

**Tested for real:** the breadth-report parser. I ran it (via `node`)
against both your Sep 11 and Sep 18 2026 reports, then pulled the *exact*
JSON string out of `workflow_1_...json` and ran that too — not a
copy I assumed matched, the literal string that will execute inside the
Code node. Both produced 105 rows, and the same cross-check as before held
(dividing each row's count by its pct gives a consistent implied total per
category — Stocks 554, Currencies 108, Stock Indices 186, Bonds 176,
Commodities 74, ETFs 189, Crypto 6 — meaning nothing got shifted into the
wrong category column).

**Shape-tested only, not tested live:** the Yahoo Finance fetch and
reshape. I wrote `reshape_yahoo_response.js` against Yahoo's documented v8
chart-API response shape and ran it against a synthetic response matching
that shape — it correctly pulled the symbol back out of `meta.symbol` and
skipped a null close. What I could *not* do is call the real endpoint:
this session's own network is on an allowlist that doesn't include Yahoo
Finance (I confirmed a straight 403 policy denial when I tried, not a
timeout). Your n8n host might reach it fine — or might hit the same wall,
since Yahoo's endpoint is unofficial (no API key, no SLA) and known to
block requests from datacenter/cloud IP ranges specifically. **First thing
to check after import: manually execute workflow 2 once and look at what
"Fetch Yahoo Chart Data" actually returns.** If it's a 403 or an HTML
error page instead of JSON, swap that node's URL for:
- `https://stooq.com/q/d/l/?s={symbol}&i=d` (free CSV, no key, historically
  more tolerant of automated requests) — different response shape, so
  Reshape needs adjusting to parse CSV instead of the Yahoo JSON shape; or
- your EODHD or Alpha Vantage key from the Economic Machine stack — an
  official, paid API, the most reliable option of the three if Yahoo
  gives you trouble.

**Tested for real (new this round):** `detect_new_alerts.js` — the regime
flip / volatility flag / big-swing detection at the core of workflow 3. I
ran the standalone file, then pulled the exact embedded string out of
`workflow_3_pattern_alerts.json` and ran that too (not a copy I assumed
matched), against synthetic rows covering a regime flip, a big swing with
no call change, a category with no signal, and a category that's already
in `alerts_sent` (which must get suppressed even though it also has a
fresh volatility flag). All four cases came out correct. I also ran your
real 6-week `scorecard.csv` numbers through the underlying formula by hand
as a sanity check — Crypto genuinely flips NEUTRAL→CAUTION between Sep 11
and Sep 18 with a +20 point swing, which is exactly the kind of thing this
workflow exists to catch, so there's already a real signal in your data
this would have surfaced.

**Shape-tested only, not tested live:** the Telegram send. I don't have a
bot token to test against, so `Send Telegram Alert` is built against the
documented Bot API (`POST https://api.telegram.org/bot<TOKEN>/sendMessage`
with `chat_id`, `text`, `parse_mode`) but not fired for real. Same for
`dashboard.html`'s Supabase calls — I rendered it in a headless DOM against
synthetic responses shaped exactly like `v_scorecard_wow`, `alerts_sent`,
and `market_prices` rows (checked the right category gets the CAUTION
color, the right proxy price shows against the right category, the
volatility-flag badge appears, and a fetch failure surfaces the real HTTP
error instead of failing silently) — but never against your actual
project. **First things to check after setup:** run workflow 3 manually
once and confirm the Telegram message actually arrives; open
`dashboard.html` and confirm it says "updated HH:MM:SS" rather than
showing the red error banner.

**Tested for real (this round, and this is new):** the whole
`supabase_schema.sql` file, against an actual local Postgres — not just
read over for syntax errors. I installed Postgres, created the `anon`
role Supabase provides automatically (so RLS policies would actually
resolve), ran every `create table` / `create view` / `create policy` /
`grant` in the file, loaded your real 6 weeks of `platform_breadth.csv`,
and cross-checked `v_scorecard`'s SQL formula against `scorecard.py`'s
Python output row by row — all 42 (week, category) rows matched exactly,
which proves the two versions of the same formula haven't drifted apart,
not just that both "look right." I also caught a real bug this way before
it reached you: `iv_snapshot.py` was fetching QQQ twice (once per category
it represents) and would have violated `iv_snapshots`' uniqueness
constraint — fixed in both the script and the schema (see `iv_snapshots`'
comment in `supabase_schema.sql`) and re-verified against your actual
`iv_vs_breadth.py` output from today. `push_to_supabase.py` was tested
against a mock local server that records exactly what it received — real
request URLs, headers, `on_conflict` query params, and JSON bodies, plus
a real 409 error response to confirm failures surface instead of getting
swallowed.

**Tested for real:** `parse_premium_commentary.py`, against the actual
EUR/USD report you pasted — all 35 extractable fields came back correct
against a by-hand check of the source text (reversal levels, trend-change
points, the full risk table, last close, YoY change, ECM target date). Not
parsed: the Weekly Timing Array color grid and Watchlist tables from your
screenshots — different format, and for the color grid specifically, I
don't have a source for what each color (blue/magenta/yellow/red/cyan/
grey, seemingly a different meaning per row) means, so I'm not going to
guess. If you have the legend, or can get the Watchlist tables as copyable
text, I can extend this properly.

**Tested for real (this round — FRED, backtest, and interactivity):**
`v_signal_backtest`, `v_signal_backtest_summary`, and `v_fred_latest`
against a real local Postgres, with a synthetic `platform_breadth`/
`market_prices` dataset built so I could hand-calculate the expected
forward-return numbers first — both the CAUTION-week and NEUTRAL-week
rows matched my hand math to the cent. `fred_data.py`'s CSV parsing
(missing "." readings skipped rather than fabricated, a network failure
returning an empty result rather than raising, a non-CSV/broken response
handled the same way, the 730-day lookback trim) was tested by mocking
the network call — same reason as `market_data.py`, FRED's own domain is
outside this sandbox's allowlist, confirmed with a direct curl (403).
The dashboard's new panels and interactivity — Convexity Watch, Macro
Series (FRED), Signal Backtest, and the click-to-expand drill-down charts
on the Cheapest IV, Watchlist, and FRED panels — got the same headless-DOM
treatment as everything else on the page (111 checks across 8 test files
at last count), PLUS something new: I rendered the actual page in a real
headless Chromium browser and looked at screenshots of it, since the
drill-down charts are exactly the kind of thing that can be "correct" by
every string assertion and still visually broken (overlapping labels, a
chart that's the wrong size, a legend that doesn't line up). One thing
that test caught before it reached you: an expanded chart was silently
collapsing every 60 seconds when the page auto-refreshed, because the
refresh rebuilds each panel's HTML from scratch — fixed by tracking which
rows are open outside the DOM and re-opening (and re-fetching) them after
every render, which is now itself a tested behavior, not just a fix I
assumed worked.

**A real bug you actually hit, now fixed:** running the FRED/backtest
round of `supabase_schema.sql` in your Supabase SQL editor failed with
`ERROR: 42P16: cannot change name of view column "date" to "confidence"`.
Root cause: Postgres's `create or replace view` can only append trailing
columns to an existing view — it refuses to reorder or insert a column
in the middle, and `v_price_moving_averages_latest` had gained a
`confidence` column inserted ahead of `date` rather than appended at the
end. Every Postgres check I'd done up to that point applied the schema
file to a freshly created, empty database — never to a database that
already had an older version of a view live, which is the actual
situation any re-run is in. That gap in how I was testing is exactly
what let this through. Fixed now: reproduced the exact error locally
(seeded a throwaway Postgres database with the older view shape, then
re-applied the current file on top of it and got the identical `42P16`
error), added `drop view if exists ... cascade;` immediately before
every `create or replace view` in the file (checked that every view only
depends on views created earlier in the same file, so a cascade drop
never removes something the script doesn't go on to recreate a few lines
later), and re-verified the fixed file three ways: fresh empty database,
re-applied on top of the simulated older state, and re-applied a second
time on top of itself. All three came back clean. Going forward I'll
test schema re-runs against a database seeded with an older schema
version, not just fresh applies.

**Tested for real (this round — FX ETFs and the decision panel):**
`v_instrument_backtest`/`v_instrument_backtest_summary` against a real
local Postgres, seeded with 40 consecutive daily rows each for a rising
FXE and a falling FXY under the same two Currencies CAUTION weeks, so the
two instruments' forward returns were hand-calculable in advance
(FXE: +3.00%, then +2.96%; FXY: -2.50%, then -2.53%). The view's output
matched those hand-calculated numbers exactly, confirming the per-symbol
join (via `iv_proxy_map` rather than `price_proxy_map`) is pulling each
instrument's own price history, not silently reusing the category's
canonical proxy. The dashboard's new Instrument Decision Panel got the
same headless-DOM + real-Chromium-screenshot treatment as the rest of the
page (29 checks in its own test file, all passing) — including
deliberately mocking FXY as present in `iv_snapshots` but ABSENT from
`instruments` and `v_price_moving_averages_latest`, since that's the real
state FXY was in before this round (IV/skew trackable, price history not
yet), to confirm the panel shows "no price history tracked" rather than a
blank tile or a JS error. Switching the dropdown was checked to fire zero
additional network requests (renders from the same bulk-fetched data
every other panel already uses), and the selected symbol was checked to
survive an auto-refresh cycle rather than silently resetting to the FXE
default every 60 seconds.

**Tested for real (this round — VIX headline and Opportunity Finder):**
`v_fred_series_rank`/`v_fred_series_rank_latest` against a real local
Postgres, hand-verified with 5 synthetic VIX values (12, 15, 18, 22, 30)
— the view's percentiles came back exactly 0/25/50/75/100, matching hand
math. The VIX headline card got its own headless-DOM test file
(`test_vix_headline.js`, 12 checks, all passing) covering a rich/elevated
reading, a cheap/quiet reading, thin history (n<4, shows "building
history" rather than a fabricated percentile), and no data at all (shows
guidance pointing at `fred_data.py` rather than a blank card). The
Opportunity Finder got a more involved test (`test_opportunities.js`, 22
checks) built around a hand-worked scenario: 4 candidate instruments
(FXE, FXY, QQQ via two different categories, HYG) with a hand-calculated
expected composite score and ranking order, plus a category-exclusion
case (a NEUTRAL category with no signal must never contribute a
candidate), a no-IV-snapshot exclusion case, and a dedup case (one symbol
mapped to two signal-passing categories must keep only the
higher-priority one). Writing this test surfaced two real bugs in the
test itself, not the implementation, both from the same root cause
(checking the whole rendered panel string instead of one candidate's own
card, so a wrong assertion could pass by accident-matching a different
candidate's card): an assertion about FXE's skew direction and one about
FXY's skew direction were each backwards relative to the actual
`skew = otm_put_iv - otm_call_iv` definition, and both had been silently
passing by matching each other's (correct) card content instead of their
own. Fixed by properly scoping each check to its own candidate's HTML
slice (`extractCard()` in the test file) and correcting the expected
direction for each — confirmed by manually inspecting the real rendered
HTML for both cards before changing the assertions, and by the Playwright
screenshot below, not just by making the test pass. Also confirmed the
existing 111+ checks across the other test files still all pass with the
two new fetch calls (`v_fred_series_rank_latest`) mocked in — 232 checks
total (56 Python + 176 JS) across the full suite as of this round.

**Two small fixes (this round, from real dashboard screenshots you sent
back after using it):**
- **Skew now reads in plain language everywhere, not a signed number.**
  The Cheapest IV panel, the category cards, and the Decision Panel used
  to show a bare `skew -8.02`, which is exactly the kind of thing that
  needs mental translation. All three now lead with the actual read —
  "calls expensive · puts cheap" or "puts expensive · calls cheap" — via
  one shared `skewLeanLabel()` function, so it's impossible for the three
  panels to describe the same skew differently. The raw number isn't
  gone, it's just demoted to a hover tooltip. (The Opportunity Finder
  already did this; this brings the rest of the page in line with it.)
- **FX-ETF instruments (FXE/FXY/FXB/FXF/FXC) now sit in their own proper
  watchlist group next to FX (spot).** They were already tagged
  `group_label: "FX-ETF"` in `instruments`/`market_data.py`, but
  `dashboard.html`'s `GROUP_ORDER`/`GROUP_COLORS` never listed that
  group — so it fell through to the unordered, default-grey tail of the
  watchlist instead of sitting next to its spot-rate sibling, which is
  almost certainly why it read as miscategorized. Fixed by adding
  `"FX-ETF"` to both lists, right after `"FX"`. Both fixes are covered by
  new/updated checks in `test_iv_rank.js`, `test_cheapest_iv.js`,
  `test_decision_panel.js`, and `test_watchlist.js` — 241 checks total
  now (56 Python + 185 JS).

- **50-day moving average + "Breadth call vs. actual price trend" panel
  (this round, from "I need directional data" and "the dashboard is
  telling me short FXE, is that actually confirmed").** New
  `sma_50`/`observations_50` columns on `v_price_moving_averages`/
  `v_price_moving_averages_latest` (same append-only, honest-observation-
  count pattern as `sma_10`/`sma_20` — see the schema comment). A new
  panel, right under the Opportunity Finder, shows each category's
  *current* breadth call next to its canonical price proxy's real,
  measured trend: UPTREND/DOWNTREND from price vs. its own 50-day SMA
  (`MIN_OBSERVATIONS_FOR_TREND = 5` real sessions before it'll call a
  trend at all — below that it says so honestly rather than reading noise
  as a signal), with the exact observation count shown whenever the
  window's still partial (`n=12/50`, not silently padded to look like a
  full 50-day read). A category with more than one price proxy (Bonds:
  HYG and TLT) shows both, independently — one can read uptrend while the
  other reads downtrend under the same call.

  **Deliberately does NOT say whether the call and the trend "agree."**
  This was a real design decision, not an oversight: the breadth score
  (`scorecard.py`) is a composite of net reversal bias, net high/low, and
  panic-cycle exposure — it has never been a price-direction forecast
  anywhere else on this page (Convexity Watch has the identical
  disclaimer), so a CAUTION call doesn't have one fixed "expected
  direction" this system can check price against. What "short FXE" or
  "USD up vs EUR" means from a CAUTION call is your own Socrates/Elliott
  Wave interpretation, layered on top of the breadth score — not
  something `scorecard.py`'s formula outputs. So this panel gives you
  the two facts side by side (the call, and the actual measured trend)
  and leaves the reconciliation to you, rather than silently baking in a
  directional mapping I'd have to invent and that could easily be wrong
  for a given category or regime.

  The Instrument Watchlist got a matching "vs 50d" column (reusing the
  existing `maBadge` — same thin-window honesty as 10d/20d) and its
  drill-down chart now plots the 50-day average as a third line alongside
  price/10d/20d. Tested with a dedicated `test_direction_check.js` (17
  checks: an active call with a trustworthy trend read, a category with
  two proxies pointing opposite directions, a too-thin window that must
  not fabricate a trend, a category with no price history at all, a
  category with no proxy mapped, active-before-NEUTRAL sort order, and an
  explicit check that the panel never uses "confirms"/"contradicts"
  language about the call) plus updated checks in `test_watchlist.js` for
  the new column and the "no 50d yet" fallback — 260 checks total now
  (56 Python + 204 JS). Schema re-verified fresh and re-applied on top of
  itself with the new columns, zero errors, 20 views unchanged.

  **What's still ahead, by your own stated priority order:** volume
  folded into the Opportunity Finder's ranking (you asked for it as a
  full scored factor, not just a liquidity filter — noted, not yet
  built), capping the Opportunity Finder at 3 candidates instead of 2,
  reorganizing watchlist categories further, a price/volume "study" per
  group over time, and expanding IV/skew tracking to more instruments.

- **Panic Cycle Radar, market-stress gauges, and IBIT (this round, from
  "how can I 2x the next panic cycle opportunity" plus "where can I get
  market stress gauge data").** Three separate additions:

  **Panic Cycle Radar** — a new panel, right under the Opportunity
  Finder. This is not new data: `panic_cycle_pct` (Socrates' own "Panic
  Cycle Signal Within 3 weeks" % per category, from
  `platform_breadth.csv`'s timing_array section) was already flowing all
  the way through `v_panic_cycle_exposure` → `v_scorecard` →
  `v_scorecard_wow`, and was already being fetched by every `refresh()`
  call — it just wasn't shown anywhere except as the boolean
  `volatility_flag` (`> 20%`) baked into Convexity Watch and the
  Opportunity Finder. This panel ranks every category by that same
  number's actual magnitude, highlights the top 2 ("2x"), and
  cross-references each with its mapped optionable instrument's current
  IV/skew so you see the panic-cycle reading and today's cheap/rich
  premium side by side. It shows the real week-over-week point change
  when two weeks of history exist for that category, and honestly omits
  it (not a fabricated 0) when only one week is on file. Same
  non-advice discipline as everywhere else: it ranks by volatility
  magnitude, not by a price direction, and it does not decide a trade.

  **Data gap, flagged not guessed:** your Execution Rules 2 and 3
  ("Panic Cycle Convexity Rule" — prioritize spreads into high-density
  Aggregate/Panic Cycle *target weeks*; "Monthly Pattern Alignment Rule"
  — check a Weekly Directional Change against the category's Monthly
  Pattern label like "Turning Back UP" or "Still Under Pressure") need
  two things `platform_breadth.csv` doesn't currently carry: a
  forward-looking calendar of target weeks (what's parsed today is a
  rolling 3-week-ahead % per category, not a dated list of upcoming
  high-density windows), and a per-instrument Monthly Pattern label. The
  panel says this to you directly rather than inventing either. If you
  can export the report section(s) that show these, they're addable the
  same way everything else here was — read from a real source, not
  fabricated.

  **Market stress gauges** — `fred_data.py`'s `FRED_SERIES` list now
  also pulls three genuinely free, no-API-key series from the same
  `fredgraph.csv` endpoint already in use, so this needed zero new
  infrastructure: `BAMLH0A0HYM2` (ICE BofA US High Yield OAS — credit
  market stress, independent of VIX's equity-vol basis), `NFCI`
  (Chicago Fed National Financial Conditions Index — 0 is the historical
  average, positive is tighter/more stressed), and `STLFSI4` (St. Louis
  Fed Financial Stress Index — a broader composite across yields, credit
  spreads, and equity/bond volatility). All three show up in the Macro
  Series (FRED) panel and its drill-down chart like every other series
  there. **What I checked and could NOT find a free source for:** the
  MOVE index (bond market's VIX equivalent) — it's ICE BofA's
  proprietary index, not published to FRED or any other free CSV
  endpoint; the only views found were paid data feeds or non-API chart
  pages (CNBC's `.MOVE` quote, TradingView). If you have a paid feed
  that carries it, it plugs in the same way as everything else here.

  **IBIT** added to `market_data.py`'s `INSTRUMENT_UNIVERSE` and
  `supabase_schema.sql`'s `instruments` table (Crypto group, high
  confidence) — found already present in your own working copy of
  `market_data.py` during this round's diff; brought into the canonical
  files here and into `iv_proxy_map` (was already correctly mapped as
  Crypto's IV proxy, alongside BTC-USD/ETH-USD as the spot proxies).

  Tested with a dedicated `test_panic_radar.js` (20 checks: correct
  descending rank by `panic_cycle_pct`, the flagged/elevated/calm
  threshold coloring, real week-over-week change vs. honestly omitted
  when only one week exists, real IV/skew/rank cross-reference for a
  top-2 card, "no IV proxy mapped" fallback for a top-2 card with
  nothing mapped, categories with no panic data or a null reading
  excluded rather than crashing or showing "null%", the rest-of-field
  ordering, the non-advice language guardrail, and the empty state).

  **New `positions` table + `v_position_pnl` view (this round, from "I
  need another csv of what is live, price bought... to help me
  backtest").** This is different from every other backtest number on
  this page: `v_signal_backtest`/`v_instrument_backtest` describe what a
  category's *canonical proxy* did after a breadth call — not what you
  actually traded, or at what size. `positions` is your own trade log
  (`position_id`, `symbol`, `direction`, `status`, `open_date`/
  `open_price`, `close_date`/`close_price`, `quantity`, plus optional
  `linked_week_of`/`linked_category` so a position can be tied back to
  the exact `v_scorecard_wow` row that was live when you opened it, and
  a free-text `notes`/`instrument_type`). `v_position_pnl` computes real
  P&L per position: realized return from your own close_price for
  closed positions, an honest unrealized mark from `market_prices`'
  latest close for open ones (null, not guessed, if that symbol isn't
  tracked), correctly sign-flipped for `short` positions, and — when
  linked — the `call`/`panic_cycle_pct` that were active at entry, so
  you can eventually group your real trades by "positions taken under a
  CAUTION call" or "under a flagged panic-cycle week" and see how those
  actually did, instead of only the generic proxy backtest.
  **`positions_template.csv`** is the starting point — copy it to your
  data folder as `positions.csv`, replace the two example rows with your
  real trades, and re-run **`push_to_supabase.py`** (now also reads
  `positions.csv` and upserts on `position_id`, so editing a row and
  re-running is always safe, same pattern as every other table it
  loads). Read-only for the dashboard's anon key like everything else
  here — writes only go through `push_to_supabase.py` with your secret
  key, from your own CSV, never from the browser. No dashboard panel for
  this yet (you asked for the CSV/backtest piece specifically) — a
  "My Positions" panel reading `v_position_pnl` is a natural next step
  if you want it. Tested with a dedicated `test_push_positions.py` (10
  checks: payload casts numeric fields and passes through an already-
  closed position's close_date/close_price, a still-open position keeps
  those genuinely `None` rather than fabricated, optional fields blank
  vs. filled, and the push itself upserts on `position_id` with the same
  merge-duplicates header as every other table).

  **290 checks total now (66 Python + 224 JS)**. Schema re-verified
  fresh and re-applied on top of itself with the IBIT row, the Panic
  Cycle Radar's underlying fields, and the new `positions` table/view
  all included — zero errors, 21 views.

- **More free stress/rate data, and a real bug caught (this round, from
  your pasted "Equity Volatility, Options Market & Corporate Credit
  Risk" / "Sovereign Fixed Income" tables).** Checked every row in both
  tables for a genuinely free source — web search, not memory, since
  provider/paywall status changes — before adding or skipping it:

  **Added, all free, no key:** `^VVIX`, the Cboe 1-Month Implied
  Correlation Index (`^COR1M` — the modern free replacement for Cboe's
  discontinued S&P 500 Implied Correlation Index/ICJ, at the exact 1M
  tenor your table used), and VSTOXX (`V2TX.DE`) all turned up as real,
  currently-listed Yahoo Finance tickers — added to `market_data.py`'s
  `INSTRUMENT_UNIVERSE` (Volatility group, "medium" confidence since
  this sandbox can't reach Yahoo to verify them live — same caveat as
  every other ticker here, spot-check on your first real run). On the
  FRED side: `BAMLC0A0CM` (ICE BofA US Corporate/investment-grade OAS —
  the closest free equivalent to your "CDX IG" row, same family as the
  high-yield spread added last round, but a bond-index OAS, not the same
  instrument as the CDX swap index) and Germany/France/Italy 10-year
  OECD government bond yields (`IRLTLT01DEM156N`/`FRM156N`/`ITM156N`,
  medium confidence, same "ID pattern inferred" caveat as the existing
  Japan/Euro-area rows), plus the raw 3-Month Euro Interbank rate
  (`IR3TIB01EZM156N`) — flagged clearly as the rate only, not a spread
  (see below).

  **Genuinely not free anywhere:** CDX IG, CDX HY, and iTraxx Europe
  Main — all three are IHS Markit/S&P Global-administered CDS indices,
  distributed via ICE Clear Credit or paid terminals only, same
  treatment as the MOVE index from last round: flagged, not faked, not
  quietly substituted with something that only looks similar. A true
  Euribor-OIS spread also isn't free — no daily €STR/OIS leg was found
  to subtract from the raw Euribor rate, so the spread itself isn't
  computed anywhere in this pipeline, only the plain rate.

  **The "make sure the data gives insights" part:** a new
  `v_fred_spreads`/`v_fred_spreads_latest` view pair turns the raw
  levels into the actual spreads your table showed — US 2s10s (from
  `DGS10`/`DGS2`, already tracked, just never subtracted before),
  France−Germany 10Y, and Italy−Germany 10Y — plain subtractions in
  basis points, nothing fitted or invented. Each spread's latest reading
  is computed independently (`v_fred_spreads_latest`), since the US leg
  updates daily and the European legs update monthly — the naive "latest
  single row" would've shown a real US number next to two blank
  European ones on most days; this doesn't. Surfaced on the dashboard as
  three new tiles above the Macro Series (FRED) cards: value in bps,
  the real as-of date per spread, and a plain-language note (curve
  shape for 2s10s, "sovereign risk premium over Germany" for the other
  two) — states what the number is, same as everywhere else on this
  page, never a trade call.

  **Real bug caught and fixed in the same pass:** last round's three
  stress-gauge FRED series (`BAMLH0A0HYM2`, `NFCI`, `STLFSI4`) were
  added to `fred_data.py`'s `FRED_SERIES` list but never inserted into
  `supabase_schema.sql`'s `fred_series_meta` table — since `fred_series`
  has a foreign key on it, pushing that data would have failed outright
  the moment you actually ran `push_to_supabase.py` with real readings
  for those three. Caught while wiring in this round's new series (same
  table needed touching anyway) and fixed — all 16 FRED series now
  present in `fred_series_meta`, re-verified against a fresh schema
  apply.

  Tested with a dedicated `test_fred_spreads.js` (11 checks: three
  tiles render with real values, each spread shows its OWN as-of date
  independently rather than being blanked out by a more-recent date on
  a different-frequency series, positive/negative 2s10s reads as
  normal/inverted, partial data renders only the tiles with a real
  value — not a crash on the missing legs — and no data at all renders
  an empty strip rather than a fabricated tile). Adding the new
  `v_fred_spreads_latest` fetch to `refresh()` meant every other test
  file's mocked fetch needed the same one-line addition (a real
  `Promise.all` in `refresh()` fails its entire refresh if ANY query
  404s — intentional, so a real Supabase error surfaces loudly instead
  of silently missing data, but it meant 13 existing test files needed
  updating for the new endpoint) — all of them re-verified passing
  after the fix. **301 checks total now (66 Python + 235 JS)**. Schema
  re-verified fresh and re-applied on top of itself with the new FRED
  series, the `v_fred_spreads`/`v_fred_spreads_latest` views, and the
  `fred_series_meta` fix all included — zero errors, 23 views.

One honest gap in workflow 3's design: `Record Alerts Sent` runs in
parallel with `Send Telegram Alert`, not after it succeeds — so if a
Telegram send genuinely fails, that category still gets marked as
"already alerted" and won't be retried tomorrow. I did it this way to keep
the workflow simple rather than adding retry/rollback logic for a
notification that isn't your system of record (the dashboard and Supabase
are); if Telegram delivery turns out to be flaky in practice, worth
revisiting.

## Setup (the n8n automation — do the dashboard quickstart above first)

1. Already done if you followed the quickstart above.
2. In n8n: **Import from File** for all three workflow JSON files.
3. On the n8n host, set these environment variables (workflows read them
   via `$env`): `SUPABASE_URL` (your project's REST URL, e.g.
   `https://xxxx.supabase.co`), `SUPABASE_SERVICE_KEY` (the secret /
   `service_role` key — the same one you put in `push_to_supabase.py`,
   not the publishable/anon one, since these writes bypass row-level
   security policies deliberately here), `TELEGRAM_BOT_TOKEN`, and
   `TELEGRAM_CHAT_ID` (see below for both). Restart n8n after setting
   them if it doesn't pick up env changes live.
4. Workflow 1: copy its webhook URL from the node (n8n shows it once
   active/saved) — that's what you POST each week's report text to.
   Test it once by hand (curl, Postman, or n8n's own "Listen for test
   event") before relying on it.
5. Workflow 2: manually execute it once with `RANGE = "5d"` (the default
   in "Build Symbol Requests") to confirm the Yahoo call actually works
   from your host — see the caveat above. Once confirmed, either leave the
   Schedule Trigger running weekly as-is, or temporarily edit `RANGE` to
   `"2y"` and run it once by hand for an initial historical backfill, then
   change it back to `"5d"` before turning the schedule on.
6. Workflow 3: create a Telegram bot once — message **@BotFather** on
   Telegram, send `/newbot`, follow its prompts, and it gives you a bot
   token (`TELEGRAM_BOT_TOKEN`). Then message your new bot anything once
   (it can't message you first), and fetch
   `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser — your
   `chat.id` in the response is `TELEGRAM_CHAT_ID`. Set both env vars, then
   run the workflow manually once to confirm a message actually arrives.
7. Activate all three workflows. `dashboard.html` is already showing real
   data from the quickstart above — once these are active, it'll start
   updating itself instead of you having to re-run `push_to_supabase.py`.

## Feeding in your older archive weeks

Same idea as before, now via the webhook: for each older weekly summary
you can pull, POST it as `{ "report_text": "<that week's full text>" }` to
workflow 1's webhook. The parser doesn't care what order weeks arrive in —
it reads the week from the report's own "close for Weekly YYYY-MM-DD"
line, not from when you send it. The unique constraint means sending the
same week twice fails loudly rather than duplicating.

## What workflow 3 actually alerts on

Three conditions, computed from `v_scorecard_wow` (same fixed formula as
`scorecard.py`: 0.4×net reversal bias + 0.4×net high/low + 0.2×panic-cycle
exposure; CAUTION above 8, CONSTRUCTIVE below -8, NEUTRAL between):

1. **Regime flip** — this week's call differs from last week's for that
   category (e.g. NEUTRAL → CAUTION).
2. **New volatility flag** — panic-cycle exposure just crossed above 20%
   when it wasn't last week.
3. **Big single-week swing** — the score moved 15+ points even without
   crossing a call boundary (catches something building before it fully
   flips).

Each category gets checked once per newly-ingested week, never repeated —
see `alerts_sent` and the honest gap noted above. It deliberately does
*not* alert on "still CAUTION, same as last week" — that's noise, not a
new opportunity to hunt down. If you find yourself wanting more signal
(e.g. a same-direction reversal-bias move for 3+ consecutive weeks, which
is the multi-week pattern already visible in Stocks/Stock Indices across
your first 6 weeks), that's a real extension to `Detect New Alerts` —
just say so and I'll build it once you have more weeks in to validate it
against.

## Why there's no "model" node

Same reasoning as before, just relocated: with a handful of weeks of
paired Socrates+market data, a fitted model would be fitting noise, not
signal. What's here is the honest version — extraction, storage, and the
trend views — with `v_price_forward_return` giving you the raw material
(15-trading-session-forward return per price row) to check calls against
reality yourself in Supabase's SQL editor or a BI tool, once enough weeks
have actually accumulated to say something real.
