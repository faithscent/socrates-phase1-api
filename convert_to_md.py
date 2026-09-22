#!/usr/bin/env python3
"""
Mechanical structural conversion of the Socrates master database txt into
Markdown. This does NOT rewrite, summarize, or reinterpret any content —
it only maps existing structural markers (════ dividers, SECTION headers,
TRADE: labels, etc.) onto Markdown syntax so the file gets headers/folding/
outline support in an editor. Every line of substantive text is passed
through unchanged.

Section 14 (the weekly macro trend table) is dropped from this file since
that data now lives in the CSV files under socrates_data/ instead.
"""
import re
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "SOCRATES_MASTER_DATABASE_V6.2.77.txt"
DST = sys.argv[2] if len(sys.argv) > 2 else "SOCRATES_MASTER_DATABASE_V6.2.77_REFERENCE.md"
CUTOFF_LINE = int(sys.argv[3]) if len(sys.argv) > 3 else None  # 1-indexed; drop everything from here on

HEAVY_DIVIDER = re.compile(r"^═+$")
LIGHT_DIVIDER = re.compile(r"^─+$")
SECTION_RE = re.compile(r"^SECTION\s+(\d+):\s*(.+)$")
TRADE_RE = re.compile(r"^TRADE:\s*(.+)$")
CHANGES_RE = re.compile(r"^CHANGES IN\s+(V[\d.]+[a-z]?)\s*[—-]?\s*(.*)$")
ARRAY_RE = re.compile(r"^ARRAY EXTRACTION\s*[—-]\s*(.+)$")
GMW_LOG_RE = re.compile(r"^GMW LOG\s*[—-]\s*(.+)$")
ELLIOTT_RE = re.compile(r"^ELLIOTT WAVE COUNT\s*[—-]\s*(.+)$")
STRESS_LOG_RE = re.compile(r"^MARKET STRESS GAUGES\s*[—-]\s*(.+)$")

def convert(lines, cutoff=None):
    out = ["<!-- Mechanically converted from SOCRATES_MASTER_DATABASE_V6.2.77.txt.",
           "     Structural markers only; no content was rewritten or reinterpreted.",
           "     Section 14 (weekly macro trend table) lives in socrates_data/*.csv now. -->",
           ""]
    if cutoff:
        lines = lines[:cutoff]
    prev_blank = False
    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        if HEAVY_DIVIDER.match(stripped) or LIGHT_DIVIDER.match(stripped):
            # collapse to a single markdown rule, but don't emit doubled rules
            if out and out[-1].strip() == "---":
                continue
            out.append("")
            out.append("---")
            continue

        m = SECTION_RE.match(stripped)
        if m:
            out.append("")
            out.append(f"## Section {m.group(1)}: {m.group(2)}")
            out.append("")
            continue

        m = TRADE_RE.match(stripped)
        if m:
            out.append("")
            out.append(f"### TRADE: {m.group(1)}")
            continue

        m = CHANGES_RE.match(stripped)
        if m:
            tail = f" — {m.group(2)}" if m.group(2) else ""
            out.append("")
            out.append(f"#### Changes in {m.group(1)}{tail}")
            continue

        m = ARRAY_RE.match(stripped)
        if m:
            out.append("")
            out.append(f"#### Array extraction — {m.group(1)}")
            continue

        m = GMW_LOG_RE.match(stripped)
        if m:
            out.append("")
            out.append(f"#### GMW log — {m.group(1)}")
            continue

        m = ELLIOTT_RE.match(stripped)
        if m:
            out.append("")
            out.append(f"#### Elliott Wave count — {m.group(1)}")
            continue

        m = STRESS_LOG_RE.match(stripped)
        if m:
            out.append("")
            out.append(f"#### Market stress gauges — {m.group(1)}")
            continue

        # bold field labels like "Status:", "Entry:", "NEEDS:" at line start
        line2 = re.sub(r"^([A-Za-z][A-Za-z0-9 /]{0,28}:)(\s)", r"**\1**\2", line)
        out.append(line2)

    return "\n".join(out) + "\n"

def main():
    with open(SRC, "r", encoding="utf-8") as f:
        lines = f.readlines()
    md = convert(lines, CUTOFF_LINE)
    with open(DST, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {DST} ({len(md.splitlines())} lines) from {SRC} ({len(lines)} source lines, cutoff={CUTOFF_LINE})")

if __name__ == "__main__":
    main()
