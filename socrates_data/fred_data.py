"""
fred_data.py — pull point-in-time macro series (rates, CPI, dollar index,
VIX) from the St. Louis Fed's FRED, via the free public fredgraph.csv
endpoint. No API key required.

⚠ RUN THIS ON YOUR OWN MACHINE, NOT IN THIS SANDBOX — same restriction as
market_data.py. The cloud workspace this conversation runs in has its
outbound network access restricted to an allowlist, and fred.stlouisfed.org
is not on it (confirmed directly: a plain curl to both
api.stlouisfed.org and fred.stlouisfed.org comes back "CONNECT tunnel
failed, response 403" from the proxy here — not a transient error).

WHY THIS EXISTS: two gaps market_data.py flagged as UNAVAILABLE — Japan
and Euro area 10-year government bond yields — have no usable Yahoo
Finance ticker. FRED carries both, sourced from the OECD. FRED also gives
a much longer, more reliable history for US rates, CPI, the dollar index,
and VIX than a 2-year yfinance pull would.

IMPORTANT — READ BEFORE TRUSTING THE OUTPUT: FRED_SERIES below has a
confidence tag per series, same discipline as market_data.py's
INSTRUMENT_UNIVERSE. "high" entries (DGS10, DGS2, DFF, VIXCLS, DTWEXBGS,
CPIAUCSL) are standard, extremely well-known FRED series IDs I'd bet on.
The two "medium" entries — IRLTLT01JPM156N (Japan) and IRLTLT01EZM156N
(Euro area) — follow FRED's well-established naming pattern for OECD
"long-term interest rates" series (IRLTLT01 + ISO country code + M156N
for the monthly, national-currency vintage; e.g. IRLTLT01DEM156N is
Germany's), which I'm reasonably confident about, but I could NOT verify
either ID against a live fetch from this sandbox (see above) — this
script prints a WARNING and skips (never fabricates) any series ID that
doesn't return real data. If either of these comes back empty or 404s on
your first run, tell me and I'll find the right ID with you.

Usage:
    python fred_data.py

Writes: fred_series.csv — long format: series_id, date, value. Only real
observations are written — a FRED "." (no reading posted yet for that
date, common for the most recent month of a monthly series) is skipped
entirely, never written as a fabricated 0 or interpolated value.
"""
import csv
import io
import os
import urllib.error
import urllib.request
from datetime import date, timedelta

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(DATA_DIR, "fred_series.csv")

# Trim to the same lookback window as market_data.py, for consistency and
# to keep the push size reasonable — FRED's daily series otherwise go
# back decades. fredgraph.csv doesn't take a documented/verified date-range
# query param, so this fetches full history and trims client-side rather
# than relying on an unverified URL parameter.
LOOKBACK_DAYS = 730

