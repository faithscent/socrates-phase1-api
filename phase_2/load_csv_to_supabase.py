"""
Load OHLCV CSV data into Supabase.

Usage:
    python load_csv_to_supabase.py --url YOUR_SUPABASE_URL --key YOUR_ANON_KEY
"""

import csv
import sys
import argparse
from datetime import datetime

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ Please install: pip install supabase")
    sys.exit(1)

def load_csv_file(filepath):
    """Read CSV and return list of rows."""
    rows = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "timestamp": row['timestamp'],
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": int(row['volume']),
                "symbol": row['symbol'],
                "timeframe": row['timeframe'],
                "created_at": datetime.now().isoformat()
            })
    return rows

def load_to_supabase(supabase_url, supabase_key, csv_files):
    """Load CSV data into Supabase."""

    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        print(f"✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

    total_loaded = 0

    for csv_file in csv_files:
        try:
            print(f"\n📂 Reading {csv_file}...")
            rows = load_csv_file(csv_file)
            print(f"   Loaded {len(rows)} rows from CSV")

            # Insert in batches (Supabase limit ~1000 per request)
            batch_size = 500
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                response = supabase.table('ohlcv_bars').insert(batch).execute()
                print(f"   ✅ Inserted batch {i//batch_size + 1} ({len(batch)} rows)")
                total_loaded += len(batch)

        except Exception as e:
            print(f"   ❌ Error loading {csv_file}: {e}")
            return False

    print(f"\n✨ Phase 2b: CSV Loader Complete")
    print(f"📊 Total rows loaded: {total_loaded}")
    print(f"\n✅ Data ready in Supabase 'ohlcv_bars' table")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Load OHLCV CSV to Supabase')
    parser.add_argument('--url', required=True, help='Supabase URL')
    parser.add_argument('--key', required=True, help='Supabase Anon Key')
    parser.add_argument('--files', nargs='+', required=True, help='CSV files to load')

    args = parser.parse_args()

    print("🚀 Loading OHLCV data to Supabase...\n")
    success = load_to_supabase(args.url, args.key, args.files)

    sys.exit(0 if success else 1)
