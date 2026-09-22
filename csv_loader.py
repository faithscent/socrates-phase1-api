"""
CSV Data Loader — Load OHLCV bars from CSV into Supabase on API startup.

Expected CSV format:
    timestamp,open,high,low,close,volume,symbol,timeframe
    2024-01-01T00:00:00,400.0,410.0,395.0,405.0,1000000,QQQ,1D
    2024-01-02T00:00:00,405.0,415.0,400.0,410.0,1200000,QQQ,1D

Usage:
    from csv_loader import load_csv_data
    load_csv_data('data.csv', supabase_client)
"""

import os
import csv
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def load_csv_data(csv_file_path: str, supabase_client=None) -> dict:
    """
    Load OHLCV data from CSV file.

    Args:
        csv_file_path: Path to CSV file
        supabase_client: Optional Supabase client for persistence

    Returns:
        Dict with loaded count and any errors
    """

    if not os.path.exists(csv_file_path):
        logger.warning(f"CSV file not found: {csv_file_path}")
        return {"success": False, "error": f"File not found: {csv_file_path}", "loaded": 0}

    try:
        loaded_count = 0
        error_count = 0
        rows = []

        with open(csv_file_path, 'r') as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader):
                try:
                    # Parse timestamp
                    timestamp_str = row['timestamp']
                    if 'T' in timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    else:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d')

                    # Extract data
                    bar_data = {
                        "timestamp": timestamp.isoformat(),
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": int(row['volume']),
                        "symbol": row.get('symbol', '').upper(),
                        "timeframe": row.get('timeframe', '1D').upper(),
                    }

                    # Validate OHLCV
                    if bar_data['high'] < bar_data['low']:
                        raise ValueError(f"high ({bar_data['high']}) < low ({bar_data['low']})")
                    if bar_data['close'] < bar_data['low'] or bar_data['close'] > bar_data['high']:
                        raise ValueError(f"close outside high/low range")

                    rows.append(bar_data)
                    loaded_count += 1

                except Exception as e:
                    logger.error(f"Error parsing row {i}: {str(e)}")
                    error_count += 1
                    continue

        # Optionally persist to Supabase
        if supabase_client and loaded_count > 0:
            try:
                # Note: This is a placeholder. Adjust based on your Supabase table structure
                logger.info(f"Would insert {loaded_count} rows into Supabase")
                # supabase_client.table('ohlcv_data').insert(rows).execute()
            except Exception as e:
                logger.error(f"Error persisting to Supabase: {str(e)}")

        result = {
            "success": True,
            "loaded": loaded_count,
            "errors": error_count,
            "message": f"Loaded {loaded_count} bars from {csv_file_path}"
        }

        logger.info(result["message"])
        return result

    except Exception as e:
        logger.error(f"CSV loading failed: {str(e)}")
        return {"success": False, "error": str(e), "loaded": 0}


def get_bars_from_csv(csv_file_path: str, symbol: str, timeframe: str, limit: int = 100) -> list:
    """
    Retrieve OHLCV bars from CSV for a specific symbol/timeframe.

    Args:
        csv_file_path: Path to CSV file
        symbol: Trading symbol (e.g., 'QQQ')
        timeframe: Timeframe (e.g., '1D')
        limit: Maximum bars to return (most recent first)

    Returns:
        List of OHLCV bars matching criteria
    """

    if not os.path.exists(csv_file_path):
        logger.warning(f"CSV file not found: {csv_file_path}")
        return []

    try:
        bars = []

        with open(csv_file_path, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                if (row.get('symbol', '').upper() == symbol.upper() and
                    row.get('timeframe', '').upper() == timeframe.upper()):

                    timestamp_str = row['timestamp']
                    if 'T' in timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    else:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d')

                    bar = {
                        "timestamp": timestamp,
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": int(row['volume']),
                    }
                    bars.append(bar)

        # Return most recent bars first (reverse order) and limit
        return sorted(bars, key=lambda x: x['timestamp'], reverse=True)[:limit]

    except Exception as e:
        logger.error(f"Error reading bars from CSV: {str(e)}")
        return []
