"""
push_to_supabase.py — one-time (and re-runnable) loader that pushes your
local CSVs into the Supabase project you just set up, so dashboard.html
has something real to read today, without needing the n8n workflows
running yet. Those still matter for keeping things updated automatically
going forward — this script is the fast path to "see it working now."

SECURITY: fill in SUPABASE_URL and SUPABASE_SECRET_KEY below, in this
file, on your own machine. Never paste your secret key into chat with me
or anyone else — it bypasses row-level security entirely (same as
n8n's SUPABASE_SERVICE_KEY). If your Supabase project shows "secret key"
(sb_secret_...) rather than "service_role key", they're the same thing
under Supabase's newer naming — use whichever one your project's API
settings page shows you.

Uses upsert (Prefer: resolution=merge-duplicates), not plain insert, so
re-running this after adding more weeks/snapshots to your CSVs is always
safe — it won't fail on rows already in Supabase, and it won't duplicate
them either.

Run: python push_to_supabase.py
Reads:  platform_breadth.csv, iv_snapshot.csv, market_prices.csv,
        fred_series.csv, positions.csv (all in SOCRATES_DATA_DIR below)
Writes: nothing locally — POSTs rows to your Supabase project

positions.csv is different from the others: it's not pulled from a market
data source, it's YOUR trade log — see positions_template.csv for the
columns and supabase_schema.sql's comment above the `positions` table for
what each one means. You maintain it by hand (or export it from IBKR and
reshape it into these columns) and re-run this script whenever you open,
close, or update a position; upsert-by-position_id means editing a row
and re-running is always safe.
"""
import csv
import json
import os
import urllib.error
import urllib.request

# ---- Fill these in, then save. Never share SUPABASE_SECRET_KEY. --------
SUPABASE_URL = "YOUR_SUPABASE_URL_HERE"          # e.g. https://xxxx.supabase.co
SUPABASE_SECRET_KEY = "YOUR_SECRET_KEY_HERE"      # Project Settings -> API -> secret / service_role key
# --------------------------------------------------------------------------

# Hardcoded to your real folder (confirmed on 2026-09-21 to be the one
# holding the full 6-week, 630-row platform_breadth.csv) after several
# duplicate "socrates_data" folders on this machine caused a stale 1-week
# file to get pushed silently, over and over, with no error. If you ever
# move where add_breadth_week.py writes its CSVs, update this line to
# match. Also worth deleting or archiving the other duplicate
# socrates_data folders on this machine so this can't happen again —
# every extra copy of platform_breadth.csv is a future version of this
# same bug waiting to happen.
SOCRATES_DATA_DIR = "/Users/Ruthie/Downloads/socrates_data main/socrates_data_main_dashboard"
PLATFORM_BREADTH_CSV = os.path.join(SOCRATES_DATA_DIR, "platform_breadth.csv")
IV_SNAPSHOT_CSV = os.path.join(SOCRATES_DATA_DIR, "iv_snapshot.csv")
MARKET_PRICES_CSV = os.path.join(SOCRATES_DATA_DIR, "market_prices.csv")
FRED_SERIES_CSV = os.path.join(SOCRATES_DATA_DIR, "fred_series.csv")
POSITIONS_CSV = os.path.join(SOCRATES_DATA_DIR, "positions.csv")

BATCH_SIZE = 200  # PostgREST handles large arrays fine, but keep requests reasonably sized


def read_csv_rows(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def platform_breadth_payload(rows):
    """Table columns: week_of, section, category, metric, count, pct.
    Drop nothing else — the CSV has exactly these columns already."""
    return [
        {
            "week_of": r["week_of"], "section": r["section"], "category": r["category"],
            "metric": r["metric"], "count": int(r["count"]), "pct": float(r["pct"]),
        }
        for r in rows
    ]


def iv_snapshot_payload(rows):
    """Table columns deliberately exclude 'category' (see supabase_schema.sql's
    comment on iv_snapshots — QQQ alone represents two breadth categories, so
    category isn't part of the row's identity). The CSV still has a category
    column for human readability; drop it here rather than pushing a column
    that doesn't exist in the table."""
    out = []
    for r in rows:
        out.append({
            "date": r["date"], "symbol": r["symbol"], "spot": float(r["spot"]),
            "expiry_used": r["expiry_used"], "dte": int(r["dte"]),
            "atm_call_iv": float(r["atm_call_iv"]), "atm_put_iv": float(r["atm_put_iv"]),
            "atm_iv_avg": float(r["atm_iv_avg"]),
            "otm_call_iv_5pct": float(r["otm_call_iv_5pct"]), "otm_put_iv_5pct": float(r["otm_put_iv_5pct"]),
            "put_call_skew_5pct": float(r["put_call_skew_5pct"]),
        })
    return out


def market_prices_payload(rows):
    """Table columns: date, symbol, close, open, high, low, volume.
    open/high/low/volume are optional — an older market_prices.csv (or one
    written before this script's OHLCV update) may only have date/symbol/
    close, and yfinance can legitimately return a blank for one of these
    for a given symbol/day. Blank stays None here, never guessed at."""
    def num_or_none(value, cast):
        if value is None or value == "":
            return None
        return cast(value)

    out = []
    for r in rows:
        out.append({
            "date": r["date"], "symbol": r["symbol"], "close": float(r["close"]),
            "open": num_or_none(r.get("open"), float),
            "high": num_or_none(r.get("high"), float),
            "low": num_or_none(r.get("low"), float),
            "volume": num_or_none(r.get("volume"), lambda v: int(float(v))),
        })
    return out


def fred_series_payload(rows):
    """Table columns: series_id, date, value. value is skipped (row
    dropped entirely, not pushed as null) if blank — fred_data.py already
    does this filtering itself before writing the CSV, but this is a
    second, independent check rather than trusting the CSV was written
    correctly."""
    out = []
    for r in rows:
        if r.get("value") in (None, ""):
            continue
        out.append({"series_id": r["series_id"], "date": r["date"], "value": float(r["value"])})
    return out


def positions_payload(rows):
    """Table columns: position_id, symbol, category, instrument_type,
    direction, status, open_date, open_price, quantity, close_date,
    close_price, linked_week_of, linked_category, notes. Everything past
    quantity is optional — a still-open position legitimately has no
    close_date/close_price yet, and linked_week_of/linked_category/notes
    are there to help your own review, not required for the row to be
    valid. Blank stays blank (None), never guessed or defaulted, same
    discipline as market_prices_payload's open/high/low/volume above."""
    def str_or_none(value):
        return value if value not in (None, "") else None

    def num_or_none(value, cast):
        if value is None or str(value).strip() == "":
            return None
        return cast(value)

    out = []
    for r in rows:
        out.append({
            "position_id": r["position_id"],
            "symbol": r["symbol"],
            "category": str_or_none(r.get("category")),
            "instrument_type": r.get("instrument_type") or "shares",
            "direction": r["direction"],
            "status": r["status"],
            "open_date": r["open_date"],
            "open_price": float(r["open_price"]),
            "quantity": float(r["quantity"]),
            "close_date": str_or_none(r.get("close_date")),
            "close_price": num_or_none(r.get("close_price"), float),
            "linked_week_of": str_or_none(r.get("linked_week_of")),
            "linked_category": str_or_none(r.get("linked_category")),
            "notes": str_or_none(r.get("notes")),
        })
    return out


def push_batch(table, on_conflict_columns, batch):
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}?on_conflict={on_conflict_columns}"
    body = json.dumps(batch).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{table}: HTTP {e.code} — {error_body}") from None


