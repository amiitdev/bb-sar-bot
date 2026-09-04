"""
Main entry point — Bollinger Bands + Pure SAR live bot with Telegram alerts.

Runs a 5-minute loop:
  1. Fetch latest candles (Dhan API or cache)
  2. Evaluate BB + SAR signal
  3. Execute trade (paper or live)
  4. Send Telegram alerts
  5. Log everything

Usage:
    python run.py                # paper mode (default)
    BOT_MODE=live python run.py  # live Dhan mode
"""
import sys
import time
import logging
from datetime import datetime

from config import (
    MODE, ACTIVE_SYMBOL, SYMBOLS, MARKET_OPEN, MARKET_CLOSE,
    SIGNAL_START, SIGNAL_END, SQUARE_OFF,
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
)
from bb_sar_engine import evaluate_signal, get_bb_snapshot, PositionTracker
from broker import get_broker
from fetcher import get_candles
from telegram_notifier import (
    send_signal_alert, send_trade_alert, send_squareoff_alert,
    send_daily_summary, send_status_update, test_connection,
)

# ============================================================
# Logging setup
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/bot.log"),
    ],
)
logger = logging.getLogger(__name__)

# ============================================================
# Global state
# ============================================================
tracker = PositionTracker()
daily_pnl = 0.0
daily_trades = 0
daily_wins = 0


def is_market_hours() -> bool:
    now = datetime.now()
    current = now.strftime("%H:%M")
    return MARKET_OPEN <= current <= MARKET_CLOSE


def is_signal_window() -> bool:
    now = datetime.now()
    current = now.strftime("%H:%M")
    return SIGNAL_START <= current <= SIGNAL_END


def should_square_off() -> bool:
    now = datetime.now()
    return now.strftime("%H:%M") >= SQUARE_OFF


def run_once(broker, force: bool = False):
    global daily_pnl, daily_trades, daily_wins

    sym = SYMBOLS[ACTIVE_SYMBOL]
    now = datetime.now()
    current_time = now.strftime("%H:%M")

    # Square-off check
    if not force and should_square_off() and tracker.position != 0:
        action = "SELL" if tracker.position == 1 else "BUY"
        price = 0.0
        pnl = tracker.get_unrealized_pnl(price) if price > 0 else 0

        logger.info(f"SQUARE-OFF at {current_time}: closing position.")
        broker.place_order(action, sym["lot_size"], price, tag="SQUARE_OFF")

        # Telegram alert
        send_squareoff_alert(ACTIVE_SYMBOL, price, pnl)

        daily_pnl += pnl
        daily_trades += 1
        if pnl > 0:
            daily_wins += 1

        tracker = PositionTracker()
        return

    # Signal window check
    if not force and not is_signal_window():
        logger.debug(f"Outside signal window ({current_time}). Waiting.")
        return

    # Fetch candles
    df = get_candles()
    if df.empty:
        logger.warning("No candles available. Skipping cycle.")
        return

    # Evaluate signal
    signal = evaluate_signal(df)
    snap = get_bb_snapshot(df)

    if signal:
        logger.info(f"SIGNAL: {signal} | BB: {snap}")

        if signal == "BUY" and tracker.position != 1:
            qty = sym["lot_size"] * 2 if tracker.position == -1 else sym["lot_size"]
            price = df["close"].iloc[-1]

            # Calculate stop loss
            lookback = min(len(df), 20)
            swing_low = df["low"].iloc[-lookback:].min()
            from config import ATR_BUFFER_MULT
            from bb_sar_engine import calculate_atr
            atr = calculate_atr(df).iloc[-1]
            buffer = atr * ATR_BUFFER_MULT
            stop_loss = swing_low - buffer

            # Open position
            tracker._entry_idx = len(df) - 1
            tracker.open_position(1, price, atr, swing_low=swing_low)

            # Execute trade
            broker.place_order("BUY", qty, price, tag="SIGNAL")

            # Telegram alert
            send_signal_alert("BUY", ACTIVE_SYMBOL, price, stop_loss, snap)
            send_trade_alert("BUY", ACTIVE_SYMBOL, qty, price)

        elif signal == "SELL" and tracker.position != -1:
            qty = sym["lot_size"] * 2 if tracker.position == 1 else sym["lot_size"]
            price = df["close"].iloc[-1]

            # Calculate stop loss
            lookback = min(len(df), 20)
            swing_high = df["high"].iloc[-lookback:].max()
            from config import ATR_BUFFER_MULT
            from bb_sar_engine import calculate_atr
            atr = calculate_atr(df).iloc[-1]
            buffer = atr * ATR_BUFFER_MULT
            stop_loss = swing_high + buffer

            # Open position
            tracker._entry_idx = len(df) - 1
            tracker.open_position(-1, price, atr, swing_high=swing_high)

            # Execute trade
            broker.place_order("SELL", qty, price, tag="SIGNAL")

            # Telegram alert
            send_signal_alert("SELL", ACTIVE_SYMBOL, price, stop_loss, snap)
            send_trade_alert("SELL", ACTIVE_SYMBOL, qty, price)

    else:
        logger.info(
            f"No signal | Close: {snap.get('close', 'N/A')} | "
            f"Upper: {snap.get('upper', 'N/A')} | Lower: {snap.get('lower', 'N/A')} | "
            f"BW%: {snap.get('bandwidth_pct', 'N/A')} | Slope: {snap.get('slope', 'N/A')}"
        )


