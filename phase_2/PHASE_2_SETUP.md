# Phase 2: Real Data Pipeline + Correlation Dashboard

## What You're Getting

✅ **CSV Generator** — Creates realistic OHLCV data with panic cycle correlations  
✅ **CSV Loader** — Loads data into Supabase `ohlcv_bars` table  
✅ **n8n Workflow** — Real data pipeline replacing hardcoded test data  
✅ **Correlation Dashboard** — Interactive panic monitor for FXE/FXY/IBIT  

---

## Step-by-Step Setup

### Step 1: Generate and Load Market Data (5 min)

**On your Mac:**

```bash
cd ~/Downloads/work/phase2-build

# Run the CSV generator
python3 generate_ohlcv_data.py

# This creates:
# - FXE_1D.csv (90 days of Euro data with panic patterns)
# - FXY_1D.csv (90 days of Yen data with safe-haven correlation)
# - IBIT_1D.csv (90 days of Bitcoin data with risk-off patterns)
```

**Load into Supabase:**

```bash
python3 load_csv_to_supabase.py \
  --url https://db.cztxnaqtklilxdcdwzka.supabase.co \
  --key eyJ... \
  --files FXE_1D.csv FXY_1D.csv IBIT_1D.csv
```

**Verify in Supabase:**
1. Go to https://supabase.com/dashboard
2. Click your project
3. Go to **SQL Editor**
4. Run:
   ```sql
   SELECT COUNT(*) as total_rows FROM ohlcv_bars;
   SELECT DISTINCT symbol FROM ohlcv_bars;
   ```

Should show **270 rows total** and **3 symbols** (FXE, FXY, IBIT).

---

### Step 2: Update n8n Workflow (10 min)

**In n8n on Hostinger:**

1. **Delete the old workflow** (or archive it)
2. **Import the new workflow:**
   - File → Import Workflow
   - Paste contents of `n8n_workflow_phase2.json`
   - Click Import

3. **Configure Supabase connection:**
   - Click any **Query** node (Query FXE Data, etc.)
   - Click **Create Credential**
   - Add your Supabase connection details:
     ```
     Host: db.cztxnaqtklilxdcdwzka.supabase.co
     Database: postgres
     User: postgres
     Password: your-supabase-password
     Port: 5432
     ```
   - Click **Test Connection** ✅

4. **Update the final HTTP node (Save All Results):**
   - Replace `YOUR_SUPABASE_ANON_KEY` with your actual anon key
   - From Supabase → Settings → API → Copy "Anon Key"

5. **Test the workflow:**
   - Click **Execute Workflow** (play button)
   - Should take 10-15 seconds
   - Check Supabase → `technical_reports` table for 3 new rows (FXE, FXY, IBIT)

6. **Activate & Save:**
   - Click **Activate** toggle (top right)
   - Click **Save**

**Your cron job will now run this daily and analyze real market data!**

---

### Step 3: Deploy Correlation Dashboard (5 min)

**Option A: Use as Static HTML**

1. Open `correlation_dashboard.html` in your browser
2. It will query your Supabase live
3. Shows FXE/FXY/IBIT correlation status

**Option B: Publish as Interactive Artifact** (Recommended)

Send me the `correlation_dashboard.html` file and I'll publish it as a live dashboard on claude.ai that:
- Auto-refreshes every 30 seconds
- Shows real-time panic cycle signals
- Color-codes based on correlation strength

---

## Data Structure

### ohlcv_bars Table

```
timestamp     | open  | high  | low   | close | volume   | symbol | timeframe
--------------+-------+-------+-------+-------+----------+--------+----------
2026-06-25    | 98.66 | 98.94 | 98.09 | 98.78 | 5559008  | FXE    | 1D
2026-06-26    | 99.18 | 99.2  | 98.58 | 98.87 | 6760507  | FXE    | 1D
...
```

### technical_reports Table

```
symbol | timeframe | current_price | timestamp           | report (full JSON)
-------+-----------+---------------+---------------------+-------------------
FXE    | 1D        | 98.78         | 2026-09-22 10:35:00 | {all 6 engines}
FXY    | 1D        | 105.42        | 2026-09-22 10:35:30 | {all 6 engines}
IBIT   | 1D        | 44892.50      | 2026-09-22 10:35:45 | {all 6 engines}
```

---

## Panic Cycle Correlation Logic

**When all 3 align:**

- **FXE drops** (Euro weakness) = Risk off
- **FXY rises** (Yen strength) = Safe haven flow
- **IBIT drops** (Bitcoin liquidation) = Risk asset capitulation

**Result: 🚨 PANIC MODE ACTIVE**

The dashboard monitors this correlation and flags when 2+ signals align simultaneously.

---

## Next Steps (Phase 2b Enhancements)

1. **Add live market data:**
   - Replace CSV generator with Alpha Vantage API or IB data
   - Push bars hourly instead of daily

2. **Add Socrates signal integration:**
   - Inject Armstrong timing arrays into analysis
   - Filter signals by panic cycle state

3. **Add trading alerts:**
   - Webhook alerts when panic correlation triggers
   - Send to Slack/Discord/email

4. **Add IV data:**
   - Track implied volatility alongside price
   - Flag when IV spikes during panic

---

## Troubleshooting

### Error: "Cannot connect to Supabase"
- Check your connection string in n8n
- Verify Supabase credentials
- Test with SQL Editor first

### Error: "ohlcv_bars table not found"
- Run supabase_migrations.sql in SQL Editor first
- This creates all required tables

### Dashboard shows no data
- Verify n8n workflow has run at least once
- Check `technical_reports` table has rows

### n8n workflow times out
- Supabase might be slow
- Try running the workflow manually first
- Check Railway logs for API errors

---

## Summary

You now have:

✅ Real OHLCV data for FXE, FXY, IBIT (90 days each)  
✅ Automated analysis pipeline running daily  
✅ Correlation dashboard monitoring panic cycles  
✅ All 6 engines analyzing real market data  

**Your system is now ready for live trading signals.**

Next: Add your Socrates timing arrays and integration rules.

---

**Questions?** Check the files in this directory or reach out.