# Mirrored into supabase_schema.sql's fred_series_meta table — if you add
# or change a series here, update that table's insert too (same
# "keep N places in sync" discipline as INSTRUMENT_UNIVERSE / iv_proxy_map
# elsewhere in this project).
FRED_SERIES = [
    {"series_id": "DGS10", "description": "10-Year Treasury Constant Maturity Rate (US)",
     "frequency": "daily", "confidence": "high"},
    {"series_id": "DGS2", "description": "2-Year Treasury Constant Maturity Rate (US)",
     "frequency": "daily", "confidence": "high"},
    {"series_id": "DFF", "description": "Federal Funds Effective Rate",
     "frequency": "daily", "confidence": "high"},
    {"series_id": "VIXCLS", "description": "CBOE Volatility Index (VIX) — FRED's own copy",
     "frequency": "daily", "confidence": "high"},
    {"series_id": "DTWEXBGS", "description": "Trade Weighted US Dollar Index: Broad, Goods and Services",
     "frequency": "daily", "confidence": "high"},
    {"series_id": "CPIAUCSL", "description": "CPI for All Urban Consumers: All Items, seasonally adjusted",
     "frequency": "monthly", "confidence": "high"},
    {"series_id": "IRLTLT01JPM156N", "description": "Japan 10-Year Government Bond Yield (OECD, via FRED)",
     "frequency": "monthly", "confidence": "medium — series ID pattern inferred, not verified against live data (see docstring)"},
    {"series_id": "IRLTLT01EZM156N", "description": "Euro Area 10-Year Government Bond Yield (OECD, via FRED)",
     "frequency": "monthly", "confidence": "medium — same caveat as Japan above"},
    # Market stress gauges (added for the "where do I get stress gauge
    # data" question) — all three are free, no-key FRED series, same
    # fredgraph.csv endpoint as everything above, so this needed zero new
    # infrastructure. Verified live on FRED as of 2026-09-22: BAMLH0A0HYM2
    # (https://fred.stlouisfed.org/series/BAMLH0A0HYM2), NFCI
    # (https://fred.stlouisfed.org/series/NFCI), STLFSI4
    # (https://fred.stlouisfed.org/series/STLFSI4). The MOVE index (bond-
    # market equivalent of VIX) is deliberately NOT here — it's ICE BofA's
    # proprietary index, not published to FRED or any other free CSV
    # source; the only free multi-day view found was a TradingView/CNBC
    # quote page, not a fetchable series. If you have a paid data feed
    # that carries MOVE, it can be added the same way as everything else
    # here — just not for free.
    {"series_id": "BAMLH0A0HYM2", "description": "ICE BofA US High Yield Index Option-Adjusted Spread (credit stress — widens when credit markets get nervous, independent of equity-vol-driven VIX)",
     "frequency": "daily", "confidence": "high"},
    {"series_id": "NFCI", "description": "Chicago Fed National Financial Conditions Index (0 = historical average; positive = tighter/more stressed financial conditions, negative = looser)",
     "frequency": "weekly", "confidence": "high"},
    {"series_id": "STLFSI4", "description": "St. Louis Fed Financial Stress Index (0 = historical average; a broader composite stress gauge across yields, credit spreads, and equity/bond volatility)",
     "frequency": "weekly", "confidence": "high"},

    # Added against your pasted "Equity Volatility, Options Market &
    # Corporate Credit Risk" / "Sovereign Fixed Income" tables. Checked
    # each row for a genuinely free source (web search, not memory —
    # provider/paywall status changes) before adding or skipping it:
    #
    #   FREE, added here: ICE BofA US Corporate Index OAS (BAMLC0A0CM) —
    #   same FRED family as the HY spread above, investment-grade rather
    #   than high-yield. This is the closest free equivalent to your
    #   "CDX IG" row — same concept (IG credit stress), NOT the same
    #   instrument (this is a cash-bond-index OAS; CDX IG is a CDS swap
    #   index — they move together but aren't numerically identical).
    #   Germany/France/Italy 10-year government bond yields (OECD via
    #   FRED, same medium-confidence "ID pattern inferred" caveat as the
    #   existing Japan/Euro-area rows below) — supabase_schema.sql's new
    #   v_fred_spreads view turns these into real France-Germany and
    #   Italy-Germany 10Y spreads (your "French-German"/"Italian-German"
    #   rows), computed, not manually re-typed each week. 3-Month Euro
    #   Interbank Offered Rate (IR3TIB01EZM156N) — see its own note below,
    #   this is NOT your Euribor-OIS spread row.
    #
    #   FREE, but not via FRED/fredgraph.csv — belongs in market_data.py
    #   instead (see that file): VVIX, the Cboe Implied Correlation Index
    #   at the 1-month tenor, and VSTOXX (Euro Stoxx 50 volatility) all
    #   turned up as real, currently-listed Yahoo Finance tickers.
    #
    #   NOT free anywhere found: CDX IG, CDX HY, and iTraxx Europe Main
    #   (all three are IHS Markit/S&P Global-administered CDS indices;
    #   settlement levels are distributed via ICE Clear Credit or paid
    #   terminals, no free CSV/API) — same treatment as the MOVE index
    #   above: flagged, not faked, not substituted with something that
    #   only looks similar. A true Euribor-OIS spread also isn't free —
    #   IR3TIB01EZM156N below is the raw 3M Euribor LEVEL only; no free
    #   daily €STR/OIS series was found to subtract from it, so the
    #   spread itself isn't computed anywhere in this pipeline. If you
    #   have a paid feed for any of these four, they plug in the same way
    #   as everything else here.
    {"series_id": "BAMLC0A0CM", "description": "ICE BofA US Corporate Index Option-Adjusted Spread (investment-grade credit stress — closest free equivalent to a CDX IG-style read, not the same instrument)",
     "frequency": "daily", "confidence": "high"},
    {"series_id": "IRLTLT01DEM156N", "description": "Germany 10-Year Government Bond Yield (Bund, OECD via FRED)",
     "frequency": "monthly", "confidence": "medium — same 'ID pattern inferred' caveat as Japan/Euro area above"},
    {"series_id": "IRLTLT01FRM156N", "description": "France 10-Year Government Bond Yield (OECD via FRED)",
     "frequency": "monthly", "confidence": "medium — same caveat"},
    {"series_id": "IRLTLT01ITM156N", "description": "Italy 10-Year Government Bond Yield (OECD via FRED)",
     "frequency": "monthly", "confidence": "medium — same caveat"},
    {"series_id": "IR3TIB01EZM156N", "description": "3-Month Euro Area Interbank Offered Rate — the raw rate only, NOT a Euribor-OIS spread (no free OIS leg found; see note above)",
     "frequency": "monthly", "confidence": "medium — same caveat"},
]

