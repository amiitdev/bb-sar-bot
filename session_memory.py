"""
Session memory — stores conversation context in SQLite.

Usage:
    python session_memory.py          # Initialize database
    python session_memory.py --show   # Show stored session
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "session.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # Projects table
    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            path TEXT,
            description TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    # Session notes table
    c.execute("""
        CREATE TABLE IF NOT EXISTS session_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            category TEXT,
            note TEXT,
            created_at TEXT
        )
    """)

    # Configuration table
    c.execute("""
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            key TEXT,
            value TEXT,
            is_secret INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)

    # Backtest results table
    c.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            data_file TEXT,
            total_trades INTEGER,
            win_rate REAL,
            net_pnl REAL,
            profit_factor REAL,
            max_drawdown REAL,
            result_json TEXT,
            created_at TEXT
        )
    """)

    # Todo/checklist table
    c.execute("""
        CREATE TABLE IF NOT EXISTS todo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            task TEXT,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            created_at TEXT,
            completed_at TEXT
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {DB_PATH}")


def save_project(name, path, description=""):
    conn = get_db()
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO projects (name, path, description, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (name, path, description, now, now))
    conn.commit()
    conn.close()


def save_note(project_name, category, note):
    conn = get_db()
    conn.execute("""
        INSERT INTO session_notes (project_name, category, note, created_at)
        VALUES (?, ?, ?, ?)
    """, (project_name, category, note, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def save_config(project_name, key, value, is_secret=False):
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO config (project_name, key, value, is_secret, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (project_name, key, value, 1 if is_secret else 0, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def save_backtest(project_name, data_file, result):
    conn = get_db()
    conn.execute("""
        INSERT INTO backtest_results 
        (project_name, data_file, total_trades, win_rate, net_pnl, profit_factor, max_drawdown, result_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project_name, data_file,
        result.get("total_trades", 0),
        result.get("win_rate", 0),
        result.get("net_pnl", 0),
        result.get("profit_factor", 0),
        result.get("max_drawdown", 0),
        json.dumps(result),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def save_todo(project_name, task, status="pending", priority="medium"):
    conn = get_db()
    conn.execute("""
        INSERT INTO todo (project_name, task, status, priority, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (project_name, task, status, priority, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def complete_todo(todo_id):
    conn = get_db()
    conn.execute("""
        UPDATE todo SET status = 'completed', completed_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), todo_id))
    conn.commit()
    conn.close()


def get_project_notes(project_name):
    conn = get_db()
    rows = conn.execute("""
        SELECT category, note, created_at FROM session_notes
        WHERE project_name = ?
        ORDER BY created_at DESC
    """, (project_name,)).fetchall()
    conn.close()
    return rows


def get_project_config(project_name, show_secrets=False):
    conn = get_db()
    if show_secrets:
        rows = conn.execute("""
            SELECT key, value, is_secret FROM config
            WHERE project_name = ?
        """, (project_name,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT key, value, is_secret FROM config
            WHERE project_name = ? AND is_secret = 0
        """, (project_name,)).fetchall()
    conn.close()
    return rows


def get_backtest_history(project_name):
    conn = get_db()
    rows = conn.execute("""
        SELECT data_file, total_trades, win_rate, net_pnl, profit_factor, created_at
        FROM backtest_results
        WHERE project_name = ?
        ORDER BY created_at DESC
    """, (project_name,)).fetchall()
    conn.close()
    return rows


def get_todos(project_name, status=None):
    conn = get_db()
    if status:
        rows = conn.execute("""
            SELECT id, task, status, priority, created_at FROM todo
            WHERE project_name = ? AND status = ?
            ORDER BY priority DESC, created_at ASC
        """, (project_name, status)).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, task, status, priority, created_at FROM todo
            WHERE project_name = ?
            ORDER BY status ASC, priority DESC, created_at ASC
        """, (project_name,)).fetchall()
    conn.close()
    return rows


def show_session(project_name):
    print("\n" + "=" * 60)
    print(f"  SESSION: {project_name}")
    print("=" * 60)

    # Project info
    conn = get_db()
    project = conn.execute("SELECT * FROM projects WHERE name = ?", (project_name,)).fetchone()
    conn.close()

    if project:
        print(f"\n📁 Path: {project['path']}")
        print(f"📝 Description: {project['description']}")
        print(f"📅 Created: {project['created_at']}")

    # Notes
    notes = get_project_notes(project_name)
    if notes:
        print(f"\n📋 Notes ({len(notes)}):")
        for cat, note, created in notes:
            print(f"  [{cat}] {note[:80]}...")

    # Config
    config = get_project_config(project_name)
    if config:
        print(f"\n⚙️ Configuration:")
        for key, value, is_secret in config:
            display = "***" if is_secret else value[:50]
            print(f"  {key}: {display}")

    # Backtest
    backtests = get_backtest_history(project_name)
    if backtests:
        print(f"\n📊 Backtest History ({len(backtests)}):")
        for dt, trades, winrate, pnl, pf, created in backtests:
            print(f"  {created[:10]} | {trades} trades | {winrate}% win | {pnl:+.0f} pts | PF: {pf}")

    # Todos
    todos = get_todos(project_name)
    if todos:
        print(f"\n✅ Todo List ({len(todos)}):")
        for tid, task, status, pri, created in todos:
            check = "✅" if status == "completed" else "⬜"
            print(f"  {check} [{pri}] {task}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    import sys

    if "--show" in sys.argv:
        init_db()
        # Show all projects
        conn = get_db()
        projects = conn.execute("SELECT name FROM projects").fetchall()
        conn.close()
        for p in projects:
            show_session(p["name"])
    else:
        init_db()
