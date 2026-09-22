// Diffs this week's v_scorecard_wow rows against what's already in
// alerts_sent and decides which categories have a genuinely NEW signal
// worth a Telegram message. Tested standalone (node detect_new_alerts.js)
// against synthetic rows shaped like the real view/table output before
// being pasted into the n8n "Detect New Alerts" Code node.
//
// Thresholds are duplicated from scorecard.py / v_scorecard on purpose —
// see the comment in supabase_schema.sql. If you change one, change all
// three (scorecard.py, the SQL view, this file's BIG_SWING_THRESHOLD).

const BIG_SWING_THRESHOLD = 15.0; // points of score change week-over-week worth flagging on its own, even without crossing a call boundary

function detectNewAlerts(items) {
  // items: array of { __kind: "scorecard", ...v_scorecard_wow row } or
  //        { __kind: "alerted", category }
  const scorecardRows = items.filter((r) => r.__kind === "scorecard");
  const alertedCategories = new Set(
    items.filter((r) => r.__kind === "alerted").map((r) => r.category)
  );

  const out = [];
  for (const r of scorecardRows) {
    if (alertedCategories.has(r.category)) continue; // already sent for this category this week

    const reasons = [];

    if (r.prior_call !== null && r.prior_call !== undefined && r.call !== r.prior_call) {
      reasons.push(`regime flip: ${r.prior_call} -> ${r.call} (score ${r.score})`);
    }
    if (r.volatility_flag === true && r.prior_volatility_flag !== true) {
      reasons.push(`panic-cycle volatility flag just triggered (panic ${r.panic_cycle_pct}%)`);
    }
    const swing = r.score_change_from_prior_week;
    if (swing !== null && swing !== undefined && Math.abs(swing) >= BIG_SWING_THRESHOLD) {
      reasons.push(`big swing: score moved ${swing > 0 ? "+" : ""}${swing} this week`);
    }

    if (reasons.length > 0) {
      out.push({
        week_of: r.week_of,
        category: r.category,
        call: r.call,
        volatility_flag: r.volatility_flag,
        line: reasons.join("; "),
      });
    }
  }
  return out;
}

module.exports = { detectNewAlerts, BIG_SWING_THRESHOLD };

if (require.main === module) {
  // Scenario 1: Stocks flips CONSTRUCTIVE->CAUTION (regime flip), Bonds
  // has a big swing but no call change, Currencies unchanged (no alert),
  // Crypto already alerted this week (must be skipped even though it
  // also has a fresh volatility flag).
  const synthetic = [
    { __kind: "scorecard", week_of: "2026-09-18", category: "Stocks", net_reversal_bias: 12, net_high_low: 6, panic_cycle_pct: 10, score: 9.2, call: "CAUTION", volatility_flag: false, prior_call: "CONSTRUCTIVE", prior_volatility_flag: false, score_change_from_prior_week: 18.4 },
    { __kind: "scorecard", week_of: "2026-09-18", category: "Bonds", net_reversal_bias: 5, net_high_low: 4, panic_cycle_pct: 5, score: 4.6, call: "NEUTRAL", volatility_flag: false, prior_call: "NEUTRAL", prior_volatility_flag: false, score_change_from_prior_week: -16.0 },
    { __kind: "scorecard", week_of: "2026-09-18", category: "Currencies", net_reversal_bias: 1, net_high_low: 1, panic_cycle_pct: 2, score: 0.4, call: "NEUTRAL", volatility_flag: false, prior_call: "NEUTRAL", prior_volatility_flag: false, score_change_from_prior_week: 0.1 },
    { __kind: "scorecard", week_of: "2026-09-18", category: "Crypto", net_reversal_bias: 3, net_high_low: 2, panic_cycle_pct: 25, score: 3.8, call: "NEUTRAL", volatility_flag: true, prior_call: "NEUTRAL", prior_volatility_flag: false, score_change_from_prior_week: 1.0 },
    { __kind: "alerted", category: "Crypto" },
  ];

  const result = detectNewAlerts(synthetic);
  console.log(JSON.stringify(result, null, 2));

  if (result.length !== 2) throw new Error(`expected 2 new alerts (Stocks, Bonds), got ${result.length}`);
  if (!result.some((r) => r.category === "Stocks" && r.line.includes("regime flip"))) {
    throw new Error("expected Stocks regime-flip alert");
  }
  if (!result.some((r) => r.category === "Bonds" && r.line.includes("big swing"))) {
    throw new Error("expected Bonds big-swing alert");
  }
  if (result.some((r) => r.category === "Currencies")) {
    throw new Error("Currencies should not alert — nothing crossed a threshold");
  }
  if (result.some((r) => r.category === "Crypto")) {
    throw new Error("Crypto should be suppressed — already in alerts_sent this week");
  }
  console.log("self-test passed: regime flip, big swing, no-signal, and already-alerted dedup all handled correctly");
}
