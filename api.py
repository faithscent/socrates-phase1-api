"""
SOCrates V2 Phase 1 — REST API Server

Exposes the unified technical intelligence pipeline as HTTP endpoints.
Callable from n8n workflows, Hostinger cron jobs, or any HTTP client.

Usage:
    export FLASK_APP=api.py
    python -m flask run --host 0.0.0.0 --port 5000

Example POST to /analyze:
    curl -X POST http://localhost:5000/analyze \\
      -H "Content-Type: application/json" \\
      -d '{
        "symbol": "QQQ",
        "timeframe": "1D",
        "current_price": 450.0,
        "bars": [
          {"timestamp": "2024-01-01T00:00:00", "open": 400.0, "high": 410.0, "low": 395.0, "close": 405.0, "volume": 1000000},
          ...
        ]
      }'
"""

from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, Any, List

from socrates_data.technical.pipeline import analyze_symbol, report_to_dict
from socrates_data.technical.types import OHLCV

app = Flask(__name__)
CORS(app)  # Enable CORS for n8n and web dashboard


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint.

    Returns:
        JSON with status and algorithm versions
    """
    return jsonify({
        "status": "healthy",
        "service": "SOCrates V2 Phase 1",
        "timestamp": datetime.utcnow().isoformat(),
        "engines": [
            "SWING_V1",
            "STRUCTURE_V1",
            "FIB_V1",
            "ELLIOTT_V1",
            "CONFLUENCE_V1",
            "TARGET_V1",
        ],
    }), 200


# ============================================================================
# ANALYZE ENDPOINT
# ============================================================================

@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Run complete Phase 1 technical analysis.

    Request JSON schema:
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
            ...
        ]
    }

    Response:
        {
            "success": true,
            "report": { ... unified technical intelligence ... },
            "timestamp": "2024-01-01T12:00:00"
        }

    Error Response (400/422):
        {
            "success": false,
            "error": "Description of error",
            "timestamp": "2024-01-01T12:00:00"
        }
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "Request body must be JSON",
                "timestamp": datetime.utcnow().isoformat(),
            }), 400

        # Validate required fields
        required_fields = ["symbol", "timeframe", "current_price", "bars"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing)}",
                "timestamp": datetime.utcnow().isoformat(),
            }), 400

        # Extract and validate inputs
        symbol: str = data["symbol"].upper()
        timeframe: str = data["timeframe"].upper()
        current_price: float = float(data["current_price"])

        # Validate symbol and timeframe
        if not symbol or len(symbol) > 10:
            return jsonify({
                "success": False,
                "error": f"Invalid symbol: {symbol}",
                "timestamp": datetime.utcnow().isoformat(),
            }), 400

        if timeframe not in ["1D", "1W", "1M"]:
            return jsonify({
                "success": False,
                "error": f"Invalid timeframe: {timeframe}. Must be 1D, 1W, or 1M",
                "timestamp": datetime.utcnow().isoformat(),
            }), 400

        if current_price <= 0:
            return jsonify({
                "success": False,
                "error": f"Invalid current_price: {current_price}. Must be > 0",
                "timestamp": datetime.utcnow().isoformat(),
            }), 400

        # Parse OHLCV bars
        bars_data: List[Any] = data.get("bars", [])
        if not bars_data:
            return jsonify({
                "success": False,
                "error": "bars array is empty",
                "timestamp": datetime.utcnow().isoformat(),
            }), 400

        bars: List[OHLCV] = []
        for i, bar_data in enumerate(bars_data):
            try:
                # Parse timestamp
                if isinstance(bar_data["timestamp"], str):
                    timestamp = datetime.fromisoformat(bar_data["timestamp"])
                else:
                    timestamp = datetime.fromtimestamp(bar_data["timestamp"])

                bar: OHLCV = {
                    "timestamp": timestamp,
                    "open": float(bar_data["open"]),
                    "high": float(bar_data["high"]),
                    "low": float(bar_data["low"]),
                    "close": float(bar_data["close"]),
                    "volume": int(bar_data["volume"]),
                }

                # Validate OHLCV
                if bar["high"] < bar["low"]:
                    raise ValueError(f"high ({bar['high']}) < low ({bar['low']})")
                if bar["high"] < bar["close"] or bar["low"] > bar["close"]:
                    raise ValueError(f"close ({bar['close']}) outside high/low range")

                bars.append(bar)
            except (KeyError, ValueError, TypeError) as e:
                return jsonify({
                    "success": False,
                    "error": f"Invalid bar at index {i}: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat(),
                }), 422

        # Run analysis
        report = analyze_symbol(
            bars=bars,
            symbol=symbol,
            timeframe=timeframe,
            current_price=current_price,
        )

        # Convert report to JSON-serializable dict
        report_dict = report_to_dict(report)

        return jsonify({
            "success": True,
            "report": report_dict,
            "timestamp": datetime.utcnow().isoformat(),
        }), 200

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
        }), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "timestamp": datetime.utcnow().isoformat(),
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors (method not allowed)."""
    return jsonify({
        "success": False,
        "error": "Method not allowed",
        "timestamp": datetime.utcnow().isoformat(),
    }), 405


if __name__ == "__main__":
    # Development server (don't use in production!)
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
