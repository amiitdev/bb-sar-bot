"""
FastAPI backend for BB + Pure SAR Bot dashboard.

Endpoints:
  GET  /api/status        — bot status, position, P&L
  GET  /api/signals       — recent signals
  GET  /api/trades        — trade history
  GET  /api/backtest      — backtest results
  POST /api/start         — start bot (paper/live)
  POST /api/stop          — stop bot
  POST /api/credentials   — save Dhan credentials
"""
import csv
import json
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import (
    MODE, ACTIVE_SYMBOL, SYMBOLS, TRADE_LOG,
    DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN,
)
from bb_sar_engine import evaluate_signal, get_bb_snapshot, PositionTracker
from broker import get_broker
from fetcher import get_candles

logger = logging.getLogger(__name__)

app = FastAPI(title="BB + Pure SAR Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Global state
# ============================================================
bot_thread: Optional[threading.Thread] = None
bot_running = False
broker = None
signals_log = []
position_tracker = PositionTracker()


class CredentialsRequest(BaseModel):
    client_id: str
    access_token: str


class StartRequest(BaseModel):
    mode: str = "paper"  # "paper" or "live"
    symbol: str = "NIFTY"


# ============================================================
# API Endpoints
# ============================================================

@app.get("/api/status")
def get_status():
    """Get bot status, current position, and P&L."""
    trade_count = 0
    total_pnl = 0.0
    win_count = 0

    if TRADE_LOG.exists():
        with open(TRADE_LOG) as f:
            reader = csv.DictReader(f)
            for row in reader:
                trade_count += 1
                pnl = float(row.get("pnl", 0))
                total_pnl += pnl
                if pnl > 0:
                    win_count += 1

    return {
        "running": bot_running,
        "mode": MODE,
        "symbol": ACTIVE_SYMBOL,
        "lot_size": SYMBOLS[ACTIVE_SYMBOL]["lot_size"],
        "position": position_tracker.position,
        "entry_price": position_tracker.entry_price,
        "stop_loss": position_tracker.stop_loss,
        "peak_price": position_tracker.peak_price,
        "total_trades": trade_count,
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_count / trade_count * 100, 1) if trade_count > 0 else 0,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/signals")
def get_signals():
    """Get recent signals from live evaluation."""
    df = get_candles()
    if df.empty:
        return {"signals": [], "bb_snapshot": {}}

    snap = get_bb_snapshot(df)
    signal = evaluate_signal(df)

    return {
        "current_signal": signal,
        "bb_snapshot": snap,
        "recent_signals": signals_log[-20:],
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/trades")
def get_trades():
    """Get trade history from CSV."""
    trades = []
    if TRADE_LOG.exists():
        with open(TRADE_LOG) as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append(row)
    return {"trades": trades[-50:]}  # Last 50 trades


@app.get("/api/backtest")
def run_backtest():
    """Run backtest on cached data and return results."""
    from backtest import run_backtest as backtest_run

    # Try to load cached data
    data_files = [
        "upstox_nifty_5m_20260903.json",
        "upstox_nifty_15m_20260903.json",
    ]

    for fname in data_files:
        path = Path.home() / "upstox-scraper" / "data" / fname
        if path.exists():
            import pandas as pd
            df = pd.read_json(path)
            df.columns = [c.lower().strip() for c in df.columns]
            if "timestamp" in df.columns and "datetime" not in df.columns:
                if df["timestamp"].dtype in ["int64", "float64"]:
                    df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
                else:
                    df["datetime"] = pd.to_datetime(df["timestamp"])
            elif "datetime" in df.columns:
                df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

            lot = SYMBOLS[ACTIVE_SYMBOL]["lot_size"]
            result = backtest_run(df, lot_size=lot)
            result["data_file"] = fname
            result["candles"] = len(df)
            return result

    return {"error": "No data files found"}


@app.post("/api/credentials")
def save_credentials(req: CredentialsRequest):
    """Save Dhan credentials to env file."""
    env_path = Path(__file__).parent / ".env"
    with open(env_path, "w") as f:
        f.write(f"DHAN_CLIENT_ID={req.client_id}\n")
        f.write(f"DHAN_ACCESS_TOKEN={req.access_token}\n")

    import os
    os.environ["DHAN_CLIENT_ID"] = req.client_id
    os.environ["DHAN_ACCESS_TOKEN"] = req.access_token

    return {"status": "ok", "message": "Credentials saved"}


@app.post("/api/start")
def start_bot(req: StartRequest):
    """Start the trading bot in a background thread."""
    global bot_thread, bot_running, broker

    if bot_running:
        return {"status": "already_running"}

    bot_running = True
    broker = get_broker()

    def run():
        import time
        from config import MARKET_OPEN, MARKET_CLOSE, SQUARE_OFF, SIGNAL_START, SIGNAL_END

        while bot_running:
            now = datetime.now()
            current = now.strftime("%H:%M")

            if MARKET_OPEN <= current <= MARKET_CLOSE:
                if current >= SQUARE_OFF and position_tracker.position != 0:
                    # Square off
                    action = "SELL" if position_tracker.position == 1 else "BUY"
                    price = 0
                    broker.place_order(action, SYMBOLS[ACTIVE_SYMBOL]["lot_size"], price, "SQUARE_OFF")
                    position_tracker.position = 0
                elif SIGNAL_START <= current <= SIGNAL_END:
                    df = get_candles()
                    if not df.empty:
                        signal = evaluate_signal(df)
                        snap = get_bb_snapshot(df)
                        if signal:
                            signals_log.append({
                                "time": now.isoformat(),
                                "signal": signal,
                                "price": df["close"].iloc[-1],
                                "bb": snap,
                            })
                            if signal == "BUY" and position_tracker.position != 1:
                                qty = SYMBOLS[ACTIVE_SYMBOL]["lot_size"] * 2 if position_tracker.position == -1 else SYMBOLS[ACTIVE_SYMBOL]["lot_size"]
                                broker.place_order("BUY", qty, df["close"].iloc[-1], "SIGNAL")
                            elif signal == "SELL" and position_tracker.position != -1:
                                qty = SYMBOLS[ACTIVE_SYMBOL]["lot_size"] * 2 if position_tracker.position == 1 else SYMBOLS[ACTIVE_SYMBOL]["lot_size"]
                                broker.place_order("SELL", qty, df["close"].iloc[-1], "SIGNAL")

            time.sleep(60)

    bot_thread = threading.Thread(target=run, daemon=True)
    bot_thread.start()
    return {"status": "started", "mode": req.mode, "symbol": req.symbol}


@app.post("/api/stop")
def stop_bot():
    """Stop the trading bot."""
    global bot_running
    bot_running = False
    return {"status": "stopped"}


# ============================================================
# Serve React frontend (production build)
# ============================================================
frontend_build = Path(__file__).parent / "frontend" / "dist"

if frontend_build.exists() and frontend_build.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_build / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = frontend_build / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_build / "index.html")
