"""
parse_premium_commentary.py — parser for the per-instrument Socrates
"Premium Overview Commentary" report (the long narrative one, e.g. the
US Dollar v Euro Adjusted Spot report you pasted on 2026-09-21). This is a
different grain from platform_breadth.csv: one specific market, not a
whole-category statistic, and a MUCH richer, more free-text report.

WHAT THIS DOES AND DOESN'T DO: like add_breadth_week.py, this only pulls
fields that appear in a fixed, repeatable template phrasing — regex
against exact wording, never eyeballed or inferred. If a sentence's exact
wording ever changes between reports, that one field comes back None
rather than a guessed value; it does NOT throw for the whole report (most
of these reports will have SOME field that doesn't match if Armstrong
Economics tweaks their template, and one missing field shouldn't block
everything else). raw_text always keeps the ENTIRE report verbatim, so
nothing is ever lost even for fields not parsed into their own column.

WHAT'S DELIBERATELY NOT PARSED YET: the Monthly Timing Table grid, the
Reversal Map System price-level histogram, and the Fibonacci retracement
tables. These are structurally different (wide tables, not sentences) and
lower-value for a first pass — they're in raw_text if you need to read
them, just not their own columns. Extend EXTRACTORS below if you want one
of them pulled out later.

WHAT THIS DOESN'T EVEN TRY TO HANDLE: the Weekly Timing Array color grid
and Watchlist tables you also shared are a different format entirely
(images, not text a report emails you), with a color legend I don't have
a source for (blue/magenta/yellow/red/cyan/grey per row — I'm not going
to guess what each one means; tell me the legend and I'll build that
parser too, or if you can copy the Watchlist table as text/CSV from
wherever it's rendered, that would parse the same reliable way this does).

Run: python parse_premium_commentary.py
Reads:  nothing by default (self-test only, see RAW_REPORTS below); paste
        new reports into RAW_REPORTS the same way add_breadth_week.py works
Writes: instrument_commentary.csv (appends; skips a (market, report_date)
        already in the file rather than duplicating)
"""
import csv
import datetime
import os
import re

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(DATA_DIR, "instrument_commentary.csv")

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def parse_socrates_date(text_date):
    """'Fri. Sep. 18, 2026' -> date(2026, 9, 18). Returns None (never
    guesses) if the format doesn't match exactly."""
    m = re.match(r"\w+\.\s+(\w{3})\.\s+(\d{1,2}),\s+(\d{4})", text_date.strip())
    if not m:
        return None
    mon_str, day, year = m.groups()
    if mon_str not in MONTHS:
        return None
    return datetime.date(int(year), MONTHS[mon_str], int(day))


HEADER_RE = re.compile(
    r"THE SOCRATES PREMIUM OVERVIEW COMMENTARY,\s*(.+?)\s+AS OF THE CLOSE OF\s+(.+?):"
)


def extract_header(text):
    """Returns (market, report_date) or (None, None). Refuses to parse
    further if this doesn't match — same rule as add_breadth_week.py
    refusing to guess week_of: no market name or date, no row."""
    m = HEADER_RE.search(text)
    if not m:
        return None, None
    market = m.group(1).strip()
    report_date = parse_socrates_date(m.group(2))
    return market, report_date


# Each extractor: (field names) -> regex -> group mapping. Independent of
# each other — one not matching doesn't block the rest.
FIELD_EXTRACTORS = {
    "last_close": (
        re.compile(r"closing today at (\d+)"),
        lambda m: float(m.group(1)),
    ),
    "_yoy": (
        re.compile(r"trading (up|down) about ([\d.]+)% for the year from last year's settlement of (\d+)"),
        lambda m: (
            round(float(m.group(2)) * (1 if m.group(1) == "up" else -1), 4),
            float(m.group(3)),
        ),
    ),
    "reversal_daily_bull_bear": (
        re.compile(r"next Daily Bullish Reversal to watch stands at (\d+) while the Daily Bearish Reversal lies at (\d+)"),
        lambda m: (float(m.group(1)), float(m.group(2))),
    ),
    "reversal_weekly_bull_bear": (
        re.compile(r"Using the Weekly level, the next Bullish Reversal to watch stands at (\d+) while the Weekly Bearish Reversal lies at (\d+)"),
        lambda m: (float(m.group(1)), float(m.group(2))),
    ),
    "reversal_monthly_bull_bear": (
        re.compile(r"Now moving to the broader Monthly level, the current Bullish Reversal stands at (\d+) while the Bearish Reversal lies at (\d+)"),
        lambda m: (float(m.group(1)), float(m.group(2))),
    ),
    "ecm_next_target_date": (
        re.compile(r"Our next ECM target remains (\w+\.\s+\w+\.\s+\d{1,2},\s+\d{4})"),
        lambda m: parse_socrates_date(m.group(1)),
    ),
}

