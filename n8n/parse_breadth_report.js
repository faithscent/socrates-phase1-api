// Parser for the n8n "Parse Breadth Report" Code node — port of
// add_breadth_week.py's parse_report(), same regex approach: matches the
// "N Markets (or P%)" pattern in the fixed category order the platform
// always uses, so it doesn't depend on exact tabs/spacing from copy-paste.
//
// Tested standalone with `node parse_breadth_report.js` against the same
// two weeks (Sep 11, Sep 18, 2026) validated in the Python version before
// being embedded in the n8n Code node below.

const CATEGORY_ORDER = ["Stocks", "Currencies", "Stock Indices", "Bonds", "Commodities", "ETFs", "Crypto"];

const SECTION_HEADERS = {
  "The Reversal System": "reversal_system",
  "Timing Array Models": "timing_array",
  "Stochastics": "stochastics",
  "Indicating Ranges": "indicating_ranges",
  "Global Market Watch": "gmw",
};

const WEEK_RE = /close for Weekly\s+(\d{4}-\d{2}-\d{2})/;
const HEADLINE_RE = /^(Stocks|Currencies|Stock Indices|Bonds|Commodities|ETFs|Crypto):\s+([\d,]+)\s+Markets\s*\(or\s+([\d.]+)%\)\s+covered markets in this category are currently showing a\s+(.+?)\.\s*$/;
const CELL_RE = /([\d,]+)\s+Markets\s*\(or\s+([\d.]+)%\)/g;

function parseReport(text) {
  const weekMatch = text.match(WEEK_RE);
  if (!weekMatch) {
    throw new Error("Couldn't find 'close for Weekly YYYY-MM-DD' in this report — refusing to guess the week.");
  }
  const weekOf = weekMatch[1];
  const rows = [];

  // Headline lines
  for (const line of text.split("\n")) {
    const hm = line.match(HEADLINE_RE);
    if (hm) {
      const [, category, count, pct, metric] = hm;
      rows.push({
        week_of: weekOf, section: "headline", category,
        metric: metric.trim(), count: parseInt(count.replace(/,/g, ""), 10), pct: parseFloat(pct),
      });
    }
  }

  // Section tables
  let currentSection = null;
  for (const rawLine of text.split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;
    if (Object.prototype.hasOwnProperty.call(SECTION_HEADERS, line)) {
      currentSection = SECTION_HEADERS[line];
      continue;
    }
    if (!currentSection) continue;

    const cells = [...line.matchAll(CELL_RE)];
    if (cells.length !== CATEGORY_ORDER.length) continue; // not a data row — skip, don't guess

    const firstCellPos = line.search(CELL_RE);
    const metric = line.slice(0, firstCellPos).trim().replace(/[\t|]+$/, "").trim();

    cells.forEach((cellMatch, i) => {
      const [, count, pct] = cellMatch;
      rows.push({
        week_of: weekOf, section: currentSection, category: CATEGORY_ORDER[i],
        metric, count: parseInt(count.replace(/,/g, ""), 10), pct: parseFloat(pct),
      });
    });
  }

  return { weekOf, rows };
}

module.exports = { parseReport };

// ---- self-test when run directly ----
if (require.main === module) {
  const fs = require("fs");
  const sample = fs.readFileSync(process.argv[2] || "/dev/stdin", "utf8");
  const { weekOf, rows } = parseReport(sample);
  console.log(`week_of=${weekOf}, rows=${rows.length}`);
  console.log(rows.slice(0, 5));
  // sanity check: implied category totals should agree across timing_array metrics
  const totals = {};
  for (const r of rows) {
    if (r.section === "timing_array" && r.pct > 0) {
      const implied = Math.round(r.count / (r.pct / 100));
      totals[r.category] = totals[r.category] || [];
      totals[r.category].push(implied);
    }
  }
  console.log("implied totals by category (should be consistent per category):", totals);
}
