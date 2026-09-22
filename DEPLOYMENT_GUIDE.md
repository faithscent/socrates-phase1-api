# Railway Deployment Guide — Step-by-Step

Deploy SOCrates Phase 1 API to Railway (free) in 15 minutes using GitHub.

---

## Prerequisites

Before starting, ensure you have:
- ✅ GitHub account (free)
- ✅ Railway account (free, sign up with GitHub)
- ✅ Git installed locally
- ✅ Code in `/home/claude/work/` directory
- ✅ Supabase URL and API key (from your existing setup)

---

## STEP 1: Prepare Your Local Repository (5 minutes)

### 1a. Initialize Git in your project directory

```bash
cd /home/claude/work

# Initialize git repo
git init

# Set your Git user (replace with your details)
git config user.email "your-email@example.com"
git config user.name "Your Name"

# Check status
git status
```

**What you should see:** Multiple files ready to be staged (api.py, requirements.txt, etc.)

### 1b. Stage all files for commit

```bash
# Add all files
git add .

# Verify what will be committed
git status
```

**You should see:**
```
new file:   api.py
new file:   requirements.txt
new file:   Dockerfile
new file:   railway.json
new file:   csv_loader.py
...and many more files
```

### 1c. Create initial commit

```bash
git commit -m "Initial commit: SOCrates Phase 1 API with all 6 engines"
```

---

## STEP 2: Create GitHub Repository (3 minutes)

### 2a. Go to GitHub and create new repo

1. Go to **https://github.com/new**
2. **Repository name:** `socrates-phase1` (or any name you want)
3. **Description:** "SOCrates Phase 1 Technical Intelligence API"
4. **Visibility:** Public (Railway requires this for free tier)
5. **Do NOT initialize** README, .gitignore, or license (you already have these)
6. Click **Create repository**

### 2b. Add remote and push code

After creating the GitHub repo, you'll see instructions. Copy the commands:

```bash
# Add GitHub as remote (replace USERNAME/socrates-phase1 with your info)
git remote add origin https://github.com/USERNAME/socrates-phase1.git

# Rename branch to main (if needed)
git branch -M main

# Push code to GitHub
git push -u origin main
```

**Wait for push to complete** (2-3 minutes for first push)

### Verify on GitHub

- Go to your repo: `https://github.com/USERNAME/socrates-phase1`
- You should see all your files (api.py, Dockerfile, etc.)

---

## STEP 3: Deploy to Railway (5 minutes)

### 3a. Sign up for Railway with GitHub

1. Go to **https://railway.app**
2. Click **Deploy with GitHub** (or **Sign up**)
3. Authorize Railway to access your GitHub account
4. After authorization, you'll see Railway dashboard

### 3b. Create new project from GitHub

1. Click **New Project**
2. Click **Deploy from GitHub repo**
3. Select your GitHub repo: `socrates-phase1`
4. Click **Deploy**

**Railway will:**
- Clone your repo
- Build Docker image
- Start the API server
- Assign you a URL like `https://socrates-phase1-production.up.railway.app`

**Wait 3-5 minutes for build to complete.**

### 3c. Monitor deployment

1. In Railway dashboard, click your project
2. Click **Deployments** tab
3. Watch the build progress
4. When complete, you'll see a green checkmark ✅

**If build fails:**
- Click **Logs** tab to see error
- Common issues: missing dependencies (check requirements.txt)

---

## STEP 4: Configure Environment Variables (2 minutes)

Your API needs Supabase credentials to persist data.

### 4a. In Railway dashboard

1. Click your project
2. Click **Variables** tab
3. Add these environment variables:

| Variable | Value | Get from |
|----------|-------|----------|
| `SUPABASE_URL` | `https://your-project.supabase.co` | Supabase dashboard → Settings → API |
| `SUPABASE_KEY` | `eyJ...` (long string) | Supabase dashboard → Settings → API → anon key |
| `FLASK_ENV` | `production` | Type this value |
| `FLASK_DEBUG` | `False` | Type this value |
| `PORT` | `5000` | Type this value |

**Don't have Supabase credentials?**
- Go to **https://supabase.com**
- Create new project (free)
- Copy credentials from Settings → API

### 4b. Save and Railway redeploys automatically

Railway will restart your app with new environment variables.

---

## STEP 5: Verify Deployment (2 minutes)

### 5a. Get your API URL

In Railway dashboard:
1. Click your project
2. Click **Settings** tab
3. Look for **Service URL** or **Production Domain**
4. Should look like: `https://socrates-phase1-production.up.railway.app`

### 5b. Test the health endpoint

```bash
# Replace with your actual Railway URL
curl https://socrates-phase1-production.up.railway.app/health

# Should return:
# {
#   "status": "healthy",
#   "service": "SOCrates V2 Phase 1",
#   "engines": ["SWING_V1", "STRUCTURE_V1", ...]
# }
```

### 5c. Test analysis endpoint

