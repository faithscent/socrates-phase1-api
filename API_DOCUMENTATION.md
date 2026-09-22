# SOCrates V2 Phase 1 — REST API Documentation

Complete technical intelligence pipeline exposed as HTTP endpoints for integration with n8n, Hostinger cron jobs, and web dashboards.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [API Endpoints](#api-endpoints)
3. [Request/Response Schema](#requestresponse-schema)
4. [Integration Examples](#integration-examples)
5. [Error Handling](#error-handling)
6. [Performance & Limits](#performance--limits)
7. [Deployment](#deployment)

---

## Quick Start

### Prerequisites

- Python 3.11+
- Flask 3.0+
- Phase 1 technical analysis engines installed

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start API server
python api.py
```

The API will be available at `http://localhost:5000`

### Cloud Deployment (Recommended for Hostinger)

Deploy to cloud platform supporting Python (Heroku, Railway, PythonAnywhere, etc.):

```bash
# Typical cloud deployment
git push heroku main  # or your provider's equivalent
```

---

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Purpose:** Verify API is running and list available engines

**Response:**

```json
{
  "status": "healthy",
  "service": "SOCrates V2 Phase 1",
  "timestamp": "2024-01-15T12:34:56.789Z",
  "engines": [
    "SWING_V1",
    "STRUCTURE_V1",
    "FIB_V1",
    "ELLIOTT_V1",
    "CONFLUENCE_V1",
    "TARGET_V1"
  ]
}
```

**Example:**

```bash
curl http://api.socrates.local/health
```

---

### 2. Complete Technical Analysis

**Endpoint:** `POST /analyze`

**Purpose:** Run all 6 engines on market data and return unified technical intelligence report

#### Request Schema

**Content-Type:** `application/json`

```json
{
  "symbol": "QQQ",
  "timeframe": "1D",
  "current_price": 450.0,
  "bars": [
    {
      "timestamp": "2024-01-01T00:00:00",
      "open": 400.0,
      "high": 410.0,
      "low": 395.0,
      "close": 405.0,
      "volume": 1000000
    },
    {
      "timestamp": "2024-01-02T00:00:00",
      "open": 405.0,
      "high": 415.0,
      "low": 400.0,
      "close": 410.0,
      "volume": 1200000
    }
  ]
}
```

**Required Fields:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `symbol` | string | Trading symbol (max 10 chars) | `"QQQ"` |
| `timeframe` | string | One of: `1D`, `1W`, `1M` | `"1D"` |
| `current_price` | number | Current market price (must be > 0) | `450.0` |
| `bars` | array | OHLCV bars (minimum 3 bars) | See below |

**Bar Object Fields:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `timestamp` | string or number | ISO 8601 datetime OR Unix timestamp | `"2024-01-01T00:00:00"` or `1704067200` |
| `open` | number | Opening price | `400.0` |
| `high` | number | High price | `410.0` |
| `low` | number | Low price | `395.0` |
| `close` | number | Closing price | `405.0` |
| `volume` | integer | Trading volume | `1000000` |

**Validation Rules:**

- `high >= low` (high must be >= low)
- `close` must be between `low` and `high`
- Bars must be sorted chronologically (oldest first)
- Minimum 3 bars required

#### Success Response (200 OK)

```json
{
  "success": true,
  "report": {
    "symbol": "QQQ",
    "timeframe": "1D",
    "generated_at": "2024-01-15T12:34:56.789Z",
    
    "swings": {
      "success": true,
      "symbol": "QQQ",
      "timeframe": "1D",
      "total_bars_analyzed": 100,
      "total_swings_found": 12,
      "minor_swings": 4,
      "intermediate_swings": 6,
      "major_swings": 2
    },
    
    "structure": {
      "success": true,
      "symbol": "QQQ",
      "timeframe": "1D",
      "structure_state": "BULLISH",
      "is_bullish": true,
      "is_bearish": false,
      "is_transitioning": false
    },
    
    "fibonacci": {
      "success": true,
      "symbol": "QQQ",
      "timeframe": "1D",
      "total_levels": 24,
      "retracement_count": 8,
      "extension_count": 8,
      "projection_count": 8
    },
    
    "elliott": {
      "success": true,
      "symbol": "QQQ",
      "timeframe": "1D",
      "impulse_candidates": 3,
      "correction_candidates": 2,
      "has_primary_count": true,
      "current_phase": "WAVE_3"
    },
    
    "confluence": {
      "success": true,
      "symbol": "QQQ",
      "timeframe": "1D",
      "total_zones": 8,
      "high_confluence_zones": 2,
      "medium_confluence_zones": 3,
      "low_confluence_zones": 3
    },
    
    "targets": {
      "success": true,
      "symbol": "QQQ",
      "timeframe": "1D",
      "total_targets": 12,
      "high_confidence_targets": 3,
      "medium_confidence_targets": 6
    },
    
    "all_engines_successful": true,
    "errors": [],
    
    "algorithm_versions": {
      "SWING": "SWING_V1",
      "STRUCTURE": "STRUCTURE_V1",
      "FIBONACCI": "FIB_V1",
      "ELLIOTT": "ELLIOTT_V1",
      "CONFLUENCE": "CONFLUENCE_V1",
      "TARGET": "TARGET_V1"
    }
  },
  "timestamp": "2024-01-15T12:34:56.789Z"
}
```

#### Error Responses

**400 Bad Request** — Invalid input

```json
{
  "success": false,
  "error": "Invalid timeframe: 1H. Must be 1D, 1W, or 1M",
  "timestamp": "2024-01-15T12:34:56.789Z"
}
```

**422 Unprocessable Entity** — Invalid bar data

```json
{
  "success": false,
  "error": "Invalid bar at index 5: high (410.0) < low (415.0)",
  "timestamp": "2024-01-15T12:34:56.789Z"
}
```

**500 Internal Server Error** — Server-side error

```json
{
  "success": false,
  "error": "Internal server error: description",
  "timestamp": "2024-01-15T12:34:56.789Z"
}
```

---

## Request/Response Schema

### Supported Symbols

Any valid trading symbol (stock, crypto, forex):
- Stocks: `AAPL`, `MSFT`, `QQQ`, `SPY`
- Crypto: `BTCUSD`, `ETHUSD`
- Forex: `EURUSD`, `GBPUSD`

### Supported Timeframes

| Timeframe | Meaning | Min Bars for Analysis |
|-----------|---------|----------------------|
| `1D` | Daily | 30 bars (≈1 month) |
| `1W` | Weekly | 30 bars (≈7 months) |
| `1M` | Monthly | 30 bars (≈2.5 years) |

### Timestamp Formats

Both ISO 8601 and Unix timestamp are supported:

```json
// ISO 8601 (recommended)
"timestamp": "2024-01-15T12:34:56Z"

// Unix timestamp (seconds)
"timestamp": 1705336496
```

---

## Integration Examples

### Example 1: n8n Webhook Integration

**n8n Workflow Setup:**

1. Create new workflow
2. Add "Webhook" trigger node
3. Configure trigger:
   - Method: POST
   - URL: `http://api.socrates.local/analyze`
4. Add "HTTP Request" node
   - Method: POST
   - URL: `http://api.socrates.local/analyze`
   - Body: Use JSON from incoming request
5. Add "Set" node to extract targets from response
6. Add database node to save results

**Sample n8n JSON:**

```json
{
  "nodes": [
    {
      "name": "Analyze QQQ",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [300, 200],
      "parameters": {
        "method": "POST",
        "url": "http://api.socrates.local/analyze",
        "sendBody": true,
        "bodyParametersJson": "={\n  \"symbol\": \"QQQ\",\n  \"timeframe\": \"1D\",\n  \"current_price\": 450.0,\n  \"bars\": {{$json.bars}}\n}"
      }
    }
  ]
}
```

### Example 2: Python Client (Hostinger Cron Job)

```python
#!/usr/bin/env python3
"""
SOCrates Phase 1 API Client for Hostinger Cron Jobs
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

class SocratesClient:
    """Client for Phase 1 API."""
    
    def __init__(self, api_url: str = "http://api.socrates.local"):
        self.api_url = api_url
    
    def health_check(self) -> bool:
        """Verify API is running."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        bars: List[Dict[str, Any]],
        current_price: float,
    ) -> Dict[str, Any]:
        """
        Run complete Phase 1 analysis.
        
        Args:
            symbol: Trading symbol (e.g., "QQQ")
            timeframe: Timeframe (1D, 1W, 1M)
            bars: List of OHLCV bars
            current_price: Current market price
        
        Returns:
            Full analysis report
        """
        payload = {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": current_price,
            "bars": bars,
        }
        
        response = requests.post(
            f"{self.api_url}/analyze",
            json=payload,
            timeout=30,
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API error: {response.status_code} - {response.text}")


# Example usage in Hostinger cron job
if __name__ == "__main__":
    client = SocratesClient("http://api.socrates.local")
    
    # Verify API is available
    if not client.health_check():
        print("API is unavailable!")
        exit(1)
    
    # Fetch market data (pseudo-code; use your data source)
    bars = fetch_bars_from_data_provider("QQQ", "1D", 100)
    current_price = get_current_price("QQQ")
    
    # Run analysis
    report = client.analyze(
        symbol="QQQ",
        timeframe="1D",
        bars=bars,
        current_price=current_price,
    )
    
    # Save to database or send to dashboard
    if report["success"]:
        targets = report["report"]["targets"]["targets"]
        print(f"Found {len(targets)} targets")
        # Save to Supabase or your database
    else:
        print(f"Analysis failed: {report['error']}")
```

### Example 3: cURL from Command Line

```bash
# Analyze QQQ with sample data
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "QQQ",
    "timeframe": "1D",
    "current_price": 450.0,
    "bars": [
      {"timestamp": "2024-01-01T00:00:00", "open": 400.0, "high": 410.0, "low": 395.0, "close": 405.0, "volume": 1000000},
      {"timestamp": "2024-01-02T00:00:00", "open": 405.0, "high": 415.0, "low": 400.0, "close": 410.0, "volume": 1200000},
      {"timestamp": "2024-01-03T00:00:00", "open": 410.0, "high": 420.0, "low": 405.0, "close": 415.0, "volume": 1100000}
    ]
  }' | jq '.report.targets'
```

---

## Error Handling

### HTTP Status Codes

| Status | Meaning | Example Error |
|--------|---------|----------------|
| 200 | Success | Analysis completed |
| 400 | Bad Request | Invalid symbol format |
| 422 | Unprocessable Entity | Bar data validation failed |
| 404 | Not Found | Invalid endpoint |
| 405 | Method Not Allowed | Used GET instead of POST |
| 500 | Server Error | Unexpected exception |

### Client-Side Error Handling

Always check `success` field first:

```python
response = requests.post("http://api.socrates.local/analyze", json=payload)
data = response.json()

if data["success"]:
    # Process report
    report = data["report"]
    print(f"Found {report['targets']['total_targets']} targets")
else:
    # Handle error
    print(f"Analysis failed: {data['error']}")
    # Retry logic, fallback, etc.
```

### Common Errors

**"Invalid timeframe"**
```
Solution: Use one of: 1D, 1W, 1M
```

**"Insufficient bars"**
```
Solution: Provide at least 3 bars, ideally 30+ for meaningful analysis
```

**"Invalid bar at index N"**
```
Solution: Verify high >= low and close is between high and low
```

---

## Performance & Limits

### Response Times

| Scenario | Typical Time |
|----------|--------------|
| 30 bars (1 month daily) | 50-100ms |
| 100 bars (5+ months) | 100-200ms |
| 500 bars (2+ years) | 300-500ms |

### Rate Limits

For production deployments, recommend:
- **Per IP:** 1000 requests/hour
- **Per API key:** 10,000 requests/day
- **Concurrent:** 5 simultaneous requests

### Timeout Handling

Recommended timeout settings:
- API request: 30 seconds
- Health check: 5 seconds
- Batch processing: 60 seconds per symbol

---

## Deployment

### Environment Setup

Set these environment variables before deployment:

```bash
# Flask configuration
FLASK_ENV=production
FLASK_DEBUG=False

# API port
PORT=5000

# Optional: Enable CORS for specific origins
CORS_ORIGINS=["https://dashboard.domain.com", "https://n8n.domain.com"]
```

### Production Deployment Checklist

- [ ] Use production WSGI server (Gunicorn, uWSGI) instead of Flask dev server
- [ ] Enable HTTPS/SSL
- [ ] Configure rate limiting
- [ ] Set up monitoring and logging
- [ ] Enable CORS for your dashboard domain
- [ ] Configure database backups (if using Supabase)
- [ ] Set up health check monitoring

### Deployment Example (Gunicorn)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 api:app
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY socrates_data/ ./socrates_data/
COPY api.py .

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "api:app"]
```

```bash
docker build -t socrates-phase1 .
docker run -p 5000:5000 socrates-phase1
```

---

## FAQ

**Q: Can I run multiple analyses concurrently?**
A: Yes, the API is thread-safe. Gunicorn with 4-8 workers recommended.

**Q: What happens if one engine fails?**
A: The report returns with `all_engines_successful: false` and errors list populated. Inspect the individual engine's `success` field.

**Q: Can I use different data sources (crypto, forex)?**
A: Yes, any symbol and OHLCV data is supported. Algorithm is market-agnostic.

**Q: How do I persist reports to a database?**
A: Use the Supabase schema provided (`supabase_migrations.sql`). After receiving a report, INSERT into the relevant tables.

**Q: Is the API deterministic?**
A: Yes, identical input always produces identical output. Great for backtesting and validation.

---

## Support

For issues or questions:
1. Check the `/health` endpoint first
2. Verify bar data format in error message
3. Check logs for detailed exception traceback
4. Refer to GitHub repository for known issues

---

**API Version:** Phase 1 v1.0  
**Last Updated:** January 2024  
**Algorithm Versions:** SWING_V1, STRUCTURE_V1, FIB_V1, ELLIOTT_V1, CONFLUENCE_V1, TARGET_V1
