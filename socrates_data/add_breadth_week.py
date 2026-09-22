"""
add_breadth_week.py — parse the automated "Socrates Platform Market
Activity Summary" (weekly, whole-platform breadth by category) and append
it to platform_breadth.csv in long/tidy format.

This is a different data source from weekly_macro_trends.csv: that one is
your own per-market read (QQQ, HYG, USO, ...); this one is the platform's
own aggregate stats across its ~1,600+ markets, grouped into seven
categories (Stocks, Currencies, Stock Indices, Bonds, Commodities, ETFs,
Crypto). Kept as a separate table on purpose — different grain, don't
merge them.

Usage:
    1. Paste each week's full summary text as one triple-quoted string
       into RAW_REPORTS below (one entry per week — you said you have 6).
    2. Run: python add_breadth_week.py
    3. Rows land in platform_breadth.csv, one row per
       (week_of, section, category, metric).

The parser is regex-based against the "<N> Markets (or <pct>%)" pattern
that repeats through the report, in the fixed category order the platform
always uses (Stocks, Currencies, Stock Indices, Bonds, Commodities, ETFs,
Crypto) — it doesn't depend on exact tabs/spaces, so copy-pasting straight
from the email/webpage should work as-is.
"""
import csv
import os
import re
import sys

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
BREADTH_CSV = os.path.join(DATA_DIR, "platform_breadth.csv")
FIELDS = ["week_of", "section", "category", "metric", "count", "pct"]

CATEGORY_ORDER = ["Stocks", "Currencies", "Stock Indices", "Bonds",
                  "Commodities", "ETFs", "Crypto"]

SECTION_HEADERS = {
    "The Reversal System": "reversal_system",
    "Timing Array Models": "timing_array",
    "Stochastics": "stochastics",
    "Indicating Ranges": "indicating_ranges",
    "Global Market Watch": "gmw",
}

WEEK_RE = re.compile(r"close for Weekly\s+(\d{4}-\d{2}-\d{2})")
HEADLINE_RE = re.compile(
    r"^(Stocks|Currencies|Stock Indices|Bonds|Commodities|ETFs|Crypto):\s+"
    r"([\d,]+)\s+Markets\s*\(or\s+([\d.]+)%\)\s+covered markets in this "
    r"category are currently showing a\s+(.+?)\.\s*$",
    re.MULTILINE,
)
CELL_RE = re.compile(r"([\d,]+)\s+Markets\s*\(or\s+([\d.]+)%\)")

