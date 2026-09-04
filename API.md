# 📡 API Documentation

## Base URL

```
http://localhost:8001
```

## Endpoints

### GET `/api/status`

Get current bot status.

**Response:**
```json
{
  "running": true,
  "mode": "paper",
  "symbol": "NIFTY",
  "lot_size": 50,
  "position": 0,
  "entry_price": 0.0,
  "stop_loss": 0.0,
  "peak_price": 0.0,
  "total_trades": 0,
  "total_pnl": 0.0,
  "win_rate": 0,
  "timestamp": "2026-09-04T11:43:22.649670"
}
```

---

### GET `/api/signals`

Get current trading signals and Bollinger Bands snapshot.

**Response:**
```json
{
  "current_signal": null,
  "bb_snapshot": {
    "close": 23983.75,
    "basis": 23967.75,
    "upper": 23997.51,
    "lower": 23937.99,
    "bandwidth_pct": 0.2483,
    "slope": 5.53
  },
  "recent_signals": [],
  "timestamp": "2026-09-04T11:49:43.859968"
}
```

---

### GET `/api/trades`

Get all executed trades.

**Response:**
```json
{
  "trades": [
    {
      "time": "2026-09-04 10:30:00",
      "action": "BUY",
      "symbol": "NIFTY",
      "qty": 50,
      "price": 24150.00,
      "sl": 24080.00,
      "exit_price": 24200.00,
      "pnl": 2500.00
    }
  ],
  "total": 1,
  "win_rate": 100.0,
  "total_pnl": 2500.0
}
```

---

### GET `/api/backtest`

Run backtest on historical data.

**Response:**
```json
{
  "total_trades": 3189,
  "win_rate": 6.2,
  "net_pnl": 765092.5,
  "profit_factor": 26.84,
  "max_drawdown": -4662.5
}
```

---

### POST `/api/start`

Start the trading bot.

**Response:**
```json
{
  "status": "started",
  "mode": "paper"
}
```

---

### POST `/api/stop`

Stop the trading bot.

**Response:**
```json
{
  "status": "stopped"
}
```

---

### POST `/api/credentials`

Update API credentials.

**Request Body:**
```json
{
  "dhan_client_id": "1100999451",
  "dhan_access_token": "your_token",
  "telegram_token": "your_bot_token",
  "telegram_chat_id": "your_chat_id"
}
```

**Response:**
```json
{
  "status": "updated",
  "message": "Credentials saved. Restart bot to apply."
}
```

---

## WebSocket (Future)

```javascript
// Connect to real-time updates
const ws = new WebSocket('ws://localhost:8001/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data); // { type: 'signal', data: {...} }
};
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "Error message",
  "details": "Additional information"
}
```

**HTTP Status Codes:**
- `200` — Success
- `400` — Bad request
- `500` — Internal server error