def summarize_dates(rows, date_field):
    """No-inference sanity line: shows exactly what's about to be pushed
    (row count + date range) so a stale/wrong file is obvious in the
    terminal BEFORE it's pushed, not discovered later on the dashboard."""
    dates = sorted(set(r[date_field] for r in rows))
    if not dates:
        return f"{len(rows)} rows"
    return f"{len(rows)} rows, {date_field} {dates[0]} to {dates[-1]} ({len(dates)} distinct date(s))"


def push_table(table, on_conflict_columns, payload):
    if not payload:
        print(f"{table}: nothing to push")
        return
    for i in range(0, len(payload), BATCH_SIZE):
        batch = payload[i:i + BATCH_SIZE]
        status = push_batch(table, on_conflict_columns, batch)
        print(f"{table}: pushed rows {i + 1}-{i + len(batch)} of {len(payload)} (HTTP {status})")


def main():
    if SUPABASE_URL == "YOUR_SUPABASE_URL_HERE" or SUPABASE_SECRET_KEY == "YOUR_SECRET_KEY_HERE":
        print("Fill in SUPABASE_URL and SUPABASE_SECRET_KEY at the top of this file first, then re-run.")
        return

    breadth_rows = read_csv_rows(PLATFORM_BREADTH_CSV)
    if breadth_rows is None:
        print(f"Not found: {PLATFORM_BREADTH_CSV} — skipping platform_breadth.")
    else:
        print(f"platform_breadth.csv: {summarize_dates(breadth_rows, 'week_of')}  <-- check this before it pushes")
        push_table("platform_breadth", "week_of,section,category,metric", platform_breadth_payload(breadth_rows))

    iv_rows = read_csv_rows(IV_SNAPSHOT_CSV)
    if iv_rows is None:
        print(f"Not found: {IV_SNAPSHOT_CSV} — skipping iv_snapshots (run iv_snapshot.py first if you want this).")
    else:
        print(f"iv_snapshot.csv: {summarize_dates(iv_rows, 'date')}  <-- check this before it pushes")
        push_table("iv_snapshots", "date,symbol", iv_snapshot_payload(iv_rows))

    price_rows = read_csv_rows(MARKET_PRICES_CSV)
    if price_rows is None:
        print(f"Not found: {MARKET_PRICES_CSV} — skipping market_prices (run market_data.py first if you want this).")
    else:
        print(f"market_prices.csv: {summarize_dates(price_rows, 'date')}, "
              f"{len(set(r['symbol'] for r in price_rows))} symbols  <-- check this before it pushes")
        push_table("market_prices", "date,symbol", market_prices_payload(price_rows))

    fred_rows = read_csv_rows(FRED_SERIES_CSV)
    if fred_rows is None:
        print(f"Not found: {FRED_SERIES_CSV} — skipping fred_series (run fred_data.py first if you want this).")
    else:
        print(f"fred_series.csv: {summarize_dates(fred_rows, 'date')}, "
              f"{len(set(r['series_id'] for r in fred_rows))} series  <-- check this before it pushes")
        push_table("fred_series", "series_id,date", fred_series_payload(fred_rows))

    position_rows = read_csv_rows(POSITIONS_CSV)
    if position_rows is None:
        print(f"Not found: {POSITIONS_CSV} — skipping positions "
              f"(copy positions_template.csv there and fill in your own trades if you want this).")
    else:
        open_n = sum(1 for r in position_rows if r.get("status") == "open")
        closed_n = sum(1 for r in position_rows if r.get("status") == "closed")
        print(f"positions.csv: {len(position_rows)} rows ({open_n} open, {closed_n} closed)  <-- check this before it pushes")
        push_table("positions", "position_id", positions_payload(position_rows))

    print("\nDone. Open dashboard.html (with SUPABASE_URL / SUPABASE_ANON_KEY filled in — the "
          "PUBLISHABLE key, not this secret one) to see it.")


if __name__ == "__main__":
    main()
