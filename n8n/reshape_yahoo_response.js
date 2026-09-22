// Reshapes a Yahoo Finance chart-API response (v8/finance/chart/{symbol})
// into { date, symbol, close } rows for the n8n "Reshape Yahoo Response"
// Code node. Tested standalone against a synthetic response matching
// Yahoo's known v8 chart schema before being embedded in the workflow —
// I don't have live access to the real endpoint from this session (see
// README-n8n.md), so this is shape-tested, not tested against a live
// response. Verify it once against a real pull after import.

function reshapeYahooResponse(chartResponse) {
  const result = chartResponse?.chart?.result?.[0];
  if (!result) {
    const err = chartResponse?.chart?.error;
    throw new Error(`No result in Yahoo response${err ? `: ${err.description || JSON.stringify(err)}` : ""}`);
  }
  // Yahoo's own response echoes back the symbol it resolved — read it from
  // there instead of trying to carry the requested symbol through the HTTP
  // Request node's output (which n8n version differences make fragile).
  const symbol = result.meta?.symbol;
  if (!symbol) throw new Error("Yahoo response has no result.meta.symbol — response shape may have changed.");
  const timestamps = result.timestamp || [];
  const closes = result.indicators?.quote?.[0]?.close || [];

  const rows = [];
  for (let i = 0; i < timestamps.length; i++) {
    const close = closes[i];
    if (close === null || close === undefined) continue; // non-trading session in range — skip, don't fabricate
    const date = new Date(timestamps[i] * 1000).toISOString().slice(0, 10);
    rows.push({ date, symbol, close: Number(close) });
  }
  return rows;
}

module.exports = { reshapeYahooResponse };

if (require.main === module) {
  // Synthetic response matching Yahoo's known v8 chart schema, for a shape
  // test only (not real prices).
  const fakeResponse = {
    chart: {
      result: [{
        meta: { symbol: "QQQ" },
        timestamp: [1757548800, 1757635200, 1757721600],
        indicators: { quote: [{ close: [123.45, null, 125.10] }] },
      }],
      error: null,
    },
  };
  const rows = reshapeYahooResponse(fakeResponse);
  console.log(rows);
  if (rows.length !== 2) throw new Error("expected null close to be skipped");
  console.log("shape test passed (null close correctly skipped, 2 rows produced)");
}
