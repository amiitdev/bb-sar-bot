"""
Backtest — run BB + Pure SAR strategy with Hybrid Exit on historical CSV data.

Usage:
    python backtest.py data/nifty_5m.csv
    python backtest.py data/nifty_15m.csv
"""
import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path

from config import (
    BB_PERIOD, BB_STD_MULT, MIN_BANDWIDTH_PCT, MIN_SLOPE,
    SLOPE_LOOKBACK, ATR_PERIOD, ATR_BUFFER_MULT,
    BE_TRIGGER_R, BE_OFFSET_R, TRAIL_TRIGGER_R, TRAIL_DIST_R,
    SYMBOLS, ACTIVE_SYMBOL,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_backtest(df: pd.DataFrame, lot_size: int = 50) -> dict:
    """
    Run backtest on historical OHLCV data with hybrid exit logic.
    Returns trade summary dict.
    """
    from bb_sar_engine import calculate_bb, calculate_atr, bandwidth_pct, basis_slope, PositionTracker

    data = calculate_bb(df)
    data["atr"] = calculate_atr(data)
    data["bw_pct"] = data.apply(bandwidth_pct, axis=1)

    # Calculate slope for each row
    slopes = [np.nan] * len(data)
    for i in range(SLOPE_LOOKBACK + 1, len(data)):
        slopes[i] = abs(data["basis"].iloc[i] - data["basis"].iloc[i - SLOPE_LOOKBACK - 1])
    data["slope"] = slopes

    trades = []
    tracker = PositionTracker()

    for i in range(BB_PERIOD + SLOPE_LOOKBACK + 1, len(data)):
        curr = data.iloc[i]
        prev = data.iloc[i - 1]

        # Update existing position with current bar
        if tracker.position != 0:
            exit_signal = tracker.update(curr["high"], curr["low"], curr["close"])
            if exit_signal == "EXIT":
                pnl = tracker.get_unrealized_pnl(curr["close"])
                trades.append({
                    "entry_idx": tracker._entry_idx,
                    "exit_idx": i,
                    "action": "LONG" if tracker.position == -1 else "SHORT",  # was long/short before exit
                    "entry": tracker.entry_price,
                    "exit": curr["close"],
                    "pnl": round(pnl * lot_size, 2),
                    "exit_type": "STOP",
                })
                tracker = PositionTracker()
                continue

        # Check for new entry signal
        bw = curr["bw_pct"]
        sl = curr["slope"]
        atr = curr["atr"]

        if pd.isna(bw) or pd.isna(sl) or pd.isna(atr):
            continue
        if bw < MIN_BANDWIDTH_PCT or sl < MIN_SLOPE:
            continue

        buy_cross = (curr["close"] > curr["lower"]) and (prev["close"] <= prev["lower"])
        sell_cross = (curr["close"] < curr["upper"]) and (prev["close"] >= prev["upper"])

        if buy_cross and tracker.position != 1:
            # Close short if exists
            if tracker.position == -1:
                pnl = tracker.get_unrealized_pnl(curr["close"])
                trades.append({
                    "entry_idx": tracker._entry_idx,
                    "exit_idx": i,
                    "action": "SHORT",
                    "entry": tracker.entry_price,
                    "exit": curr["close"],
                    "pnl": round(pnl * lot_size, 2),
                    "exit_type": "REVERSE",
                })
                tracker = PositionTracker()

            # Find recent swing low for SL
            lookback = min(i, 20)
            swing_low = data["low"].iloc[i-lookback:i].min()

            tracker._entry_idx = i
            tracker.open_position(1, curr["close"], atr, swing_low=swing_low)

        elif sell_cross and tracker.position != -1:
            # Close long if exists
            if tracker.position == 1:
                pnl = tracker.get_unrealized_pnl(curr["close"])
                trades.append({
                    "entry_idx": tracker._entry_idx,
                    "exit_idx": i,
                    "action": "LONG",
                    "entry": tracker.entry_price,
                    "exit": curr["close"],
                    "pnl": round(pnl * lot_size, 2),
                    "exit_type": "REVERSE",
                })
                tracker = PositionTracker()

            # Find recent swing high for SL
            lookback = min(i, 20)
            swing_high = data["high"].iloc[i-lookback:i].max()

            tracker._entry_idx = i
            tracker.open_position(-1, curr["close"], atr, swing_high=swing_high)

    # Close final position at last price
    if tracker.position != 0:
        last_price = data["close"].iloc[-1]
        pnl = tracker.get_unrealized_pnl(last_price)
        trades.append({
            "entry_idx": tracker._entry_idx,
            "exit_idx": len(data) - 1,
            "action": "LONG" if tracker.position == 1 else "SHORT",
            "entry": tracker.entry_price,
            "exit": last_price,
            "pnl": round(pnl * lot_size, 2),
            "exit_type": "EOD",
        })

    return summarize(trades, data)


def summarize(trades: list, data: pd.DataFrame) -> dict:
    """Summarize backtest results."""
    if not trades:
        return {"total_trades": 0, "message": "No trades generated."}

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_pnl = sum(pnls)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    win_rate = len(wins) / len(pnls) * 100 if pnls else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0

    # Max drawdown
    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    drawdown = equity - peak
    max_dd = drawdown.min()

    # Exit type breakdown
    exit_types = {}
    for t in trades:
        et = t.get("exit_type", "UNKNOWN")
        exit_types.setdefault(et, {"count": 0, "pnl": 0})
        exit_types[et]["count"] += 1
        exit_types[et]["pnl"] += t["pnl"]

    # Year breakdown
    years = {}
    for t in trades:
        idx = t["entry_idx"]
        if idx < len(data):
            yr = str(data["datetime"].iloc[idx].year)
            years.setdefault(yr, {"trades": 0, "pnl": 0, "wins": 0})
            years[yr]["trades"] += 1
            years[yr]["pnl"] += t["pnl"]
            if t["pnl"] > 0:
                years[yr]["wins"] += 1

    return {
        "total_trades": len(pnls),
        "win_rate": round(win_rate, 1),
        "net_pnl": round(total_pnl, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(-gross_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "max_drawdown": round(max_dd, 2),
        "exit_types": {k: {"count": v["count"], "pnl": round(v["pnl"], 2)} for k, v in exit_types.items()},
        "years": {y: {
            "trades": v["trades"],
            "win_rate": round(v["wins"] / v["trades"] * 100, 1) if v["trades"] else 0,
            "net_pnl": round(v["pnl"], 2),
        } for y, v in sorted(years.items())},
    }


def print_report(result: dict, symbol: str):
    """Pretty-print backtest report."""
    print("\n" + "=" * 60)
    print(f"  BACKTEST REPORT — {symbol} BB + Pure SAR + Hybrid Exit")
    print("=" * 60)
    if result["total_trades"] == 0:
        print("  No trades generated.")
        print("=" * 60)
        return

    print(f"  Total Trades:      {result['total_trades']}")
    print(f"  Win Rate:          {result['win_rate']}%")
    print(f"  Net P&L:           {result['net_pnl']:+.2f} pts")
    print(f"  Gross Profit:      {result['gross_profit']:+.2f}")
    print(f"  Gross Loss:        {result['gross_loss']:+.2f}")
    print(f"  Profit Factor:     {result['profit_factor']}")
    print(f"  Avg Win / Loss:    {result['avg_win']:+.2f} / {result['avg_loss']:+.2f}")
    print(f"  Max Drawdown:      {result['max_drawdown']:+.2f}")

    print("\n  Exit Type Breakdown:")
    print(f"  {'Type':<12} {'Count':>8} {'P&L':>12}")
    print("  " + "-" * 35)
    for et, v in result["exit_types"].items():
        print(f"  {et:<12} {v['count']:>8} {v['pnl']:>+12.2f}")

    print("\n  Year-by-Year:")
    print(f"  {'Year':<8} {'Trades':>8} {'WinRate':>10} {'Net P&L':>12}")
    print("  " + "-" * 40)
    for yr, v in result["years"].items():
        print(f"  {yr:<8} {v['trades']:>8} {v['win_rate']:>9.1f}% {v['net_pnl']:>+12.2f}")

    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backtest.py <csv_or_json_file>")
        print("Example: python backtest.py data/nifty_5m.csv")
        sys.exit(1)

    file_path = sys.argv[1]
    if file_path.endswith(".json"):
        df = pd.read_json(file_path)
    else:
        df = pd.read_csv(file_path)

    # Normalize column names
    df.columns = [c.lower().strip() for c in df.columns]
    if "timestamp" in df.columns and "datetime" not in df.columns:
        if df["timestamp"].dtype in ["int64", "float64"]:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        else:
            df["datetime"] = pd.to_datetime(df["timestamp"])
    elif "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

    lot = SYMBOLS[ACTIVE_SYMBOL]["lot_size"]
    result = run_backtest(df, lot_size=lot)
    print_report(result, ACTIVE_SYMBOL)
