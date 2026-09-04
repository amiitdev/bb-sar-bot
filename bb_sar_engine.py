"""
Bollinger Bands + Pure SAR (Stop-and-Reverse) Engine with Hybrid Exit.

Strategy logic (from PDF spec):
  - Bollinger Bands: SMA(20) ± 2.0 × StdDev
  - Flat-market filter: bandwidth < 0.20% OR basis slope < 6.0 pts → no trade
  - BUY: close crosses ABOVE lower band (prev bar was ≤ lower)
  - SELL: close crosses BELOW upper band (prev bar was ≥ upper)
  - Stop-and-Reverse: always in a position (long or short), flips on opposite signal
  - Hybrid Exit: Phase 1 breakeven at 0.75R, Phase 2 trailing at 1.2R with 0.6R trail
"""
import pandas as pd
import numpy as np
from config import (
    BB_PERIOD, BB_STD_MULT, MIN_BANDWIDTH_PCT, MIN_SLOPE,
    SLOPE_LOOKBACK, ATR_PERIOD, ATR_BUFFER_MULT,
    BE_TRIGGER_R, BE_OFFSET_R, TRAIL_TRIGGER_R, TRAIL_DIST_R,
)

# ============================================================
# Indicator calculations
# ============================================================

def calculate_bb(df: pd.DataFrame) -> pd.DataFrame:
    """Add Bollinger Band columns to dataframe."""
    data = df.copy()
    data["basis"] = data["close"].rolling(BB_PERIOD).mean()
    data["dev"] = BB_STD_MULT * data["close"].rolling(BB_PERIOD).std()
    data["upper"] = data["basis"] + data["dev"]
    data["lower"] = data["basis"] - data["dev"]
    return data


