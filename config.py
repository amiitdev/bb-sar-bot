import os
from pathlib import Path

# Load .env file if it exists
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

# ============================================================
# MODE: "paper" = simulated orders, "live" = real Dhan orders
# ============================================================
MODE = os.getenv("BOT_MODE", "paper")

# ============================================================
# STRATEGY SETTINGS
# ============================================================
SYMBOLS = {
    "NIFTY": {"security_id": "13", "lot_size": 50, "exchange": "INDEX"},
    "BANKNIFTY": {"security_id": "13", "lot_size": 15, "exchange": "INDEX"},
}
ACTIVE_SYMBOL = "NIFTY"  # Switch to "BANKNIFTY" as needed

BB_PERIOD = 20
BB_STD_MULT = 2.0
MIN_BANDWIDTH_PCT = 0.20
MIN_SLOPE = 6.0  # Minimum absolute basis slope (pts over 3 bars)
SLOPE_LOOKBACK = 3

# ATR and Exit Settings
ATR_PERIOD = 14
ATR_BUFFER_MULT = 0.75   # ATR buffer for stop loss placement
BE_TRIGGER_R = 0.75      # Phase 1: Breakeven trigger at 0.75R
BE_OFFSET_R = 0.05       # Phase 1: Profit locked at BE (+0.05R)
TRAIL_TRIGGER_R = 1.20   # Phase 2: Trailing trigger at 1.2R
TRAIL_DIST_R = 0.60      # Phase 2: Trailing distance (0.6R behind peak)

# Rolling candle buffer (indicators only need last 100)
MAX_CANDLES = 100

# ============================================================
# SESSION SETTINGS (IST)
# ============================================================
MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"
SIGNAL_START = "09:30"
SIGNAL_END = "14:45"
SQUARE_OFF = "15:15"

# ============================================================
# Dhan API (set via environment or fill in directly)
# ============================================================
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")

# ============================================================
# TELEGRAM (set via environment or fill in directly)
# ============================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ============================================================
# PATHS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
TRADE_LOG = BASE_DIR / "trades" / "trades.csv"
LOG_FILE = BASE_DIR / "logs" / "bot.log"
DATA_DIR = BASE_DIR / "data"