TREND_CHANGE_RE = re.compile(
    r"^(Daily|Weekly|Monthly|Quarterly|Yearly)\s*\.{3,}\s*(-?\d+)\s*$", re.MULTILINE
)

RISK_TABLE_ROW_RE = re.compile(
    r"^(DAILY|WEEKLY|MONTHLY|QUARTERLY|YEARLY)\.{3,}\s+(\d+)\s*\|\s*([\d.]+)%\s*\|\s*(\d+)\s*\|\s*([\d.]+)%\s*\|",
    re.MULTILINE,
)


def extract_trend_change_points(text):
    """Scoped to the 'WIDE-RANGING CLOSING TREND CHANGE POINTS' section
    only — the same header words (Daily/Weekly/...) appear elsewhere in
    these reports with different meanings, so searching the whole text
    would risk picking up the wrong numbers."""
    start = text.find("WIDE-RANGING CLOSING TREND CHANGE POINTS")
    if start == -1:
        return {}
    window = text[start:start + 1500]
    out = {}
    for m in TREND_CHANGE_RE.finditer(window):
        level, value = m.group(1).lower(), float(m.group(2))
        out[f"trend_change_{level}"] = value
    return out


def extract_risk_table(text):
    """Scoped to the 'RISK FACTORS' section for the same reason as above."""
    start = text.find("RISK FACTORS")
    if start == -1:
        return {}
    window = text[start:start + 1500]
    out = {}
    for m in RISK_TABLE_ROW_RE.finditer(window):
        level = m.group(1).lower()
        out[f"risk_{level}_upside_price"] = float(m.group(2))
        out[f"risk_{level}_upside_pct"] = float(m.group(3))
        out[f"risk_{level}_downside_price"] = float(m.group(4))
        out[f"risk_{level}_downside_pct"] = float(m.group(5))
    return out


def parse_commentary(text):
    """Returns a dict matching instrument_commentary's columns, or None if
    the market/date header doesn't match (refuses to guess which report
    this even is). Any individual field that doesn't match its pattern is
    left out of the dict entirely (never a fabricated 0 or None-as-if-real)."""
    market, report_date = extract_header(text)
    if market is None or report_date is None:
        return None

    row = {"market": market, "report_date": report_date.isoformat(), "raw_text": text}

    for field, (pattern, extractor) in FIELD_EXTRACTORS.items():
        m = pattern.search(text)
        if not m:
            continue
        value = extractor(m)
        if field == "_yoy":
            row["pct_change_yoy"], row["prior_year_close"] = value
        elif field == "reversal_daily_bull_bear":
            row["reversal_daily_bull"], row["reversal_daily_bear"] = value
        elif field == "reversal_weekly_bull_bear":
            row["reversal_weekly_bull"], row["reversal_weekly_bear"] = value
        elif field == "reversal_monthly_bull_bear":
            row["reversal_monthly_bull"], row["reversal_monthly_bear"] = value
        elif field == "ecm_next_target_date":
            row["ecm_next_target_date"] = value.isoformat() if value else None
        else:
            row[field] = value

    row.update(extract_trend_change_points(text))
    row.update(extract_risk_table(text))
    return row


FIELDS = [
    "market", "report_date", "last_close", "prior_year_close", "pct_change_yoy",
    "reversal_daily_bull", "reversal_daily_bear",
    "reversal_weekly_bull", "reversal_weekly_bear",
    "reversal_monthly_bull", "reversal_monthly_bear",
    "trend_change_daily", "trend_change_weekly", "trend_change_monthly",
    "trend_change_quarterly", "trend_change_yearly",
    "risk_daily_upside_price", "risk_daily_upside_pct", "risk_daily_downside_price", "risk_daily_downside_pct",
    "risk_weekly_upside_price", "risk_weekly_upside_pct", "risk_weekly_downside_price", "risk_weekly_downside_pct",
    "risk_monthly_upside_price", "risk_monthly_upside_pct", "risk_monthly_downside_price", "risk_monthly_downside_pct",
    "risk_quarterly_upside_price", "risk_quarterly_upside_pct", "risk_quarterly_downside_price", "risk_quarterly_downside_pct",
    "risk_yearly_upside_price", "risk_yearly_upside_pct", "risk_yearly_downside_price", "risk_yearly_downside_pct",
    "ecm_next_target_date", "raw_text",
]

