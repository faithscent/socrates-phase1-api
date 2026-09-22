"""
Generate realistic OHLCV data for FXE, FXY, IBIT with panic cycle correlations.
Creates CSV files ready to load into Supabase.
"""

import csv
from datetime import datetime, timedelta
import random
import math

def generate_correlated_prices(symbol, days=90, base_price=100):
    """
    Generate realistic OHLCV bars with panic cycle patterns.

    FXE (Euro) - drops when panic (inverse correlation with risk)
    FXY (Yen) - rises when panic (safe haven)
    IBIT (Bitcoin) - drops when panic (risk-off)
    """

    bars = []
    current_price = base_price

    # Panic cycle: days 50-60 are panic periods
    for day in range(days):
        is_panic_period = 45 <= day <= 60

        # Generate correlation pattern
        if symbol == "FXE":  # Euro - drops in panic
            volatility = 0.015 if is_panic_period else 0.008
            trend = -0.003 if is_panic_period else 0.0005
        elif symbol == "FXY":  # Yen - rises in panic (safe haven)
            volatility = 0.012 if is_panic_period else 0.006
            trend = 0.004 if is_panic_period else 0.0003
        elif symbol == "IBIT":  # Bitcoin - drops in panic
            volatility = 0.025 if is_panic_period else 0.015
            trend = -0.005 if is_panic_period else 0.001
        else:
            volatility = 0.01
            trend = 0

        # Random walk with drift
        daily_return = trend + random.gauss(0, volatility)
        current_price *= (1 + daily_return)

        # Generate OHLCV for this day
        timestamp = datetime.now() - timedelta(days=days-day-1)

        open_price = current_price * (1 + random.uniform(-volatility, volatility))
        high_price = max(open_price, current_price) * (1 + abs(random.gauss(0, volatility/2)))
        low_price = min(open_price, current_price) * (1 - abs(random.gauss(0, volatility/2)))
        close_price = current_price
        volume = int(random.gauss(5000000, 1000000))

        bars.append({
            "timestamp": timestamp.strftime("%Y-%m-%dT00:00:00"),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": max(volume, 100000),
            "symbol": symbol,
            "timeframe": "1D"
        })

    return bars

def write_csv(filename, bars):
    """Write bars to CSV file."""
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol', 'timeframe'])
        writer.writeheader()
        for bar in bars:
            writer.writerow(bar)
    print(f"✅ Written {len(bars)} bars to {filename}")

# Generate data for each symbol
print("🔄 Generating OHLCV data for FXE, FXY, IBIT...")

fxe_bars = generate_correlated_prices("FXE", days=90, base_price=100.0)
write_csv("/mnt/user-data/outputs/phase2-build/FXE_1D.csv", fxe_bars)

fxy_bars = generate_correlated_prices("FXY", days=90, base_price=105.0)
write_csv("/mnt/user-data/outputs/phase2-build/FXY_1D.csv", fxy_bars)

ibit_bars = generate_correlated_prices("IBIT", days=90, base_price=45000.0)
write_csv("/mnt/user-data/outputs/phase2-build/IBIT_1D.csv", ibit_bars)

print("\n✨ Phase 2a: CSV Generator Complete")
print("\n📊 Files created:")
print("  - FXE_1D.csv (Euro - panic indicator)")
print("  - FXY_1D.csv (Yen - safe haven)")
print("  - IBIT_1D.csv (Bitcoin - risk-off)")
print("\nNext: Load these into Supabase")
