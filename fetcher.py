"""
Candle fetcher — Dhan API for live 5-min candles.

During market hours, fetches the latest candles from Dhan.
During off-hours, loads from local CSV cache (for backtesting).
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from config import DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN, ACTIVE_SYMBOL, SYMBOLS, DATA_DIR

logger = logging.getLogger(__name__)


def fetch_latest_candles_dhan(count: int = 50) -> pd.DataFrame:
    """Fetch latest intraday 5-min candles from Dhan API."""
    if not DHAN_CLIENT_ID or not DHAN_ACCESS_TOKEN:
        logger.warning("No Dhan credentials — cannot fetch live candles.")
        return pd.DataFrame()

    try:
        from dhanhq import DhanContext, dhanhq
        context = DhanContext(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
        dhan = dhanhq(context)
        sym = SYMBOLS[ACTIVE_SYMBOL]

        resp = dhan.intraday_minute_data(
            security_id=sym["security_id"],
            exchange_segment=getattr(dhanhq, sym["exchange"], dhanhq.INDEX),
            instrument_type="INDEX",
            interval="5",
        )

        if resp.get("status") == "success":
            data = resp["data"]
            df = pd.DataFrame({
                "datetime": pd.to_datetime(data["start_Time"], unit="s"),
                "open": data["open"],
                "high": data["high"],
                "low": data["low"],
                "close": data["close"],
                "volume": data["volume"],
            })
            df = df.sort_values("datetime").reset_index(drop=True)
            logger.info(f"Fetched {len(df)} candles from Dhan.")
            return df.tail(count)
        else:
            logger.error(f"Dhan API error: {resp}")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Dhan fetch failed: {e}")
        return pd.DataFrame()


def load_cached_candles(filename: str) -> pd.DataFrame:
    """Load candles from a local CSV or JSON file (for backtesting / off-hours)."""
    import glob as glob_mod
    # Search in data/ dir and also ~/upstox-scraper/data/
    search_dirs = [DATA_DIR, Path.home() / "upstox-scraper" / "data"]
    df = pd.DataFrame()

    for d in search_dirs:
        # Handle glob patterns
        if "*" in filename:
            matches = sorted(glob_mod.glob(str(d / filename)))
            if matches:
                path = Path(matches[-1])  # Take the latest match
            else:
                continue
        else:
            path = d / filename

        if path.exists():
            if path.suffix == ".json":
                df = pd.read_json(path)
            else:
                df = pd.read_csv(path)
            break

    if df.empty:
        logger.error(f"Cache file not found: {filename}")
        return df

    # Normalize columns
    df.columns = [c.lower().strip() for c in df.columns]
    if "datetime" not in df.columns and "timestamp" in df.columns:
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
    elif "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])

    df = df.sort_values("datetime").reset_index(drop=True)
    logger.info(f"Loaded {len(df)} cached candles from {path.name}")
    return df


def fetch_live_yahoo(symbol: str = "^NSEI", count: int = 100) -> pd.DataFrame:
    """Fetch live candles from Yahoo Finance (free, no API key needed)."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="5d", interval="5m")
        if df.empty:
            return pd.DataFrame()

        df = df.reset_index()
        df.columns = [c.lower().strip() for c in df.columns]
        df.rename(columns={"date": "datetime"}, inplace=True)
        df = df[["datetime", "open", "high", "low", "close", "volume"]]
        df = df.sort_values("datetime").reset_index(drop=True)
        logger.info(f"Fetched {len(df)} live candles from Yahoo Finance.")
        return df.tail(count)
    except Exception as e:
        logger.error(f"Yahoo Finance fetch failed: {e}")
        return pd.DataFrame()


def get_candles() -> pd.DataFrame:
    """Get candles — live from Yahoo (free), fallback to Dhan, then cached."""
    # Try Yahoo Finance first (free, no auth needed)
    df = fetch_live_yahoo("^NSEI", count=100)
    if not df.empty:
        return df

    # Try Dhan API
    df = fetch_latest_candles_dhan(count=100)
    if not df.empty:
        return df

    # Fallback to cached data
    logger.info("Live fetch empty — trying cache files.")
    for fname in ["upstox_nifty_5m*.json", "upstox_nifty_15m*.json",
                   "nifty_5m.csv", "nifty_15m.csv", "nifty_daily.csv"]:
        df = load_cached_candles(fname)
        if not df.empty:
            return df
    return df