```bash
curl -X POST https://socrates-phase1-production.up.railway.app/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "QQQ",
    "timeframe": "1D",
    "current_price": 450.0,
    "bars": [
      {"timestamp": "2024-01-01T00:00:00", "open": 400, "high": 410, "low": 395, "close": 405, "volume": 1000000},
      {"timestamp": "2024-01-02T00:00:00", "open": 405, "high": 415, "low": 400, "close": 410, "volume": 1200000},
      {"timestamp": "2024-01-03T00:00:00", "open": 410, "high": 420, "low": 405, "close": 415, "volume": 1100000}
    ]
  }'

# Should return 200 with analysis report
```

**✅ If both return successfully, your API is live!**

---

## STEP 6: Connect n8n Workflow (Hostinger) (5 minutes)

Now connect your Hostinger n8n instance to the live API.

### 6a. In n8n workflow

1. Open your n8n instance on Hostinger
2. Create new workflow (or edit existing one)
3. Add **HTTP Request** node
4. Configure:

```
Method: POST
URL: https://socrates-phase1-production.up.railway.app/analyze

Headers:
  Content-Type: application/json

Body:
{
  "symbol": "QQQ",
  "timeframe": "1D",
  "current_price": {{$json.current_price}},
  "bars": {{$json.bars}}
}
```

### 6b. Test in n8n

1. Click **Test** button
2. Provide test data for `current_price` and `bars`
3. Should return full analysis report

### 6c. Add to your cron workflow

In your Hostinger cron job workflow:

```
[Trigger: Cron (daily at 4pm)]
  ↓
[Get Market Data from your source]
  ↓
[HTTP POST to: https://socrates-phase1-production.up.railway.app/analyze]
  ↓
[Save response to Supabase]
  ↓
[Done]
```

---

## STEP 7: Set Hostinger Cron Job (2 minutes)

### 7a. In Hostinger control panel

1. Go to **Cron Jobs**
2. Click **Create New Cron Job**
3. Configure:

```
Command: curl -X POST https://n8n.yourdomain.com/webhook/daily-analysis
Minute: 0
Hour: 16 (4 PM UTC)
Day: * (every day)
```

4. Click **Save**

### 7b. Verify cron is running

- Wait for scheduled time, or
- Manually trigger n8n workflow to test

---

## STEP 8: Monitor Your Deployment

### View logs in Railway

```bash
# In Railway dashboard
1. Click your project
2. Click "Logs" tab
3. See real-time API requests and errors
```

### Common issues & fixes

| Issue | Fix |
|-------|-----|
| 404 Not Found | Check URL is correct (copy from Railway dashboard) |
| 500 Error | Check logs in Railway dashboard |
| Timeout | API might be too slow; check Supabase connection |
| "Cannot connect" | Railway URL might not be live; wait 5 min for build |

### Keep Railway running

Free tier Railway sleeps after 7 days of inactivity. To keep it running:
- Make sure n8n cron job hits it daily, OR
- Set up a simple monitoring service that pings `/health` every few hours

---

## DONE! 🎉

Your API is now live and ready to use.

### Quick Checklist

- ✅ GitHub repo created with your code
- ✅ Railroad deployment live
- ✅ `/health` endpoint responding
- ✅ `/analyze` endpoint working
- ✅ Environment variables set (Supabase credentials)
- ✅ n8n connected to live API
- ✅ Hostinger cron job configured

### What happens now

1. **Hostinger cron** triggers daily at 4 PM UTC
2. **n8n workflow** calls your live API
3. **Phase 1 API** analyzes market data (all 6 engines)
4. **Results** saved to Supabase
5. **Dashboard** queries Supabase for latest analysis

---

## Troubleshooting

### API won't start

```bash
# Check Dockerfile, ensure:
# - Python 3.11 is available
# - requirements.txt exists
# - api.py is in root directory
```

### "Cannot find module socrates_data"

```bash
# Make sure you pushed the entire directory structure:
# /socrates_data/technical/
# /socrates_data/technical/tests/
# All files must be in repo
```

### Supabase connection errors

```bash
# Verify environment variables in Railway:
1. Go to Variables tab
2. Check SUPABASE_URL and SUPABASE_KEY are correct
3. Railway should auto-restart after changes
```

### n8n can't reach API

```bash
# Test connectivity:
curl https://socrates-phase1-production.up.railway.app/health

# If fails, API might still be building (wait 5 min)
# Or check Railway logs for errors
```

---

## Support & Next Steps

**See also:**
- `API_DOCUMENTATION.md` — Complete API reference
- `README.md` — Architecture and features
- Railway docs: https://docs.railway.app

**Questions?**
1. Check Railway logs for error details
2. Verify environment variables are set
3. Test health endpoint manually with curl

---

**Deployment Time: ~15 minutes**  
**Uptime: 99%+ on Railway free tier**  
**Cost: $0 (Railway free tier)**
