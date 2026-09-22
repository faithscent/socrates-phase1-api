# Quick Reference — Deployment & n8n Integration

## Your Deployment Checklist

### ✅ Step 1: GitHub Push (5 min)

```bash
cd /home/claude/work
git init
git config user.email "your@email.com"
git config user.name "Your Name"
git add .
git commit -m "Initial commit: SOCrates Phase 1"
git remote add origin https://github.com/USERNAME/socrates-phase1.git
git branch -M main
git push -u origin main
```

**Result:** Code on GitHub at `https://github.com/USERNAME/socrates-phase1`

---

### ✅ Step 2: Deploy to Railway (5 min)

1. Go to https://railway.app
2. Sign up with GitHub
3. Click **New Project** → **Deploy from GitHub**
4. Select `socrates-phase1` repo
5. Click **Deploy**
6. Wait 3-5 minutes for build

**Result:** API URL like `https://socrates-phase1-production.up.railway.app`

---

### ✅ Step 3: Add Environment Variables (2 min)

In Railway dashboard, go to **Variables** tab and add:

```
SUPABASE_URL = https://your-project.supabase.co
SUPABASE_KEY = eyJ... (from Supabase settings)
FLASK_ENV = production
FLASK_DEBUG = False
PORT = 5000
```

---

### ✅ Step 4: Test API (2 min)

```bash
# Test health endpoint
curl https://YOUR-RAILWAY-URL/health

# Test analysis endpoint
curl -X POST https://YOUR-RAILWAY-URL/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "QQQ",
    "timeframe": "1D",
    "current_price": 450.0,
    "bars": [
      {"timestamp": "2024-01-01T00:00:00", "open": 400, "high": 410, "low": 395, "close": 405, "volume": 1000000},
      {"timestamp": "2024-01-02T00:00:00", "open": 405, "high": 415, "low": 400, "close": 410, "volume": 1200000}
    ]
  }'
```

---

### ✅ Step 5: Connect n8n Workflow (3 min)

**In n8n on Hostinger:**

1. Add **HTTP Request** node
2. Set method to: **POST**
3. Set URL to: `https://YOUR-RAILWAY-URL/analyze`
4. Set body to:

```json
{
  "symbol": "{{$json.symbol}}",
  "timeframe": "{{$json.timeframe}}",
  "current_price": {{$json.current_price}},
  "bars": {{$json.bars}}
}
```

5. Test the node
6. Wire to your data source and save nodes

---

### ✅ Step 6: Set Hostinger Cron (2 min)

In Hostinger control panel → **Cron Jobs**:

```
Command: curl -X POST https://n8n.yourdomain.com/webhook/daily-analysis
Minute: 0
Hour: 16
Day: *
Month: *
Weekday: *
```

This triggers daily at 4 PM UTC.

---

## Environment Variables

### Get Supabase Credentials

1. Go to https://supabase.com
2. Go to your project → **Settings** → **API**
3. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **Anon Key** (under "Project API keys") → `SUPABASE_KEY`

### Add to Railway

1. Click your project in Railway
2. Click **Variables**
3. Paste credentials
4. Click **Deploy** to restart

---

## Your API Endpoints

### Health Check
```
GET https://YOUR-RAILWAY-URL/health

Response:
{
  "status": "healthy",
  "service": "SOCrates V2 Phase 1",
  "engines": ["SWING_V1", "STRUCTURE_V1", "FIB_V1", "ELLIOTT_V1", "CONFLUENCE_V1", "TARGET_V1"]
}
```

### Analyze (Main Endpoint)
```
POST https://YOUR-RAILWAY-URL/analyze

Request:
{
  "symbol": "QQQ",
  "timeframe": "1D",
  "current_price": 450.0,
  "bars": [ ... ]
}

Response:
{
  "success": true,
  "report": { ... complete analysis ... },
  "timestamp": "2024-01-15T12:34:56Z"
}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect to URL" | Wait 5 min; build might still running |
| "500 Error" | Check Railway logs; likely missing env var |
| "404 Not Found" | Check URL is correct (copy from Railway) |
| "Timeout" | API might be slow; check Supabase connection |
| n8n can't reach API | Check firewall; API is public so should work |

---

## Important Files

| File | Purpose |
|------|---------|
| `api.py` | Flask server; entry point |
| `Dockerfile` | Container config for Railway |
| `requirements.txt` | Python dependencies |
| `railway.json` | Railway deployment config |
| `csv_loader.py` | Load CSV data (optional) |
| `socrates_data/technical/*.py` | 6 analysis engines |

---

## Links You'll Need

- **GitHub:** https://github.com/USERNAME/socrates-phase1
- **Railway:** https://railway.app/dashboard
- **Supabase:** https://supabase.com/dashboard
- **n8n (Hostinger):** https://n8n.yourdomain.com

---

## Cost

- **Railway:** FREE (generous free tier)
- **Supabase:** FREE (5 GB storage, good for learning)
- **n8n (Hostinger):** Whatever your hosting costs
- **API:** $0 to run on Railway

**Total monthly cost: $0** ✅

---

## Support

**Read in order:**
1. `DEPLOYMENT_GUIDE.md` (step-by-step)
2. `API_DOCUMENTATION.md` (API reference)
3. Check Railway logs if something fails

---

**Estimated time to go live: 15-20 minutes** ⏱️

**Questions? Come back to DEPLOYMENT_GUIDE.md — every step explained.**
