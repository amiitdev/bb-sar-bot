import { useState, useEffect } from 'react'
import axios from 'axios'
import { Activity, TrendingUp, TrendingDown, DollarSign, BarChart3, Settings, Play, Square } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const API = '/api'

function App() {
  const [tab, setTab] = useState('dashboard')
  const [status, setStatus] = useState(null)
  const [signals, setSignals] = useState(null)
  const [trades, setTrades] = useState([])
  const [backtest, setBacktest] = useState(null)
  const [credentials, setCredentials] = useState({ client_id: '', access_token: '' })

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API}/status`)
      setStatus(res.data)
    } catch (e) {
      console.error('Failed to fetch status:', e)
    }
  }

  const fetchSignals = async () => {
    try {
      const res = await axios.get(`${API}/signals`)
      setSignals(res.data)
    } catch (e) {
      console.error('Failed to fetch signals:', e)
    }
  }

  const fetchTrades = async () => {
    try {
      const res = await axios.get(`${API}/trades`)
      setTrades(res.data.trades || [])
    } catch (e) {
      console.error('Failed to fetch trades:', e)
    }
  }

  const fetchBacktest = async () => {
    try {
      const res = await axios.get(`${API}/backtest`)
      setBacktest(res.data)
    } catch (e) {
      console.error('Failed to fetch backtest:', e)
    }
  }

  const saveCredentials = async () => {
    try {
      await axios.post(`${API}/credentials`, credentials)
      alert('Credentials saved!')
    } catch (e) {
      alert('Failed to save credentials')
    }
  }

  const startBot = async () => {
    try {
      await axios.post(`${API}/start`, { mode: 'paper', symbol: 'NIFTY' })
      fetchStatus()
    } catch (e) {
      alert('Failed to start bot')
    }
  }

  const stopBot = async () => {
    try {
      await axios.post(`${API}/stop`)
      fetchStatus()
    } catch (e) {
      alert('Failed to stop bot')
    }
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BarChart3 className="h-8 w-8 text-blue-500" />
            <h1 className="text-2xl font-bold">BB + Pure SAR Bot</h1>
            <span className="ml-2 px-2 py-1 text-xs bg-slate-700 rounded">{status?.mode || 'paper'}</span>
          </div>
          <div className="flex items-center gap-4">
            {status?.running ? (
              <button onClick={stopBot} className="btn-danger flex items-center gap-2">
                <Square className="h-4 w-4" /> Stop Bot
              </button>
            ) : (
              <button onClick={startBot} className="btn-primary flex items-center gap-2">
                <Play className="h-4 w-4" /> Start Bot
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="border-b border-slate-700 px-6">
        <div className="flex gap-6">
          {['dashboard', 'signals', 'trades', 'backtest', 'settings'].map(t => (
            <button
              key={t}
              onClick={() => {
                setTab(t)
                if (t === 'signals') fetchSignals()
                if (t === 'trades') fetchTrades()
                if (t === 'backtest') fetchBacktest()
              }}
              className={`py-3 px-1 border-b-2 transition-colors ${
                tab === t
                  ? 'border-blue-500 text-blue-500'
                  : 'border-transparent text-slate-400 hover:text-white'
              }`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </nav>

      {/* Content */}
      <main className="p-6">
        {tab === 'dashboard' && <Dashboard status={status} />}
        {tab === 'signals' && <Signals signals={signals} />}
        {tab === 'trades' && <Trades trades={trades} />}
        {tab === 'backtest' && <Backtest data={backtest} />}
        {tab === 'settings' && (
          <SettingsTab
            credentials={credentials}
            setCredentials={setCredentials}
            onSave={saveCredentials}
          />
        )}
      </main>
    </div>
  )
}

function Dashboard({ status }) {
  if (!status) return <div className="text-slate-400">Loading...</div>

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatCard
        icon={<Activity className="h-6 w-6 text-blue-500" />}
        label="Status"
        value={status.running ? 'Running' : 'Stopped'}
        color={status.running ? 'green' : 'red'}
      />
      <StatCard
        icon={<TrendingUp className="h-6 w-6 text-green-500" />}
        label="Position"
        value={status.position === 1 ? 'LONG' : status.position === -1 ? 'SHORT' : 'FLAT'}
        color={status.position === 1 ? 'green' : status.position === -1 ? 'red' : 'slate'}
      />
      <StatCard
        icon={<DollarSign className="h-6 w-6 text-yellow-500" />}
        label="Total P&L"
        value={`${status.total_pnl >= 0 ? '+' : ''}${status.total_pnl}`}
        color={status.total_pnl >= 0 ? 'green' : 'red'}
      />
      <StatCard
        icon={<BarChart3 className="h-6 w-6 text-purple-500" />}
        label="Win Rate"
        value={`${status.win_rate}%`}
        color={status.win_rate >= 50 ? 'green' : 'red'}
      />

      {/* Position Details */}
      <div className="card col-span-2">
        <h3 className="text-lg font-semibold mb-4">Position Details</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-slate-400 text-sm">Symbol</span>
            <p className="text-xl font-bold">{status.symbol}</p>
          </div>
          <div>
            <span className="text-slate-400 text-sm">Lot Size</span>
            <p className="text-xl font-bold">{status.lot_size}</p>
          </div>
          <div>
            <span className="text-slate-400 text-sm">Entry Price</span>
            <p className="text-xl font-bold">{status.entry_price || '—'}</p>
          </div>
          <div>
            <span className="text-slate-400 text-sm">Stop Loss</span>
            <p className="text-xl font-bold text-red-400">{status.stop_loss || '—'}</p>
          </div>
          <div>
            <span className="text-slate-400 text-sm">Peak Price</span>
            <p className="text-xl font-bold">{status.peak_price || '—'}</p>
          </div>
          <div>
            <span className="text-slate-400 text-sm">Total Trades</span>
            <p className="text-xl font-bold">{status.total_trades}</p>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="card col-span-2">
        <h3 className="text-lg font-semibold mb-4">Strategy Parameters</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">BB Period</span>
            <span>20</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">BB Std Dev</span>
            <span>2.0</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">ATR Buffer</span>
            <span>0.75x</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Breakeven Trigger</span>
            <span>0.75R</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Trailing Trigger</span>
            <span>1.2R</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Trailing Distance</span>
            <span>0.6R</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Signal Window</span>
            <span>09:30 – 14:45 IST</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Square-off</span>
            <span>15:15 IST</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, color }) {
  const colorMap = {
    green: 'text-green-500',
    red: 'text-red-500',
    yellow: 'text-yellow-500',
    blue: 'text-blue-500',
    slate: 'text-slate-400',
  }

  return (
    <div className="card">
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className="text-slate-400 text-sm">{label}</p>
          <p className={`text-2xl font-bold ${colorMap[color] || 'text-white'}`}>{value}</p>
        </div>
      </div>
    </div>
  )
}

function Signals({ signals }) {
  if (!signals) return <div className="text-slate-400">Click "Signals" tab to load...</div>

  return (
    <div className="space-y-6">
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Current Signal</h3>
        <div className="flex items-center gap-4">
          <span className={`px-4 py-2 rounded-lg font-bold text-lg ${
            signals.current_signal === 'BUY' ? 'signal-buy' :
            signals.current_signal === 'SELL' ? 'signal-sell' :
            'bg-slate-700 text-slate-300'
          }`}>
            {signals.current_signal || 'NO SIGNAL'}
          </span>
          <span className="text-slate-400">{signals.timestamp}</span>
        </div>
      </div>

      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Bollinger Bands Snapshot</h3>
        {signals.bb_snapshot && Object.keys(signals.bb_snapshot).length > 0 ? (
          <div className="grid grid-cols-3 gap-4">
            <div>
              <span className="text-slate-400 text-sm">Close</span>
              <p className="text-xl font-bold">{signals.bb_snapshot.close}</p>
            </div>
            <div>
              <span className="text-slate-400 text-sm">Upper Band</span>
              <p className="text-xl font-bold text-red-400">{signals.bb_snapshot.upper}</p>
            </div>
            <div>
              <span className="text-slate-400 text-sm">Lower Band</span>
              <p className="text-xl font-bold text-green-400">{signals.bb_snapshot.lower}</p>
            </div>
            <div>
              <span className="text-slate-400 text-sm">Basis (SMA)</span>
              <p className="text-xl font-bold">{signals.bb_snapshot.basis}</p>
            </div>
            <div>
              <span className="text-slate-400 text-sm">Bandwidth %</span>
              <p className="text-xl font-bold">{signals.bb_snapshot.bandwidth_pct}%</p>
            </div>
            <div>
              <span className="text-slate-400 text-sm">Slope</span>
              <p className="text-xl font-bold">{signals.bb_snapshot.slope}</p>
            </div>
          </div>
        ) : (
          <p className="text-slate-400">Waiting for data...</p>
        )}
      </div>

      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Recent Signals</h3>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Signal</th>
              <th>Price</th>
            </tr>
          </thead>
          <tbody>
            {signals.recent_signals?.length > 0 ? (
              signals.recent_signals.map((s, i) => (
                <tr key={i}>
                  <td>{new Date(s.time).toLocaleString()}</td>
                  <td>
                    <span className={`px-2 py-1 rounded text-xs font-bold ${
                      s.signal === 'BUY' ? 'signal-buy' : 'signal-sell'
                    }`}>
                      {s.signal}
                    </span>
                  </td>
                  <td>{s.price}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="3" className="text-center text-slate-400">No signals yet</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Trades({ trades }) {
  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Trade History</h3>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Action</th>
            <th>Symbol</th>
            <th>Qty</th>
            <th>Price</th>
            <th>P&L</th>
          </tr>
        </thead>
        <tbody>
          {trades.length > 0 ? (
            trades.map((t, i) => (
              <tr key={i}>
                <td>{t.timestamp}</td>
                <td>
                  <span className={`px-2 py-1 rounded text-xs font-bold ${
                    t.action === 'BUY' ? 'signal-buy' : 'signal-sell'
                  }`}>
                    {t.action}
                  </span>
                </td>
                <td>{t.symbol}</td>
                <td>{t.qty}</td>
                <td>{t.price}</td>
                <td className={parseFloat(t.pnl) >= 0 ? 'text-green-500' : 'text-red-500'}>
                  {parseFloat(t.pnl) >= 0 ? '+' : ''}{t.pnl}
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan="6" className="text-center text-slate-400">No trades yet</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function Backtest({ data }) {
  if (!data) return <div className="text-slate-400">Click "Backtest" tab to load...</div>
  if (data.error) return <div className="text-red-400">{data.error}</div>

  return (
    <div className="space-y-6">
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Backtest Results</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <span className="text-slate-400 text-sm">Total Trades</span>
            <p className="text-2xl font-bold">{data.total_trades}</p>
          </div>
          <div>
            <span className="text-slate-400 text-sm">Win Rate</span>
            <p className="text-2xl font-bold text-green-500">{data.win_rate}%</p>
          </div>
          <div>
            <span className="text-slate-400 text-sm">Net P&L</span>
            <p className={`text-2xl font-bold ${data.net_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {data.net_pnl >= 0 ? '+' : ''}{data.net_pnl}
            </p>
          </div>
          <div>
            <span className="text-slate-400 text-sm">Profit Factor</span>
            <p className="text-2xl font-bold">{data.profit_factor}</p>
          </div>
          <div>
            <span className="text-slate-400 text-sm">Avg Win</span>
            <p className="text-xl font-bold text-green-500">+{data.avg_win}</p>
          </div>
          <div>
            <span className="text-slate-400 text-sm">Avg Loss</span>
            <p className="text-xl font-bold text-red-500">{data.avg_loss}</p>
          </div>
          <div>
            <span className="text-slate-400 text-sm">Max Drawdown</span>
            <p className="text-xl font-bold text-red-500">{data.max_drawdown}</p>
          </div>
          <div>
            <span className="text-slate-400 text-sm">Data File</span>
            <p className="text-sm">{data.data_file}</p>
          </div>
        </div>
      </div>

      {/* Year-by-Year */}
      {data.years && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Year-by-Year Breakdown</h3>
          <table>
            <thead>
              <tr>
                <th>Year</th>
                <th>Trades</th>
                <th>Win Rate</th>
                <th>Net P&L</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.years).map(([year, stats]) => (
                <tr key={year}>
                  <td className="font-bold">{year}</td>
                  <td>{stats.trades}</td>
                  <td className="text-green-500">{stats.win_rate}%</td>
                  <td className={stats.net_pnl >= 0 ? 'text-green-500' : 'text-red-500'}>
                    {stats.net_pnl >= 0 ? '+' : ''}{stats.net_pnl}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Exit Types */}
      {data.exit_types && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Exit Type Breakdown</h3>
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(data.exit_types).map(([type, stats]) => (
              <div key={type} className="bg-slate-800 p-4 rounded-lg">
                <span className="text-slate-400 text-sm">{type}</span>
                <p className="text-xl font-bold">{stats.count}</p>
                <p className={`text-sm ${stats.pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {stats.pnl >= 0 ? '+' : ''}{stats.pnl} pts
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function SettingsTab({ credentials, setCredentials, onSave }) {
  return (
    <div className="card max-w-lg">
      <h3 className="text-lg font-semibold mb-4">Dhan API Credentials</h3>
      <div className="space-y-4">
        <div>
          <label className="text-slate-400 text-sm block mb-1">Client ID</label>
          <input
            type="text"
            value={credentials.client_id}
            onChange={e => setCredentials({ ...credentials, client_id: e.target.value })}
            placeholder="Enter your Dhan Client ID"
          />
        </div>
        <div>
          <label className="text-slate-400 text-sm block mb-1">Access Token</label>
          <input
            type="password"
            value={credentials.access_token}
            onChange={e => setCredentials({ ...credentials, access_token: e.target.value })}
            placeholder="Enter your Dhan Access Token"
          />
        </div>
        <button onClick={onSave} className="btn-primary">
          Save Credentials
        </button>
        <p className="text-slate-500 text-sm">
          Credentials are saved locally and never shared. Required for live trading mode.
        </p>
      </div>
    </div>
  )
}

export default App
