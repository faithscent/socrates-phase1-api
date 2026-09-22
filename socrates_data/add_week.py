"""
add_week.py — append one week's cross-market read to weekly_macro_trends.csv
and weekly_macro_read.csv.

Workflow (matches Section 12's Weekly Update Procedure, Step 8 in the
reference doc): after you've read this week's Socrates arrays/premium text
for each market, fill in WEEK_DATA below and run:

    python add_week.py

Rules this script enforces (mirroring the database's own Section 12 rules,
so the CSV can't silently drift from the discipline the txt version had):
  - L-Wave color is GREEN, PURPLE, or blank ("") — nothing else. No
    "leaning green" or inferred shades.
  - Any row where you gave real data (not all blanks) MUST have a source
    citation. A row with data and no source is rejected rather than
    written blank-sourced.
  - Blank means blank: leave a field "" if you don't have it this week.
    Don't fill it from a prior week or guess it from another market.
  - Re-running for a week_of that's already in the file APPENDS a second
    set of rows rather than silently overwriting — dedupe/correct by hand
    in the CSV (or in VS Code) if that happens; this script won't guess
    which version is right.

You can also import add_market_row()/add_week_read() from another script
if you'd rather build WEEK_DATA programmatically (e.g. from an API pull).
"""
import csv
import os
from datetime import date

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
TRENDS_CSV = os.path.join(DATA_DIR, "weekly_macro_trends.csv")
READ_CSV = os.path.join(DATA_DIR, "weekly_macro_read.csv")

VALID_LWAVE = {"GREEN", "PURPLE", ""}
TRENDS_FIELDS = ["week_of", "market", "weekly_lwave", "daily_lwave",
                  "pc_flag_date", "reversal_above", "reversal_below",
                  "source", "notes"]
READ_FIELDS = ["week_of", "macro_read", "drivers"]

# ---------------------------------------------------------------------------
# EDIT THIS BLOCK EACH WEEK, then run: python add_week.py
# ---------------------------------------------------------------------------
WEEK_OF = "2026-09-18"   # the Friday close this data is for

WEEK_DATA = [
    # market, weekly_lwave, daily_lwave, pc_flag_date, reversal_above, reversal_below, source, notes
    {"market": "QQQ",     "weekly_lwave": "", "daily_lwave": "", "pc_flag_date": "", "reversal_above": "", "reversal_below": "", "source": "", "notes": ""},
    {"market": "FXE",     "weekly_lwave": "", "daily_lwave": "", "pc_flag_date": "", "reversal_above": "", "reversal_below": "", "source": "", "notes": ""},
    {"market": "USO",     "weekly_lwave": "", "daily_lwave": "", "pc_flag_date": "", "reversal_above": "", "reversal_below": "", "source": "", "notes": ""},
    {"market": "GLD",     "weekly_lwave": "", "daily_lwave": "", "pc_flag_date": "", "reversal_above": "", "reversal_below": "", "source": "", "notes": ""},
    {"market": "HYG",     "weekly_lwave": "", "daily_lwave": "", "pc_flag_date": "", "reversal_above": "", "reversal_below": "", "source": "", "notes": ""},
    {"market": "TLT",     "weekly_lwave": "", "daily_lwave": "", "pc_flag_date": "", "reversal_above": "", "reversal_below": "", "source": "", "notes": ""},
    {"market": "USD/JPY", "weekly_lwave": "", "daily_lwave": "", "pc_flag_date": "", "reversal_above": "", "reversal_below": "", "source": "", "notes": ""},
]

MACRO_READ = ""   # e.g. "mixed", "risk-off (credit + QQQ both PURPLE)", "insufficient data"
DRIVERS = ""      # e.g. "HYG PURPLE + VIX up 3pts drove the read"
# ---------------------------------------------------------------------------


def _has_data(row: dict) -> bool:
    return any(v.strip() for k, v in row.items() if k != "market")


def add_market_row(week_of: str, row: dict, csv_path: str = TRENDS_CSV) -> None:
    lwave_fields = ("weekly_lwave", "daily_lwave")
    for f in lwave_fields:
        val = (row.get(f) or "").strip().upper()
        if val not in VALID_LWAVE:
            raise ValueError(
                f"{row.get('market')}: {f}={val!r} is not GREEN, PURPLE, or "
                f"blank. No other L-Wave reading is permitted (Section 12 "
                f"Rule 2)."
            )
        row[f] = val

    if _has_data(row) and not (row.get("source") or "").strip():
        raise ValueError(
            f"{row.get('market')}: has data but no source citation — "
            f"rejected per Section 12 Rule 1 (every entry needs a source)."
        )

    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TRENDS_FIELDS)
        if not file_exists or os.path.getsize(csv_path) == 0:
            writer.writeheader()
        full_row = {"week_of": week_of, **row}
        writer.writerow({k: full_row.get(k, "") for k in TRENDS_FIELDS})


def add_week_read(week_of: str, macro_read: str, drivers: str = "",
                   csv_path: str = READ_CSV) -> None:
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=READ_FIELDS)
        if not file_exists or os.path.getsize(csv_path) == 0:
            writer.writeheader()
        writer.writerow({"week_of": week_of, "macro_read": macro_read, "drivers": drivers})


def main():
    if not WEEK_OF:
        raise SystemExit("Set WEEK_OF at the top of add_week.py before running.")

    written = 0
    for row in WEEK_DATA:
        market = row.get("market", "<unknown>")
        try:
            add_market_row(WEEK_OF, dict(row))
            written += 1
        except ValueError as e:
            print(f"SKIPPED {market}: {e}")

    if MACRO_READ.strip():
        add_week_read(WEEK_OF, MACRO_READ.strip(), DRIVERS.strip())
        print(f"Wrote macro read for {WEEK_OF} to {os.path.basename(READ_CSV)}")
    else:
        print(f"No MACRO_READ set — skipped {os.path.basename(READ_CSV)} "
              f"(fill it in once you've eyeballed the market rows).")

    print(f"Wrote {written}/{len(WEEK_DATA)} market rows for {WEEK_OF} to "
          f"{os.path.basename(TRENDS_CSV)}")


if __name__ == "__main__":
    main()
