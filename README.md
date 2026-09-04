# 📈 BB + Pure SAR Trading Bot

> **Automated Bollinger Bands + Pure Stop-and-Reverse Trading Bot for Indian Indices (NIFTY/BankNifty)**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.3-06B6D4.svg)](https://tailwindcss.com)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4.svg)](https://telegram.org)

---

## 🎯 Features

- **Hybrid Exit Logic** — Breakeven at 0.75R + Trailing stop at 1.2R
- **Flat Market Filter** — Avoids choppy markets (bandwidth < 0.20% OR slope < 6.0)
- **Live Data** — Real-time NIFTY prices via Yahoo Finance (free, no API key)
- **Telegram Alerts** — Instant BUY/SELL notifications on your phone
- **Web Dashboard** — Beautiful React + Tailwind UI for monitoring
- **Paper Trading** — Test risk-free before going live
- **Dhan API Integration** — Ready for live trading with Dhan broker

---

## 📊 Strategy Overview

### Entry Rules
| Signal | Condition |
|--------|-----------|
| 🟢 **BUY** | Close crosses **above** lower Bollinger Band |
| 🔴 **SELL** | Close crosses **below** upper Bollinger Band |

### Exit Rules (Hybrid Logic)
| Phase | Trigger | Action |
|-------|---------|--------|
| Phase 1 | Price reaches 0.75R profit | Move SL to entry + 0.05R (breakeven) |
| Phase 2 | Price reaches 1.2R profit | Trail SL by 0.6R |
| Reverse | Opposite signal appears | Exit and take new position |
| Square-off | 3:15 PM IST | Close all positions |

### Flat Market Filter
```
IF bandwidth < 0.20% OR basis_slope < 6.0:
    → NO TRADE (market is choppy)
```

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/amiitdev/bb-sar-bot.git
cd bb-sar-bot
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 4. Run the Bot

```bash
# Start the web dashboard
python3 -m uvicorn api:app --host 0.0.0.0 --port 8001

# Open http://localhost:8001 in your browser
# Click "Start Bot" to begin trading
```

---

## 📁 Project Structure

```
bb-sar-bot/
├── 📄 config.py          # Strategy & broker settings
├── 📄 bb_sar_engine.py   # Core BB + SAR + Hybrid Exit logic
├── 📄 broker.py          # PaperBroker & LiveBroker adapters
├── 📄 fetcher.py         # Dhan API + Yahoo Finance data fetcher
├── 📄 run.py             # Main bot entry point (5-min loop)
├── 📄 backtest.py        # Historical backtester
├── 📄 api.py             # FastAPI backend
├── 📄 telegram_notifier.py # Telegram alert functions
├── 📄 setup_telegram.py  # Interactive Telegram setup wizard
├── 📄 session_memory.py  # SQLite session storage
├── 📄 requirements.txt   # Python dependencies
├── 📄 .env.example       # Environment template
├── 📄 .gitignore         # Git ignore rules
├── 📄 README.md          # This file
│
├── 📁 frontend/          # React + Vite + Tailwind
│   ├── 📄 package.json
│   ├── 📄 vite.config.js
│   ├── 📄 tailwind.config.js
│   ├── 📁 src/
│   │   ├── 📄 App.jsx
│   │   ├── 📄 main.jsx
│   │   └── 📄 index.css
│   └── 📁 dist/          # Built frontend
│
├── 📁 trades/            # Trade logs (CSV)
├── 📁 logs/              # Bot logs
├── 📁 data/              # Cached market data
└── 📄 session.db         # SQLite database
```

---

## 🔧 Configuration

### Environment Variables (`.env`)

```env
# Dhan API Credentials
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token

# Telegram Bot
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading Mode
BOT_MODE=paper  # paper or live
```

### Strategy Settings (`config.py`)

```python
# Bollinger Bands
BB_PERIOD = 20
BB_STD_DEV = 2.0

# Pure SAR
SAR_AF = 0.02
SAR_MAX_AF = 0.2

# Hybrid Exit
PHASE1_R = 0.75      # Breakeven at 0.75R
PHASE2_R = 1.2       # Trailing at 1.2R
TRAIL_STEP = 0.6     # Trail by 0.6R

# Flat Market Filter
MIN_BANDWIDTH = 0.20  # Minimum bandwidth %
MIN_SLOPE = 6.0       # Minimum basis slope

# Risk Management
ATR_MULT = 0.75       # ATR buffer for SL
```

---

## 📱 Telegram Alerts

The bot sends instant alerts for:

| Alert Type | Description |
|------------|-------------|
| 🟢 BUY Signal | Entry signal with price & stop loss |
| 🔴 SELL Signal | Entry signal with price & stop loss |
| 📊 Square-off | End-of-day position closure |
| 📈 Daily Summary | P&L, trades, and win rate |

### Setup Telegram Bot

```bash
python setup_telegram.py
```

Follow the interactive wizard to:
1. Create a bot via @BotFather
2. Get your Chat ID
3. Test the connection

---

## 📈 Backtest Results

### NIFTY 5-Minute (2022-2026)

| Metric | Value |
|--------|-------|
| Total Trades | 3,189 |
| Win Rate | 6.2% |
| Net P&L | **+765,092 pts** |
| Profit Factor | 26.84 |
| Max Drawdown | -4,662 pts |

### Year-by-Year Performance

| Year | Trades | Win Rate | Net P&L |
|------|--------|----------|---------|
| 2022 | 713 | 6.9% | +240,180 |
| 2023 | 594 | 5.1% | +80,735 |
| 2024 | 708 | 6.4% | +176,535 |
| 2025 | 691 | 5.8% | +157,972 |
| 2026 | 483 | 6.8% | +109,670 |

> **Note:** Low win rate is by design — most trades exit at breakeven, while winning trades capture large moves.

---

## 🖥️ Web Dashboard

The React dashboard provides:

- **Real-time Status** — Current position, P&L, win rate
- **Signal Monitor** — Live BUY/SELL signals
- **Trade History** — All executed trades
- **Backtest** — Run historical tests
- **Settings** — Configure strategy parameters

### Tech Stack

- **Frontend:** React 18 + Vite + Tailwind CSS
- **Backend:** FastAPI + Uvicorn
- **Data:** Yahoo Finance (live) + Dhan API
- **Storage:** SQLite + CSV

---

## 🚢 Deployment

### Render (Recommended)

1. Push to GitHub
2. Connect to [Render](https://render.com)
3. Create a new **Web Service**
4. Use these settings:
   - **Build Command:** `pip install -r requirements.txt && cd frontend && npm install && npm run build`
   - **Start Command:** `uvicorn api:app --host 0.0.0.0 --port $PORT`

### Docker

```bash
docker build -t bb-sar-bot .
docker run -p 8001:8001 bb-sar-bot
```

### VPS (Any Linux Server)

```bash
# Install dependencies
sudo apt update && sudo apt install python3-pip nodejs npm

# Clone and setup
git clone https://github.com/amiitdev/bb-sar-bot.git
cd bb-sar-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..

# Run with systemd
sudo cp bb-sar-bot.service /etc/systemd/system/
sudo systemctl enable bb-sar-bot
sudo systemctl start bb-sar-bot
```

---

## ⚠️ Disclaimer

This bot is for **educational purposes only**. Trading involves significant risk of financial loss.

- **Paper trade first** — Test for 1-2 weeks before going live
- **Start small** — Begin with 1 lot (NIFTY = 50 qty)
- **No guarantee of profit** — Past performance doesn't guarantee future results
- **Risk capital only** — Never trade with money you can't afford to lose

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📖 Documentation

- [API Documentation](API.md) — REST API endpoints
- [LICENSE](LICENSE) — MIT License

---

## 🔍 Troubleshooting

### Bot not starting?

```bash
# Check if port is in use
lsof -i :8001

# Kill existing process
pkill -9 -f "uvicorn api:app"

# Start again
python3 -m uvicorn api:app --host 0.0.0.0 --port 8001
```

### No signals appearing?

1. Check if market is open (9:15 AM - 3:30 PM IST)
2. Verify slope > 6.0 and bandwidth > 0.20%
3. Check logs: `tail -f logs/bot.log`

### Telegram not working?

```bash
# Test connection
python3 -c "from telegram_notifier import test_connection; test_connection()"
```

### Yahoo Finance not working?

```bash
# Test data fetch
python3 -c "from fetcher import fetch_live_yahoo; print(fetch_live_yahoo().tail())"
```

---

## 📞 Support

- **GitHub Issues:** [Report a bug](https://github.com/amiitdev/bb-sar-bot/issues)
- **Telegram:** [@AmitTradePulseBot](https://t.me/AmitTradePulseBot)

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Dhan API](https://api.dhan.co) — Trading broker API
- [Yahoo Finance](https://pypi.org/project/yfinance/) — Free market data
- [FastAPI](https://fastapi.tiangolo.com) — Modern Python web framework
- [React](https://reactjs.org) — Frontend library
- [Tailwind CSS](https://tailwindcss.com) — Utility-first CSS framework

---

**Made with ❤️ by [Amit](https://github.com/amiitdev)**
