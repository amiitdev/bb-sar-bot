"""
Broker adapter — Dhan API (live) or Paper (simulated).

Paper mode logs every order to trades/trades.csv with simulated fills.
Live mode uses the dhanhq SDK to place real orders.
"""
import csv
import logging
from datetime import datetime
from pathlib import Path

from config import (
    MODE, DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN,
    ACTIVE_SYMBOL, SYMBOLS, TRADE_LOG,
)

logger = logging.getLogger(__name__)


class PaperBroker:
    """Simulated broker — logs trades to CSV, tracks position in memory."""

    def __init__(self):
        self.position = 0  # 1=Long, -1=Short, 0=Flat
        self.entry_price = 0.0
        self.entry_time = None
        self.total_pnl = 0.0
        self.trade_count = 0
        self.win_count = 0
        self._ensure_csv()

    def _ensure_csv(self):
        TRADE_LOG.parent.mkdir(parents=True, exist_ok=True)
        if not TRADE_LOG.exists():
            with open(TRADE_LOG, "w", newline="") as f:
                csv.writer(f).writerow([
                    "timestamp", "action", "symbol", "qty", "price",
                    "position_before", "position_after", "pnl"
                ])

    def place_order(self, action: str, qty: int, price: float, tag: str = "") -> dict:
        now = datetime.now()
        pnl = 0.0

        if action == "BUY" and self.position == -1:
            pnl = (self.entry_price - price) * qty
        elif action == "SELL" and self.position == 1:
            pnl = (price - self.entry_price) * qty

        pos_before = self.position

        if action == "BUY":
            if self.position == -1:
                self.position = 1
            elif self.position == 0:
                self.position = 1
            self.entry_price = price
            self.entry_time = now
        elif action == "SELL":
            if self.position == 1:
                self.position = -1
            elif self.position == 0:
                self.position = -1
            self.entry_price = price
            self.entry_time = now

        self.total_pnl += pnl
        self.trade_count += 1
        if pnl > 0:
            self.win_count += 1

        row = [
            now.isoformat(), action, ACTIVE_SYMBOL, qty,
            round(price, 2), pos_before, self.position, round(pnl, 2),
        ]
        with open(TRADE_LOG, "a", newline="") as f:
            csv.writer(f).writerow(row)

        logger.info(
            f"PAPER {action} {qty} {ACTIVE_SYMBOL} @ {price:.2f} | "
            f"PnL: {pnl:+.2f} | Total: {self.total_pnl:+.2f} | "
            f"Trades: {self.trade_count} | WinRate: "
            f"{(self.win_count/self.trade_count*100):.1f}%"
        )
        return {"status": "filled", "action": action, "qty": qty, "price": price, "pnl": pnl}


class LiveBroker:
    """Real Dhan API broker."""

    def __init__(self):
        if not DHAN_CLIENT_ID or not DHAN_ACCESS_TOKEN:
            raise ValueError(
                "DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set. "
                "Export them or fill in config.py."
            )
        from dhanhq import DhanContext, dhanhq
        context = DhanContext(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
        self.dhan = dhanhq(context)
        self.position = 0
        self.entry_price = 0.0
        self.symbol_info = SYMBOLS[ACTIVE_SYMBOL]
        logger.info("Live Dhan broker connected.")

    def place_order(self, action: str, qty: int, price: float, tag: str = "") -> dict:
        from dhanhq import dhanhq
        trans_type = dhanhq.BUY if action == "BUY" else dhanhq.SELL
        exchange = getattr(dhanhq, self.symbol_info["exchange"], dhanhq.INDEX)

        try:
            resp = self.dhan.place_order(
                security_id=self.symbol_info["security_id"],
                exchange_segment=exchange,
                transaction_type=trans_type,
                quantity=qty,
                order_type=dhanhq.MARKET,
                product_type=dhanhq.INTRA,
                validity="DAY",
            )
            logger.info(f"LIVE ORDER: {action} {qty} {ACTIVE_SYMBOL} | Response: {resp}")

            if action == "BUY":
                self.position = 1 if self.position != -1 else 1
            else:
                self.position = -1 if self.position != 1 else -1
            self.entry_price = price

            return {"status": "placed", "action": action, "qty": qty, "response": resp}
        except Exception as e:
            logger.error(f"Order failed: {e}")
            return {"status": "failed", "error": str(e)}


def get_broker():
    """Factory: returns PaperBroker or LiveBroker based on MODE."""
    if MODE == "live":
        return LiveBroker()
    logger.info("Running in PAPER mode (no real orders).")
    return PaperBroker()
