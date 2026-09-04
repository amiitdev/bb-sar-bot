"""
Telegram notifier — sends alerts to Telegram.

Usage:
    from telegram_notifier import send_alert
    send_alert("BUY", "NIFTY", 23850.50, stop_loss=23790.00)
"""
import requests
import logging
from datetime import datetime
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


def send_message(text: str) -> bool:
    """Send a message to Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured — skipping alert.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Telegram alert sent.")
            return True
        else:
            logger.error(f"Telegram error: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def send_signal_alert(signal: str, symbol: str, price: float, stop_loss: float = None, bb_snapshot: dict = None):
    """Send a trading signal alert."""
    emoji = "🟢" if signal == "BUY" else "🔴"
    time_str = datetime.now().strftime("%I:%M %p IST")

    msg = f"""
{emoji} <b>{signal} SIGNAL</b>

Symbol: <b>{symbol}</b>
Price: <b>{price:,.2f}</b>
Time: {time_str}
"""
    if stop_loss:
        msg += f"Stop Loss: {stop_loss:,.2f}\n"

    if bb_snapshot:
        msg += f"""
📊 <b>Bollinger Bands</b>
Upper: {bb_snapshot.get('upper', 'N/A')}
Basis: {bb_snapshot.get('basis', 'N/A')}
Lower: {bb_snapshot.get('lower', 'N/A')}
Bandwidth: {bb_snapshot.get('bandwidth_pct', 'N/A')}%
Slope: {bb_snapshot.get('slope', 'N/A')}
"""
    return send_message(msg.strip())


def send_trade_alert(action: str, symbol: str, qty: int, price: float, pnl: float = None):
    """Send a trade execution alert."""
    emoji = "✅" if action == "BUY" else "❌"
    time_str = datetime.now().strftime("%I:%M %p IST")

    msg = f"""
{emoji} <b>ORDER EXECUTED</b>

Action: <b>{action}</b>
Symbol: {symbol}
Qty: {qty}
Price: {price:,.2f}
Time: {time_str}
"""
    if pnl is not None:
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        msg += f"\n{pnl_emoji} P&L: {pnl:+,.2f} pts"

    return send_message(msg.strip())


def send_squareoff_alert(symbol: str, price: float, pnl: float):
    """Send square-off alert."""
    time_str = datetime.now().strftime("%I:%M %p IST")
    pnl_emoji = "📈" if pnl >= 0 else "📉"

    msg = f"""
⏰ <b>SQUARE-OFF (15:15 IST)</b>

Symbol: {symbol}
Price: {price:,.2f}
{pnl_emoji} P&L: {pnl:+,.2f} pts
Time: {time_str}
"""
    return send_message(msg.strip())


def send_daily_summary(total_pnl: float, trades: int, win_rate: float):
    """Send end-of-day summary."""
    pnl_emoji = "📈" if total_pnl >= 0 else "📉"

    msg = f"""
📊 <b>DAILY SUMMARY</b>

{pnl_emoji} Total P&L: {total_pnl:+,.2f} pts
Trades: {trades}
Win Rate: {win_rate:.1f}%
Date: {datetime.now().strftime("%d %b %Y")}
"""
    return send_message(msg.strip())


def send_status_update(status: str, position: int = 0, entry_price: float = 0):
    """Send bot status update."""
    pos_text = "LONG" if position == 1 else "SHORT" if position == -1 else "FLAT"

    msg = f"""
🤖 <b>BOT STATUS</b>

Status: {status}
Position: {pos_text}
Entry: {entry_price:,.2f if entry_price else 'N/A'}
Time: {datetime.now().strftime("%I:%M %p IST")}
"""
    return send_message(msg.strip())


def test_connection() -> bool:
    """Test Telegram connection."""
    return send_message("🤖 <b>BB + Pure SAR Bot</b>\n\n✅ Telegram connected successfully!")