SERIES_IDS = [row["series_id"] for row in FRED_SERIES]


def fetch_series(series_id):
    """Pulls one series' full history as (date_str, value_float) pairs via
    the public fredgraph.csv endpoint. Returns [] (never raises) on a
    missing/renamed series ID or a network hiccup — the caller decides
    what to do with an empty result, same pattern as market_data.py's
    fetch_yfinance skipping a symbol rather than fabricating rows."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"WARNING: could not fetch {series_id}: {e} — skipped, not filled in.")
        return []

    reader = csv.reader(io.StringIO(raw))
    header = next(reader, None)
    if not header or len(header) < 2:
        print(f"WARNING: {series_id} response didn't look like a CSV (got: {raw[:120]!r}) — skipped.")
        return []

    out = []
    skipped_missing = 0
    for row in reader:
        if len(row) < 2:
            continue
        date_str, value_str = row[0], row[1]
        if value_str == "." or value_str.strip() == "":
            skipped_missing += 1
            continue
        try:
            out.append((date_str, float(value_str)))
        except ValueError:
            continue
    if skipped_missing:
        print(f"  ({series_id}: {skipped_missing} date(s) had no posted reading yet — skipped, not fabricated)")
    return out


def main():
    print(f"Pulling {len(SERIES_IDS)} FRED series (fredgraph.csv, no API key) ...")
    cutoff = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()

    all_rows = []
    fetched_ids = set()
    for row in FRED_SERIES:
        sid = row["series_id"]
        obs = fetch_series(sid)
        if not obs:
            continue
        trimmed = [(d, v) for d, v in obs if d >= cutoff]
        if not trimmed:
            print(f"WARNING: {sid} returned data but none within the last {LOOKBACK_DAYS} days — skipped.")
            continue
        fetched_ids.add(sid)
        for d, v in trimmed:
            all_rows.append({"series_id": sid, "date": d, "value": v})
        print(f"  {sid}: {len(trimmed)} observations, {trimmed[0][0]} to {trimmed[-1][0]} "
              f"[{row['confidence']}]")

    missing_ids = set(SERIES_IDS) - fetched_ids
    if missing_ids:
        print(f"\n{len(missing_ids)} series attempted but returned nothing: {', '.join(sorted(missing_ids))}")
        print("If either of the two Japan/Euro yield IDs is in that list, tell me and I'll find the right one with you.")

    if not all_rows:
        raise SystemExit("Nothing was fetched — check your network and try again.")

    all_rows.sort(key=lambda r: (r["series_id"], r["date"]))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["series_id", "date", "value"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nWrote {len(all_rows)} rows to {os.path.basename(OUT_CSV)} "
          f"({len(fetched_ids)} of {len(SERIES_IDS)} series)")


if __name__ == "__main__":
    main()