# Paste each new report as another triple-quoted string here, comma-separated
# — same pattern as add_breadth_week.py's RAW_REPORTS.
RAW_REPORTS = [
    """
THE SOCRATES PREMIUM OVERVIEW COMMENTARY, US DOLLAR V EURO ADJUSTED SPOT AS OF THE CLOSE OF Fri. Sep. 18, 2026: The US Dollar v Euro Adjusted Spot closing today at 11490 is immediately trading down about 2.22% for the year from last year's settlement of 11751. Caution is required for this market is starting to suggest it may now decline on the MONTHLY level. Immediately, this market has been rising for 2 months going into September reflecting that this has been only still, a bullish reactionary trend. As we stand right now, this market has made a new low breaking beneath the previous month's low reaching thus far 11459 while it's even trading beneath last month's low of 11505.


Up to now, we still have only a 2 month reaction rally from the low established during June. We must exceed the 3 month mark in order to imply that a trend is developing. When we look Closely at our Stochastic Momentum Hybrid Models on all levels of time collectively, this is what we see:
At this time the short-term Monthly Stochastic Momentum is in a bearish position. The last time this model began to turn downward was following 08/01/2026. At this time the short-term Yearly Stochastic Momentum is in a bullish position. This model has just turned bullish so we can see a bounce.

When we look broadly at the market on all levels of time collectively, this is what we see:
The Stochastic tone on the Daily level remains in a bearish broader posture at this time. Refer to the arrays for targets in time. This market is still within the normal trading Daily envelope where the range remains 11490 to 11660 on this level. The last Breakout Mode indicator took place on 07/30/2026. The last Crash Mode indicator took place on 07/22/2026.
The Stochastic tone on the Weekly level is starting to imply a return to a bearish broader posture at this time. Refer to the arrays for targets in time. This market is still within the normal trading Weekly envelope where the range remains 11152 to 11878 on this level. The last Breakout Mode indicator took place on the week of August 10th. The last Crash Mode indicator took place on the week of June 15th.

Our cyclical infused Stochastic has turned warning of a retest of support is now likely as the Blue has now crossed below the Red. This is further indicated by the pentration of the previous session lowand closing below that low.
.
Our next daily target is Friday September 18th whereby Friday September 25th remains that strongest target ahead on our Daily Array. However, our next daily target of Friday September 18th is also within our target Weekly Array target of 09/14/2026 whereas the strongest target ahead on our Weekly Array will be 10/05/2026. The last strongest target on our Monthly Array was August. Looking beyond the next key Monthly turning point in the Array we come to January, which is a Panic Cycle suggesting that will perhaps become the next target thereafter.

From an intraday trading perspective, our Daily Projected Resistance and Support targets for the day show the initial trading range with resistance at 11493 and support at 11481.

A closing above last year's high of 11919 will warn of perhaps new highs into next year. A closing below that number would warn that this year could be just a temporary high.

Economic Confidence Model CORRELATION

Here in US Dollar v Euro Adjusted Spot, we do find that this particular market has correlated with our Economic Confidence Model in the past. Our next ECM target remains Tue. Feb. 16, 2027. The Last turning point on the ECM cycle low to line up with this market was 2022 and 2017 and 2010 and 2005 and 2000 and 1994. The Last turning point on the ECM cycle high to line up with this market was 2018.

WEEKLY TIMING ARRAY PERSPECTIVE

On the Weekly Level, regarding the timing, there was a reasonable potential of a outside reversal moving into key target was the week of September 14th, that is reinforced by also a Directional Change Target. However, we also see that there is another Directional Change due in the next session and then the session thereafter warning this is a choppy period ahead given that the previous Weekly session of the week of September 7th was a high with the opposite trend implied thereafter into the week of September 21st, which is a Directional Change. As of the week of September 14th, this market has declined for 4 Weeks. The strongest target in the Weekly array is the week of October 5th for a turning point ahead, at least on a closing basis. There are 6 Weekly Directional Change targets starting from the week of September 14th to the week of November 23rd, suggesting a choppy coiling period for 5 Weeks. Don't forget, a Directional Change can also be a sharp dramatic move in the same direction, not just a change in direction.

MONTHLY TIMING ARRAY PERSPECTIVE

Our key target was August, that is reinforced by also a Directional Change Target. However, we also see that there is another Directional Change due in the next session and then the session thereafter warning this is a choppy period ahead yet since this market has penetrated the August low, then a further decline is possible into the next target of September. The strongest target in the Monthly array is February 2027 for a turning point ahead, at least on a closing basis. We have overall 3 Monthly Directional Change targets ahead and 1 that also aligns with a main turning point on the top line of the Array. Therefore, this target should be an important one. This target in time is August. Directional Change targets that align with the top line for turning points often unfold as the main cyclical events. Don't forget, a Directional Change can also be a sharp dramatic move in the same direction, not just a change in direction.

We closed the previous month at 11533Immediately, the market is somewhat bullish on our monthly indicating range models which has moved up from the previous month yet wasneutral.

MONTHLY TIMING TABLE FOR: 2026/08/01

| 8 | 9 | 10 | 11 | 12 | 1 | 2 | 3 | 4 | 5 | 6 | 7
--------------------------------------------------------
TURNING POINTS
| 44 | 36 | 48 | 52 | 44 | 40 | 60 | 32 | 24 | 28 | 28 | 28
DIRECTIONAL CHANGES
| 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1
PANIC CYCLES
| 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0
LONG-TERM EMPIRICAL
| 1 | 2 | 4 | 6 | 1 | 1 | 6 | 0 | 2 | 3 | 4 | 5
VOLATILITY
| 0 | 2 | 2 | 7 | 8 | 7 | 6 | 4 | 6 | 7 | 7 | 4

END OF QUARTER

The projected overhead technical resistance stands at 12157. The projected technical support resides at 11133. The next Quarterly Minor Bullish Reversal stands at 11497 with the next Quarterly Major Bullish Reversal standing at 14579. The next Quarterly Minor Bearish Reversal resides at 9612 whereas the next Quarterly Major Bearish Reversal is to be found at 10884. Immediately, the market is somewhat bullish on our indicating range models. However, the monthly level remains moderately bullish for now yet the weekly level is distinctly bearish. We also have a Minor Monthly Bearish, which is closer to the market right now. This resides at 10652 and therefore, even a month-end closing below this would signal a further retest of support is likely.

Therefore, when we put this all together, the various timing levels require our focus on the following Bearish Reversals for the close of this quarter. The numbers to watch are: 11395 and 10884.

BROADER OVERVIEW

The historical broader tone of the US Dollar v Euro Adjusted Spot has been a bearish consolidation following the high established back in 2008. Since then, this market has created 2 reaction highs which have been unable to break this overall protracted bearish consolidating trend. Still, the major low was made in 2022 and the market has bounced back for the last 4 years. The last Yearly Reversal to be elected was a Bullish at the close of 2025. However, where there was 1 reversal elected, there was also a Super Position which took place with 1 Bearish Reversal elected warning that this immediate signal has been suppressed by the opposite force warning we may not see immediate follow through.

This market remains in a positive position on the weekly to yearly levels of our indicating models. Pay attention to the Monthly level for any serious change in long-term trend ahead.

This past year alone, saw a price decline of about 9.21%. However, last year was also an outside reversal to the upside and this market closed above the previous year's high of 11216.

HYPOTHETICAL MODEL ANALYSIS

Applying our Tentative Hypothetical Models, we see that we have Daily Bullish Reversals that would be generated if we see another new low penetrating 11459. These Tentative Hypothetical Bullish Reversals would stand at 11559, 11589, 11603, and 11609, whereas a close above the previous high 11496 would tend to suggest that these Tentative Hypothetical Bullish Reversals will then become fixed as long as the low holds thereafter for at least several days. Moreover, the election of any of these Tentative Bullish Reversals during that session would signal that a bounce is unfolding and that such a low may stand. However, if we continue to make new lows, then these WHAT-IF Reversals will be replaced by a new set until the low becomes fixed.

Turning to our Tentative Hypothetical Models, we see that we have Weekly Bullish Reversals that would be generated if we see another new low penetrating 11459. These Tentative Hypothetical Bullish Reversals would stand at 11476, 11643, 11644, and 11715, whereas a close above the previous high 11602 would tend to suggest that these Tentative Hypothetical Bullish Reversals will then become fixed as long as the low holds thereafter for at least several days. Moreover, the election of any of these Tentative Bullish Reversals during that session would signal that a bounce is unfolding and that such a low may stand. However, if we continue to make new lows, then these WHAT-IF Reversals will be replaced by a new set until the low becomes fixed.

REVERSAL SYSTEM

Relying on our Reversal System, our next Daily Bullish Reversal to watch stands at 11554 while the Daily Bearish Reversal lies at 11460. This provides a very near-term 1.80% trading range. Using the Weekly level, the next Bullish Reversal to watch stands at 11590 while the Weekly Bearish Reversal lies at 11381. This provides a 1.80% trading range. Now moving to the broader Monthly level, the current Bullish Reversal stands at 11819 while the Bearish Reversal lies at 11395. This, naturally, gives us the main broad trading range of a 3.58%.

WIDE-RANGING CLOSING TREND CHANGE POINTS

Change in Trend Indicator
Daily ........ 11548
Weekly ....... 11505
Monthly ...... 11513
Quarterly .... 10863
Yearly ....... 10575

Note: This indicator identifies the tone of the market on each time level. A positive number indicates the market is still in a bullish posture on that time level. Negative numbers indicate that the market is in a bearish posture on that time level. The indication is provided only on a closing basis. The broader change in trend takes place only on the monthly to yearly levels. Those looking for exit strategies may look at these numbers on a closing basis per level. When a major turning point is approached according to our yearly models, ECM, and timing arrays, then you can move from the higher levels to the lower to exit a market closer to the turning point.

Immediately, we have broken below last month's low and that means we have generated a new What-If Monthly Bullish Reversal which lies above the present trading level at the general area of 11669 warning that this decline has still not punched through important overhead resistance. A monthly closing beneath this level will keep this market in a bearish tone.

RISK FACTORS
US Dollar v Euro Adjusted Spot Risk Table

----------------- UPSIDE RISK ----- DOWNSIDE RISK ---

DAILY......... 11554 | 0.557% | 11460 | 0.261% |
WEEKLY........ 11590 | 0.87% | 11381 | 0.948% |
MONTHLY....... 11819 | 2.863% | 11395 | 0.826% |
QUARTERLY..... 11916 | 3.707% | 10884 | 5.274% |
YEARLY........ 12093 | 5.248% | 10635 | 7.441% |

NORMAL DAILY TRADING ENVELOPE
Last Close Was. 11490

Envelope Top... 11660
Internal AvgL.. 11488
Internal AvgH.. 11569
Envelope Btm... 11490


PIVOT POINTS

Looking at our Pivot Points, the market is trading BELOW all three indicating numbers and that leaves this in a bearish position currently with resistance at 11492, 11507, and 11510 for this next trading session.

DAILY PIVOT POINTS
11492
11507
11510

Projected technical Support tomorrow lies at 11471 and 11486. Naturally, opening below this area will cause it to become resistance. Projected technical Resistance stands tomorrow at 11492 11508. Keep in mind that these targets can provide intraday resistance or closing resistance. Opening above this area will cause it to become support.
""",
]