# ---------------------------------------------------------------------------
# PASTE EACH WEEK'S FULL REPORT TEXT HERE (one triple-quoted string per
# week), then run: python add_breadth_week.py
# ---------------------------------------------------------------------------
RAW_REPORTS = [
    r"""
Socrates Platform Market Activity Summary for 14th August 2026 (Weekly)
This is an automated update intended to share a broad view of market behavior across the entire Socrates Platform, as of the close for Weekly 2026-08-14. Members can dive deeper in their research and analysis by logging in to review the full Socrates Markets list, or focus specifically on the Socrates Market Movers, or their own Watchlist(s), and Market Subscription Alerts. Note, this summary is based on monthly price data, not daily data within the month.
Stocks: 251 Markets (or 45.31%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Currencies: 53 Markets (or 49.07%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Stock Indices: 105 Markets (or 56.45%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Bonds: 96 Markets (or 54.86%) covered markets in this category are currently showing a Closed < 1% of Bearish Reversal.
Commodities: 28 Markets (or 37.84%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
ETFs: 94 Markets (or 49.74%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Crypto: 2 Markets (or 33.33%) covered markets in this category are currently showing a Direction Change Signal Within 3 weeks.

The Reversal System
⌃
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
Elected a Bullish Reversal	101 Markets (or 18.23%)	7 Markets (or 6.48%)	42 Markets (or 22.58%)	20 Markets (or 11.43%)	8 Markets (or 10.81%)	38 Markets (or 20.11%)	0 Markets (or 0.0%)
Elected a Bearish Reversal	23 Markets (or 4.15%)	10 Markets (or 9.26%)	4 Markets (or 2.15%)	8 Markets (or 4.57%)	4 Markets (or 5.41%)	4 Markets (or 2.12%)	0 Markets (or 0.0%)
Closed < 1% of Bullish Reversal	77 Markets (or 13.9%)	44 Markets (or 40.74%)	69 Markets (or 37.1%)	87 Markets (or 49.71%)	11 Markets (or 14.86%)	70 Markets (or 37.04%)	0 Markets (or 0.0%)
Closed < 1% of Bearish Reversal	14 Markets (or 2.53%)	46 Markets (or 42.59%)	3 Markets (or 1.61%)	96 Markets (or 54.86%)	2 Markets (or 2.7%)	16 Markets (or 8.47%)	0 Markets (or 0.0%)

Timing Array Models
⌃
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
Direction Change Signal Within 3 weeks	39 Markets (or 7.04%)	4 Markets (or 3.7%)	13 Markets (or 6.99%)	7 Markets (or 4.0%)	12 Markets (or 16.22%)	14 Markets (or 7.41%)	2 Markets (or 33.33%)
Aggregate High Signal Within 3 weeks	251 Markets (or 45.31%)	53 Markets (or 49.07%)	105 Markets (or 56.45%)	71 Markets (or 40.57%)	28 Markets (or 37.84%)	94 Markets (or 49.74%)	2 Markets (or 33.33%)
Aggregate Low Signal Within 3 weeks	103 Markets (or 18.59%)	31 Markets (or 28.7%)	26 Markets (or 13.98%)	32 Markets (or 18.29%)	10 Markets (or 13.51%)	30 Markets (or 15.87%)	0 Markets (or 0.0%)
Panic Cycle Signal Within 3 weeks	112 Markets (or 20.22%)	16 Markets (or 14.81%)	43 Markets (or 23.12%)	26 Markets (or 14.86%)	15 Markets (or 20.27%)	41 Markets (or 21.69%)	1 Markets (or 16.67%)

Stochastics
⌃
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
All Stochastics > 80 (potentially overbought)	43 Markets (or 7.76%)	12 Markets (or 11.11%)	45 Markets (or 24.19%)	10 Markets (or 5.71%)	4 Markets (or 5.41%)	15 Markets (or 7.94%)	0 Markets (or 0.0%)
All Stochastics < 20 (potentially oversold)	23 Markets (or 4.15%)	8 Markets (or 7.41%)	1 Markets (or 0.54%)	5 Markets (or 2.86%)	4 Markets (or 5.41%)	12 Markets (or 6.35%)	0 Markets (or 0.0%)

Indicating Ranges
⌃
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
All Indicators are Bullish	134 Markets (or 24.19%)	9 Markets (or 8.33%)	95 Markets (or 51.08%)	21 Markets (or 12.0%)	6 Markets (or 8.11%)	74 Markets (or 39.15%)	0 Markets (or 0.0%)
All Indicators are Bearish	34 Markets (or 6.14%)	11 Markets (or 10.19%)	5 Markets (or 2.69%)	10 Markets (or 5.71%)	6 Markets (or 8.11%)	26 Markets (or 13.76%)	0 Markets (or 0.0%)

Global Market Watch
⌃
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
GMW is signaling a possible Important Event	76 Markets (or 13.72%)	14 Markets (or 12.96%)	22 Markets (or 11.83%)	10 Markets (or 5.71%)	7 Markets (or 9.46%)	25 Markets (or 13.23%)	0 Markets (or 0.0%)
GMW is signaling a possible High or Low	143 Markets (or 25.81%)	24 Markets (or 22.22%)	56 Markets (or 30.11%)	41 Markets (or 23.43%)	14 Markets (or 18.92%)	52 Markets (or 27.51%)	0 Markets (or 0.0%)
""",
    r"""
Socrates Platform Market Activity Summary for 21st August 2026 (Weekly)
This is an automated update intended to share a broad view of market behavior across the entire Socrates Platform, as of the close for Weekly 2026-08-21. Members can dive deeper in their research and analysis by logging in to review the full Socrates Markets list, or focus specifically on the Socrates Market Movers, or their own Watchlist(s), and Market Subscription Alerts. Note, this summary is based on monthly price data, not daily data within the month.
Stocks: 250 Markets (or 45.21%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Currencies: 53 Markets (or 49.07%) covered markets in this category are currently showing a Closed < 1% of Bearish Reversal.
Stock Indices: 125 Markets (or 67.2%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Bonds: 102 Markets (or 58.29%) covered markets in this category are currently showing a Closed < 1% of Bearish Reversal.
Commodities: 28 Markets (or 37.84%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
ETFs: 106 Markets (or 56.08%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Crypto: 3 Markets (or 50.0%) covered markets in this category are currently showing a Elected a Bullish Reversal.
The Reversal System
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
Elected a Bullish Reversal	122 Markets (or 22.06%)	10 Markets (or 9.26%)	22 Markets (or 11.83%)	31 Markets (or 17.71%)	23 Markets (or 31.08%)	33 Markets (or 17.46%)	3 Markets (or 50.0%)
Elected a Bearish Reversal	39 Markets (or 7.05%)	20 Markets (or 18.52%)	2 Markets (or 1.08%)	22 Markets (or 12.57%)	4 Markets (or 5.41%)	5 Markets (or 2.65%)	0 Markets (or 0.0%)
Closed < 1% of Bullish Reversal	72 Markets (or 13.02%)	43 Markets (or 39.81%)	33 Markets (or 17.74%)	99 Markets (or 56.57%)	17 Markets (or 22.97%)	47 Markets (or 24.87%)	1 Markets (or 16.67%)
Closed < 1% of Bearish Reversal	18 Markets (or 3.25%)	53 Markets (or 49.07%)	3 Markets (or 1.61%)	102 Markets (or 58.29%)	3 Markets (or 4.05%)	16 Markets (or 8.47%)	0 Markets (or 0.0%)
Timing Array Models
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
Direction Change Signal Within 3 weeks	47 Markets (or 8.5%)	8 Markets (or 7.41%)	23 Markets (or 12.37%)	25 Markets (or 14.29%)	13 Markets (or 17.57%)	19 Markets (or 10.05%)	2 Markets (or 33.33%)
Aggregate High Signal Within 3 weeks	250 Markets (or 45.21%)	34 Markets (or 31.48%)	125 Markets (or 67.2%)	63 Markets (or 36.0%)	28 Markets (or 37.84%)	106 Markets (or 56.08%)	2 Markets (or 33.33%)
Aggregate Low Signal Within 3 weeks	130 Markets (or 23.51%)	37 Markets (or 34.26%)	20 Markets (or 10.75%)	29 Markets (or 16.57%)	13 Markets (or 17.57%)	24 Markets (or 12.7%)	0 Markets (or 0.0%)
Panic Cycle Signal Within 3 weeks	113 Markets (or 20.43%)	18 Markets (or 16.67%)	42 Markets (or 22.58%)	36 Markets (or 20.57%)	9 Markets (or 12.16%)	42 Markets (or 22.22%)	1 Markets (or 16.67%)
Stochastics
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
All Stochastics > 80 (potentially overbought)	13 Markets (or 2.35%)	11 Markets (or 10.19%)	41 Markets (or 22.04%)	13 Markets (or 7.43%)	5 Markets (or 6.76%)	11 Markets (or 5.82%)	0 Markets (or 0.0%)
All Stochastics < 20 (potentially oversold)	17 Markets (or 3.07%)	7 Markets (or 6.48%)	1 Markets (or 0.54%)	8 Markets (or 4.57%)	4 Markets (or 5.41%)	9 Markets (or 4.76%)	0 Markets (or 0.0%)
Indicating Ranges
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
All Indicators are Bullish	140 Markets (or 25.32%)	7 Markets (or 6.48%)	97 Markets (or 52.15%)	33 Markets (or 18.86%)	20 Markets (or 27.03%)	67 Markets (or 35.45%)	2 Markets (or 33.33%)
All Indicators are Bearish	39 Markets (or 7.05%)	10 Markets (or 9.26%)	2 Markets (or 1.08%)	27 Markets (or 15.43%)	5 Markets (or 6.76%)	20 Markets (or 10.58%)	0 Markets (or 0.0%)
Global Market Watch
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
GMW is signaling a possible Important Event	63 Markets (or 11.39%)	19 Markets (or 17.59%)	22 Markets (or 11.83%)	16 Markets (or 9.14%)	18 Markets (or 24.32%)	21 Markets (or 11.11%)	0 Markets (or 0.0%)
GMW is signaling a possible High or Low	206 Markets (or 37.25%)	23 Markets (or 21.3%)	70 Markets (or 37.63%)	33 Markets (or 18.86%)	12 Markets (or 16.22%)	53 Markets (or 28.04%)	0 Markets (or 0.0%)
""",
    r"""
Socrates Platform Market Activity Summary for 28th August 2026 (Weekly)
This is an automated update intended to share a broad view of market behavior across the entire Socrates Platform, as of the close for Weekly 2026-08-28. Members can dive deeper in their research and analysis by logging in to review the full Socrates Markets list, or focus specifically on the Socrates Market Movers, or their own Watchlist(s), and Market Subscription Alerts. Note, this summary is based on monthly price data, not daily data within the month.
Stocks: 263 Markets (or 47.47%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Currencies: 47 Markets (or 43.52%) covered markets in this category are currently showing a Closed < 1% of Bearish Reversal.
Stock Indices: 124 Markets (or 66.67%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Bonds: 106 Markets (or 60.57%) covered markets in this category are currently showing a Closed < 1% of Bearish Reversal.
Commodities: 31 Markets (or 41.89%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
ETFs: 106 Markets (or 56.08%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Crypto: 4 Markets (or 66.67%) covered markets in this category are currently showing a All Indicators are Bullish.
The Reversal System
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
Elected a Bullish Reversal	64 Markets (or 11.55%)	9 Markets (or 8.33%)	24 Markets (or 12.9%)	19 Markets (or 10.86%)	16 Markets (or 21.62%)	7 Markets (or 3.7%)	2 Markets (or 33.33%)
Elected a Bearish Reversal	31 Markets (or 5.6%)	7 Markets (or 6.48%)	4 Markets (or 2.15%)	15 Markets (or 8.57%)	3 Markets (or 4.05%)	3 Markets (or 1.59%)	0 Markets (or 0.0%)
Closed < 1% of Bullish Reversal	50 Markets (or 9.03%)	45 Markets (or 41.67%)	45 Markets (or 24.19%)	100 Markets (or 57.14%)	18 Markets (or 24.32%)	30 Markets (or 15.87%)	0 Markets (or 0.0%)
Closed < 1% of Bearish Reversal	27 Markets (or 4.87%)	47 Markets (or 43.52%)	4 Markets (or 2.15%)	106 Markets (or 60.57%)	1 Markets (or 1.35%)	17 Markets (or 8.99%)	0 Markets (or 0.0%)
Timing Array Models
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
Direction Change Signal Within 3 weeks	50 Markets (or 9.03%)	9 Markets (or 8.33%)	18 Markets (or 9.68%)	34 Markets (or 19.43%)	4 Markets (or 5.41%)	15 Markets (or 7.94%)	0 Markets (or 0.0%)
Aggregate High Signal Within 3 weeks	263 Markets (or 47.47%)	36 Markets (or 33.33%)	124 Markets (or 66.67%)	80 Markets (or 45.71%)	31 Markets (or 41.89%)	106 Markets (or 56.08%)	2 Markets (or 33.33%)
Aggregate Low Signal Within 3 weeks	124 Markets (or 22.38%)	27 Markets (or 25.0%)	19 Markets (or 10.22%)	40 Markets (or 22.86%)	19 Markets (or 25.68%)	35 Markets (or 18.52%)	3 Markets (or 50.0%)
Panic Cycle Signal Within 3 weeks	105 Markets (or 18.95%)	15 Markets (or 13.89%)	48 Markets (or 25.81%)	22 Markets (or 12.57%)	11 Markets (or 14.86%)	35 Markets (or 18.52%)	0 Markets (or 0.0%)
Stochastics
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
All Stochastics > 80 (potentially overbought)	29 Markets (or 5.23%)	12 Markets (or 11.11%)	45 Markets (or 24.19%)	15 Markets (or 8.57%)	5 Markets (or 6.76%)	14 Markets (or 7.41%)	0 Markets (or 0.0%)
All Stochastics < 20 (potentially oversold)	21 Markets (or 3.79%)	7 Markets (or 6.48%)	2 Markets (or 1.08%)	8 Markets (or 4.57%)	4 Markets (or 5.41%)	13 Markets (or 6.88%)	0 Markets (or 0.0%)
Indicating Ranges
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
All Indicators are Bullish	129 Markets (or 23.29%)	14 Markets (or 12.96%)	78 Markets (or 41.94%)	35 Markets (or 20.0%)	19 Markets (or 25.68%)	59 Markets (or 31.22%)	4 Markets (or 66.67%)
All Indicators are Bearish	45 Markets (or 8.12%)	13 Markets (or 12.04%)	3 Markets (or 1.61%)	28 Markets (or 16.0%)	3 Markets (or 4.05%)	8 Markets (or 4.23%)	0 Markets (or 0.0%)
Global Market Watch
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
GMW is signaling a possible Important Event	53 Markets (or 9.57%)	16 Markets (or 14.81%)	20 Markets (or 10.75%)	13 Markets (or 7.43%)	12 Markets (or 16.22%)	20 Markets (or 10.58%)	3 Markets (or 50.0%)
GMW is signaling a possible High or Low	159 Markets (or 28.7%)	19 Markets (or 17.59%)	45 Markets (or 24.19%)	54 Markets (or 30.86%)	16 Markets (or 21.62%)	52 Markets (or 27.51%)	1 Markets (or 16.67%)
""",
    r"""
Socrates Platform Market Activity Summary for 4th September 2026 (Weekly)
This is an automated update intended to share a broad view of market behavior across the entire Socrates Platform, as of the close for Weekly 2026-09-04. Members can dive deeper in their research and analysis by logging in to review the full Socrates Markets list, or focus specifically on the Socrates Market Movers, or their own Watchlist(s), and Market Subscription Alerts. Note, this summary is based on monthly price data, not daily data within the month.
Stocks: 239 Markets (or 43.14%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Currencies: 53 Markets (or 49.07%) covered markets in this category are currently showing a Closed < 1% of Bearish Reversal.
Stock Indices: 74 Markets (or 39.78%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Bonds: 98 Markets (or 55.68%) covered markets in this category are currently showing a Closed < 1% of Bearish Reversal.
Commodities: 29 Markets (or 39.19%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
ETFs: 87 Markets (or 46.03%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Crypto: 6 Markets (or 100.0%) covered markets in this category are currently showing a All Indicators are Bullish.
The Reversal System
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
Elected a Bullish Reversal	50 Markets (or 9.03%)	10 Markets (or 9.26%)	18 Markets (or 9.68%)	37 Markets (or 21.02%)	15 Markets (or 20.27%)	19 Markets (or 10.05%)	3 Markets (or 50.0%)
Elected a Bearish Reversal	48 Markets (or 8.66%)	7 Markets (or 6.48%)	3 Markets (or 1.61%)	26 Markets (or 14.77%)	2 Markets (or 2.7%)	13 Markets (or 6.88%)	0 Markets (or 0.0%)
Closed < 1% of Bullish Reversal	54 Markets (or 9.75%)	42 Markets (or 38.89%)	40 Markets (or 21.51%)	94 Markets (or 53.41%)	19 Markets (or 25.68%)	37 Markets (or 19.58%)	2 Markets (or 33.33%)
Closed < 1% of Bearish Reversal	26 Markets (or 4.69%)	53 Markets (or 49.07%)	13 Markets (or 6.99%)	98 Markets (or 55.68%)	2 Markets (or 2.7%)	22 Markets (or 11.64%)	0 Markets (or 0.0%)
Timing Array Models
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
Direction Change Signal Within 3 weeks	64 Markets (or 11.55%)	10 Markets (or 9.26%)	7 Markets (or 3.76%)	14 Markets (or 7.95%)	7 Markets (or 9.46%)	11 Markets (or 5.82%)	0 Markets (or 0.0%)
Aggregate High Signal Within 3 weeks	239 Markets (or 43.14%)	37 Markets (or 34.26%)	74 Markets (or 39.78%)	59 Markets (or 33.52%)	29 Markets (or 39.19%)	87 Markets (or 46.03%)	2 Markets (or 33.33%)
Aggregate Low Signal Within 3 weeks	141 Markets (or 25.45%)	31 Markets (or 28.7%)	27 Markets (or 14.52%)	46 Markets (or 26.14%)	17 Markets (or 22.97%)	41 Markets (or 21.69%)	2 Markets (or 33.33%)
Panic Cycle Signal Within 3 weeks	103 Markets (or 18.59%)	22 Markets (or 20.37%)	40 Markets (or 21.51%)	25 Markets (or 14.2%)	9 Markets (or 12.16%)	55 Markets (or 29.1%)	1 Markets (or 16.67%)
Stochastics
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
All Stochastics > 80 (potentially overbought)	35 Markets (or 6.32%)	12 Markets (or 11.11%)	44 Markets (or 23.66%)	21 Markets (or 11.93%)	5 Markets (or 6.76%)	22 Markets (or 11.64%)	0 Markets (or 0.0%)
All Stochastics < 20 (potentially oversold)	14 Markets (or 2.53%)	7 Markets (or 6.48%)	2 Markets (or 1.08%)	11 Markets (or 6.25%)	4 Markets (or 5.41%)	17 Markets (or 8.99%)	0 Markets (or 0.0%)
Indicating Ranges
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
All Indicators are Bullish	102 Markets (or 18.41%)	14 Markets (or 12.96%)	42 Markets (or 22.58%)	48 Markets (or 27.27%)	20 Markets (or 27.03%)	35 Markets (or 18.52%)	6 Markets (or 100.0%)
All Indicators are Bearish	41 Markets (or 7.4%)	10 Markets (or 9.26%)	2 Markets (or 1.08%)	56 Markets (or 31.82%)	5 Markets (or 6.76%)	20 Markets (or 10.58%)	0 Markets (or 0.0%)
Global Market Watch
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
GMW is signaling a possible Important Event	37 Markets (or 6.68%)	16 Markets (or 14.81%)	9 Markets (or 4.84%)	9 Markets (or 5.11%)	13 Markets (or 17.57%)	15 Markets (or 7.94%)	0 Markets (or 0.0%)
GMW is signaling a possible High or Low	189 Markets (or 34.12%)	31 Markets (or 28.7%)	53 Markets (or 28.49%)	41 Markets (or 23.3%)	16 Markets (or 21.62%)	47 Markets (or 24.87%)	1 Markets (or 16.67%)
""",
    r"""
Socrates Platform Market Activity Summary for 11th September 2026 (Weekly)
This is an automated update intended to share a broad view of market behavior across the entire Socrates Platform, as of the close for Weekly 2026-09-11. Members can dive deeper in their research and analysis by logging in to review the full Socrates Markets list, or focus specifically on the Socrates Market Movers, or their own Watchlist(s), and Market Subscription Alerts. Note, this summary is based on monthly price data, not daily data within the month.
Stocks: 226 Markets (or 40.79%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Currencies: 49 Markets (or 45.37%) covered markets in this category are currently showing a Closed < 1% of Bullish Reversal.
Stock Indices: 89 Markets (or 47.85%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Bonds: 102 Markets (or 57.95%) covered markets in this category are currently showing a Closed < 1% of Bearish Reversal.
Commodities: 31 Markets (or 41.89%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
ETFs: 94 Markets (or 49.74%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Crypto: 3 Markets (or 50.0%) covered markets in this category are currently showing a Panic Cycle Signal Within 3 weeks.
The Reversal System
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
Elected a Bullish Reversal	32 Markets (or 5.78%)	8 Markets (or 7.41%)	14 Markets (or 7.53%)	56 Markets (or 31.82%)	12 Markets (or 16.22%)	19 Markets (or 10.05%)	0 Markets (or 0.0%)
Elected a Bearish Reversal	79 Markets (or 14.26%)	8 Markets (or 7.41%)	30 Markets (or 16.13%)	62 Markets (or 35.23%)	1 Markets (or 1.35%)	43 Markets (or 22.75%)	0 Markets (or 0.0%)
Closed < 1% of Bullish Reversal	27 Markets (or 4.87%)	49 Markets (or 45.37%)	17 Markets (or 9.14%)	92 Markets (or 52.27%)	10 Markets (or 13.51%)	22 Markets (or 11.64%)	0 Markets (or 0.0%)
Closed < 1% of Bearish Reversal	40 Markets (or 7.22%)	49 Markets (or 45.37%)	33 Markets (or 17.74%)	102 Markets (or 57.95%)	2 Markets (or 2.7%)	37 Markets (or 19.58%)	0 Markets (or 0.0%)
Timing Array Models
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
Direction Change Signal Within 3 weeks	53 Markets (or 9.57%)	8 Markets (or 7.41%)	5 Markets (or 2.69%)	5 Markets (or 2.84%)	10 Markets (or 13.51%)	12 Markets (or 6.35%)	1 Markets (or 16.67%)
Aggregate High Signal Within 3 weeks	226 Markets (or 40.79%)	43 Markets (or 39.81%)	89 Markets (or 47.85%)	66 Markets (or 37.5%)	31 Markets (or 41.89%)	94 Markets (or 49.74%)	0 Markets (or 0.0%)
Aggregate Low Signal Within 3 weeks	143 Markets (or 25.81%)	33 Markets (or 30.56%)	31 Markets (or 16.67%)	48 Markets (or 27.27%)	23 Markets (or 31.08%)	33 Markets (or 17.46%)	2 Markets (or 33.33%)
Panic Cycle Signal Within 3 weeks	106 Markets (or 19.13%)	20 Markets (or 18.52%)	33 Markets (or 17.74%)	15 Markets (or 8.52%)	9 Markets (or 12.16%)	44 Markets (or 23.28%)	3 Markets (or 50.0%)
Stochastics
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
All Stochastics > 80 (potentially overbought)	17 Markets (or 3.07%)	12 Markets (or 11.11%)	18 Markets (or 9.68%)	27 Markets (or 15.34%)	3 Markets (or 4.05%)	0 Markets (or 0.0%)	0 Markets (or 0.0%)
All Stochastics < 20 (potentially oversold)	24 Markets (or 4.33%)	9 Markets (or 8.33%)	0 Markets (or 0.0%)	13 Markets (or 7.39%)	4 Markets (or 5.41%)	18 Markets (or 9.52%)	0 Markets (or 0.0%)
Indicating Ranges
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
All Indicators are Bullish	65 Markets (or 11.73%)	13 Markets (or 12.04%)	25 Markets (or 13.44%)	59 Markets (or 33.52%)	15 Markets (or 20.27%)	26 Markets (or 13.76%)	1 Markets (or 16.67%)
All Indicators are Bearish	74 Markets (or 13.36%)	13 Markets (or 12.04%)	3 Markets (or 1.61%)	76 Markets (or 43.18%)	4 Markets (or 5.41%)	29 Markets (or 15.34%)	0 Markets (or 0.0%)
Global Market Watch
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
GMW is signaling a possible Important Event	69 Markets (or 12.45%)	13 Markets (or 12.04%)	37 Markets (or 19.89%)	30 Markets (or 17.05%)	7 Markets (or 9.46%)	23 Markets (or 12.17%)	2 Markets (or 33.33%)
GMW is signaling a possible High or Low	140 Markets (or 25.27%)	20 Markets (or 18.52%)	66 Markets (or 35.48%)	57 Markets (or 32.39%)	17 Markets (or 22.97%)	44 Markets (or 23.28%)	3 Markets (or 50.0%)
""",
    r"""
Socrates Platform Market Activity Summary for 18th September 2026 (Weekly)
This is an automated update intended to share a broad view of market behavior across the entire Socrates Platform, as of the close for Weekly 2026-09-18. Members can dive deeper in their research and analysis by logging in to review the full Socrates Markets list, or focus specifically on the Socrates Market Movers, or their own Watchlist(s), and Market Subscription Alerts. Note, this summary is based on monthly price data, not daily data within the month.
Stocks: 194 Markets (or 35.02%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Currencies: 50 Markets (or 46.3%) covered markets in this category are currently showing a Closed < 1% of Bullish Reversal.
Stock Indices: 70 Markets (or 37.63%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Bonds: 96 Markets (or 54.55%) covered markets in this category are currently showing a Closed < 1% of Bearish Reversal.
Commodities: 35 Markets (or 47.3%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
ETFs: 78 Markets (or 41.27%) covered markets in this category are currently showing a Aggregate High Signal Within 3 weeks.
Crypto: 4 Markets (or 66.67%) covered markets in this category are currently showing a GMW is signaling a possible High or Low.
The Reversal System
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
Elected a Bullish Reversal	32 Markets (or 5.78%)	16 Markets (or 14.81%)	8 Markets (or 4.3%)	33 Markets (or 18.75%)	7 Markets (or 9.46%)	9 Markets (or 4.76%)	2 Markets (or 33.33%)
Elected a Bearish Reversal	91 Markets (or 16.43%)	11 Markets (or 10.19%)	35 Markets (or 18.82%)	17 Markets (or 9.66%)	7 Markets (or 9.46%)	40 Markets (or 21.16%)	0 Markets (or 0.0%)
Closed < 1% of Bullish Reversal	25 Markets (or 4.51%)	50 Markets (or 46.3%)	12 Markets (or 6.45%)	84 Markets (or 47.73%)	11 Markets (or 14.86%)	12 Markets (or 6.35%)	2 Markets (or 33.33%)
Closed < 1% of Bearish Reversal	52 Markets (or 9.39%)	42 Markets (or 38.89%)	31 Markets (or 16.67%)	96 Markets (or 54.55%)	4 Markets (or 5.41%)	37 Markets (or 19.58%)	0 Markets (or 0.0%)
Timing Array Models
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
Direction Change Signal Within 3 weeks	26 Markets (or 4.69%)	10 Markets (or 9.26%)	4 Markets (or 2.15%)	4 Markets (or 2.27%)	7 Markets (or 9.46%)	9 Markets (or 4.76%)	1 Markets (or 16.67%)
Aggregate High Signal Within 3 weeks	194 Markets (or 35.02%)	45 Markets (or 41.67%)	70 Markets (or 37.63%)	61 Markets (or 34.66%)	35 Markets (or 47.3%)	78 Markets (or 41.27%)	3 Markets (or 50.0%)
Aggregate Low Signal Within 3 weeks	141 Markets (or 25.45%)	32 Markets (or 29.63%)	56 Markets (or 30.11%)	60 Markets (or 34.09%)	16 Markets (or 21.62%)	44 Markets (or 23.28%)	0 Markets (or 0.0%)
Panic Cycle Signal Within 3 weeks	103 Markets (or 18.59%)	34 Markets (or 31.48%)	34 Markets (or 18.28%)	19 Markets (or 10.8%)	10 Markets (or 13.51%)	48 Markets (or 25.4%)	3 Markets (or 50.0%)
Stochastics
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
All Stochastics > 80 (potentially overbought)	12 Markets (or 2.17%)	10 Markets (or 9.26%)	8 Markets (or 4.3%)	33 Markets (or 18.75%)	3 Markets (or 4.05%)	0 Markets (or 0.0%)	0 Markets (or 0.0%)
All Stochastics < 20 (potentially oversold)	32 Markets (or 5.78%)	6 Markets (or 5.56%)	2 Markets (or 1.08%)	25 Markets (or 14.2%)	5 Markets (or 6.76%)	19 Markets (or 10.05%)	0 Markets (or 0.0%)
Indicating Ranges
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
All Indicators are Bullish	53 Markets (or 9.57%)	17 Markets (or 15.74%)	20 Markets (or 10.75%)	60 Markets (or 34.09%)	9 Markets (or 12.16%)	14 Markets (or 7.41%)	2 Markets (or 33.33%)
All Indicators are Bearish	95 Markets (or 17.15%)	10 Markets (or 9.26%)	7 Markets (or 3.76%)	72 Markets (or 40.91%)	8 Markets (or 10.81%)	31 Markets (or 16.4%)	0 Markets (or 0.0%)
Global Market Watch
STOCKS	CURRENCIES	STOCK INDICES	BONDS	COMMODITIES	ETFS	CRYPTO
GMW is signaling a possible Important Event	73 Markets (or 13.18%)	16 Markets (or 14.81%)	29 Markets (or 15.59%)	25 Markets (or 14.2%)	5 Markets (or 6.76%)	21 Markets (or 11.11%)	2 Markets (or 33.33%)
GMW is signaling a possible High or Low	184 Markets (or 33.21%)	15 Markets (or 13.89%)	64 Markets (or 34.41%)	30 Markets (or 17.05%)	25 Markets (or 33.78%)	54 Markets (or 28.57%)	4 Markets (or 66.67%)
""",
    # Paste weeks 3-6 here as additional triple-quoted strings, comma-separated.
]
# ---------------------------------------------------------------------------