def calculate_atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    """Calculate Average True Range."""
    high = df["high"]
    low = df["low"]
    close = df["close"].shift(1)

    tr1 = high - low
    tr2 = (high - close).abs()
    tr3 = (low - close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr


def bandwidth_pct(row):
    """Bandwidth as % of basis."""
    if pd.isna(row["basis"]) or row["basis"] == 0:
        return np.nan
    return ((row["upper"] - row["lower"]) / row["basis"]) * 100.0


def basis_slope(data: pd.DataFrame, lookback: int = SLOPE_LOOKBACK) -> float:
    """Absolute slope of basis over `lookback` bars."""
    if len(data) < lookback + 1:
        return np.nan
    curr_basis = data["basis"].iloc[-1]
    prev_basis = data["basis"].iloc[-(lookback + 1)]
    return abs(curr_basis - prev_basis)


def evaluate_signal(df: pd.DataFrame) -> str | None:
    """
    Evaluate the latest bar for a BUY/SELL signal.
    Returns: "BUY", "SELL", or None.
    """
    if len(df) < BB_PERIOD + SLOPE_LOOKBACK + 2:
        return None

    data = calculate_bb(df)
    curr = data.iloc[-1]
    prev = data.iloc[-2]

    bw = bandwidth_pct(curr)
    slope = basis_slope(data)

    # Flat-market filter
    if pd.isna(bw) or pd.isna(slope):
        return None
    if bw < MIN_BANDWIDTH_PCT or slope < MIN_SLOPE:
        return None

    # Crossover logic
    buy_cross = (curr["close"] > curr["lower"]) and (prev["close"] <= prev["lower"])
    sell_cross = (curr["close"] < curr["upper"]) and (prev["close"] >= prev["upper"])

    if buy_cross:
        return "BUY"
    elif sell_cross:
        return "SELL"
    return None


def get_bb_snapshot(df: pd.DataFrame) -> dict:
    """Return current indicator values for logging/display."""
    if len(df) < BB_PERIOD + 2:
        return {}
    data = calculate_bb(df)
    curr = data.iloc[-1]
    return {
        "close": curr["close"],
        "basis": round(curr["basis"], 2),
        "upper": round(curr["upper"], 2),
        "lower": round(curr["lower"], 2),
        "bandwidth_pct": round(bandwidth_pct(curr), 4),
        "slope": round(basis_slope(data), 2),
    }


# ============================================================
# Position tracker with Hybrid Exit
# ============================================================

class PositionTracker:
    """
    Tracks open position with hybrid exit logic:
    - Phase 1: Breakeven at 0.75R → SL moves to entry + 0.05R
    - Phase 2: Trailing at 1.2R → SL trails by 0.6R behind peak
    """

    def __init__(self):
        self.position = 0       # 1=Long, -1=Short, 0=Flat
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.initial_risk = 0.0
        self.peak_price = 0.0
        self.atr = 0.0

    def open_position(self, direction: int, entry_price: float, atr: float, swing_low: float = None, swing_high: float = None):
        """
        Open a new position.
        direction: 1 for Long, -1 for Short
        """
        self.position = direction
        self.entry_price = entry_price
        self.atr = atr
        self.peak_price = entry_price

        buffer = atr * ATR_BUFFER_MULT

        if direction == 1:  # Long
            # SL below recent swing low - buffer
            if swing_low is not None:
                self.stop_loss = swing_low - buffer
            else:
                self.stop_loss = entry_price - (atr * 2)
            self.initial_risk = entry_price - self.stop_loss
        else:  # Short
            # SL above recent swing high + buffer
            if swing_high is not None:
                self.stop_loss = swing_high + buffer
            else:
                self.stop_loss = entry_price + (atr * 2)
            self.initial_risk = self.stop_loss - entry_price

    def update(self, current_high: float, current_low: float, current_close: float) -> str | None:
        """
        Update position with current bar data.
        Returns: "EXIT" if position closed, None otherwise.
        """
        if self.position == 0:
            return None

        # Update peak price for trailing
        if self.position == 1:
            self.peak_price = max(self.peak_price, current_high)
        else:
            self.peak_price = min(self.peak_price, current_low)

        # Calculate current R-multiple
        if self.position == 1:
            gain_pts = current_high - self.entry_price
        else:
            gain_pts = self.entry_price - current_low

        gain_r = gain_pts / self.initial_risk if self.initial_risk > 0 else 0

        # Phase 1: Breakeven at 0.75R
        if gain_r >= BE_TRIGGER_R:
            if self.position == 1:
                new_sl = self.entry_price + (BE_OFFSET_R * self.initial_risk)
                self.stop_loss = max(self.stop_loss, new_sl)
            else:
                new_sl = self.entry_price - (BE_OFFSET_R * self.initial_risk)
                self.stop_loss = min(self.stop_loss, new_sl)

        # Phase 2: Trailing at 1.2R
        if gain_r >= TRAIL_TRIGGER_R:
            if self.position == 1:
                new_sl = self.peak_price - (TRAIL_DIST_R * self.initial_risk)
                self.stop_loss = max(self.stop_loss, new_sl)
            else:
                new_sl = self.peak_price + (TRAIL_DIST_R * self.initial_risk)
                self.stop_loss = min(self.stop_loss, new_sl)

        # Check stop loss hit
        if self.position == 1 and current_low <= self.stop_loss:
            self.position = 0
            return "EXIT"
        elif self.position == -1 and current_high >= self.stop_loss:
            self.position = 0
            return "EXIT"

        return None

    def get_unrealized_pnl(self, current_price: float) -> float:
        """Get unrealized P&L in points."""
        if self.position == 1:
            return current_price - self.entry_price
        elif self.position == -1:
            return self.entry_price - current_price
        return 0.0

    def get_r_multiple(self, current_price: float) -> float:
        """Get current R-multiple."""
        if self.initial_risk <= 0:
            return 0.0
        pnl = self.get_unrealized_pnl(current_price)
        return pnl / self.initial_risk