def load_existing_keys():
    if not os.path.exists(OUT_CSV):
        return set()
    with open(OUT_CSV, encoding="utf-8") as f:
        return {(r["market"], r["report_date"]) for r in csv.DictReader(f)}


def main():
    existing = load_existing_keys()
    file_exists = os.path.exists(OUT_CSV)
    new_rows = []

    for raw in RAW_REPORTS:
        row = parse_commentary(raw)
        if row is None:
            print("SKIPPED a report: couldn't find the 'THE SOCRATES PREMIUM OVERVIEW COMMENTARY, "
                  "<market> AS OF THE CLOSE OF <date>:' header line — refusing to guess which report this is.")
            continue
        key = (row["market"], row["report_date"])
        if key in existing:
            print(f"SKIPPED {key}: already in {os.path.basename(OUT_CSV)}")
            continue
        new_rows.append(row)
        # Denominator excludes market/report_date (always present, or we
        # wouldn't have a row at all) and raw_text (always present, not a
        # "matched" field in the same sense).
        optional_fields = [f for f in FIELDS if f not in ("market", "report_date", "raw_text")]
        parsed_count = sum(1 for f in optional_fields if row.get(f) is not None)
        print(f"PARSED {key}: {parsed_count}/{len(optional_fields)} fields matched "
              f"(raw_text always kept regardless)")

    if new_rows:
        with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            if not file_exists:
                writer.writeheader()
            for row in new_rows:
                writer.writerow({k: row.get(k, "") for k in FIELDS})
        print(f"\nWrote {len(new_rows)} row(s) to {os.path.basename(OUT_CSV)}")
    else:
        print("\nNothing new to write.")


if __name__ == "__main__":
    main()