def parse_report(text: str):
    """Return a list of row-dicts for one week's report text."""
    m = WEEK_RE.search(text)
    if not m:
        raise ValueError(
            "Couldn't find 'close for Weekly YYYY-MM-DD' in this report — "
            "can't determine week_of, refusing to guess it."
        )
    week_of = m.group(1)
    rows = []

    # Headline: one line per category, e.g.
    # "Stocks: 226 Markets (or 40.79%) ... showing a Aggregate High Signal Within 3 weeks."
    for hm in HEADLINE_RE.finditer(text):
        category, count, pct, metric = hm.groups()
        rows.append({
            "week_of": week_of, "section": "headline", "category": category,
            "metric": metric.strip(), "count": count.replace(",", ""), "pct": pct,
        })

    # Section tables
    lines = text.splitlines()
    current_section = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in SECTION_HEADERS:
            current_section = SECTION_HEADERS[stripped]
            continue
        if current_section is None:
            continue
        cells = CELL_RE.findall(stripped)
        if len(cells) != len(CATEGORY_ORDER):
            # not a data row for this section (e.g. the column-header row,
            # or the row didn't match cleanly) — skip rather than guess
            continue
        # metric label = everything before the first numeric cell match
        first_cell_pos = CELL_RE.search(stripped).start()
        metric = stripped[:first_cell_pos].strip(" \t|")
        for category, (count, pct) in zip(CATEGORY_ORDER, cells):
            rows.append({
                "week_of": week_of, "section": current_section,
                "category": category, "metric": metric,
                "count": count.replace(",", ""), "pct": pct,
            })

    return week_of, rows


def append_rows(rows, csv_path: str = BREADTH_CSV) -> None:
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists or os.path.getsize(csv_path) == 0:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def existing_weeks(csv_path: str = BREADTH_CSV) -> set:
    if not os.path.exists(csv_path):
        return set()
    with open(csv_path, encoding="utf-8") as f:
        return {row["week_of"] for row in csv.DictReader(f)}


def main():
    already = existing_weeks()
    total_written = 0
    for raw in RAW_REPORTS:
        if not raw.strip():
            continue
        week_of, rows = parse_report(raw)
        if week_of in already:
            print(f"SKIPPED {week_of}: already in {os.path.basename(BREADTH_CSV)} "
                  f"(remove it there first if you want to re-import)")
            continue
        append_rows(rows)
        already.add(week_of)
        total_written += len(rows)
        print(f"{week_of}: wrote {len(rows)} rows "
              f"({len(rows) // len(CATEGORY_ORDER)} metrics x {len(CATEGORY_ORDER)} categories, incl. headline)")

    if total_written == 0:
        print("Nothing new written. Paste report text into RAW_REPORTS and re-run.")
    else:
        print(f"Done — {total_written} total rows written to {os.path.basename(BREADTH_CSV)}")


if __name__ == "__main__":
    main()