def send_eod_summary():
    """Send end-of-day summary via Telegram."""
    global daily_pnl, daily_trades, daily_wins

    if daily_trades > 0:
        win_rate = daily_wins / daily_trades * 100
        send_daily_summary(daily_pnl, daily_trades, win_rate)
    else:
        from telegram_notifier import send_message
        send_message(f"📊 <b>DAILY SUMMARY</b>\n\nNo trades today.\nDate: {datetime.now().strftime('%d %b %Y')}")

    # Reset daily stats
    daily_pnl = 0.0
    daily_trades = 0
    daily_wins = 0


def main():
    logger.info("=" * 60)
    logger.info(f"  BB + Pure SAR Bot — {ACTIVE_SYMBOL} — MODE: {MODE}")
    logger.info(f"  Lot size: {SYMBOLS[ACTIVE_SYMBOL]['lot_size']}")
    logger.info(f"  Signal window: {SIGNAL_START}–{SIGNAL_END} IST")
    logger.info(f"  Square-off: {SQUARE_OFF} IST")
    logger.info(f"  Telegram: {'✅ Configured' if TELEGRAM_TOKEN else '❌ Not configured'}")
    logger.info("=" * 60)

    # Test Telegram connection
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        test_connection()
        send_status_update("Bot started", 0, 0)

    broker = get_broker()

    if "--once" in sys.argv:
        logger.info("Running single evaluation (--once flag).")
        run_once(broker, force=True)
        return

    if "--test-telegram" in sys.argv:
        logger.info("Testing Telegram connection.")
        test_connection()
        return

    # Main loop
    logger.info("Bot started. Listening for 5-min bar closes...")
    last_square_off_date = None

    while True:
        try:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")

            if not is_market_hours():
                # Send EOD summary once after market close
                if last_square_off_date != today and now.strftime("%H:%M") >= "15:30":
                    send_eod_summary()
                    last_square_off_date = today

                logger.info(f"Market closed ({now.strftime('%H:%M')}). Sleeping 5 min.")
                time.sleep(300)
                continue

            run_once(broker)

            # Sleep until next 5-min boundary
            seconds_past = now.second + now.minute * 60
            next_5m = ((seconds_past // 300) + 1) * 300
            sleep_time = max(next_5m - seconds_past, 10)
            logger.info(f"Sleeping {sleep_time}s until next 5-min bar.")
            time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
                send_status_update("Bot stopped")
            break
        except Exception as e:
            logger.error(f"Loop error: {e}", exc_info=True)
            time.sleep(30)


if __name__ == "__main__":
    main()
