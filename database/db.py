"""
Smart Money Tracker — Database Operations
Async SQLite connection dan CRUD operations.
"""

import logging
import asyncio
from datetime import datetime, date
from typing import Optional

import aiosqlite

import config
from database.models import CREATE_TABLES_SQL, CLEANUP_SQL

logger = logging.getLogger(__name__)

# Global connection
_db: Optional[aiosqlite.Connection] = None


async def init_db():
    """Initialize database: create connection dan tables."""
    global _db
    _db = await aiosqlite.connect(config.DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.executescript(CREATE_TABLES_SQL)
    await _db.commit()
    logger.info(f"Database initialized at {config.DB_PATH}")


async def close_db():
    """Close database connection."""
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("Database connection closed")


async def get_db() -> aiosqlite.Connection:
    """Get database connection, initialize if needed."""
    global _db
    if _db is None:
        await init_db()
    return _db


# ──────────────────────────────────────────────
# Stock Data CRUD
# ──────────────────────────────────────────────
async def save_stock_data(
    ticker: str,
    trade_date: date,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: int,
):
    """Simpan atau update data OHLCV."""
    db = await get_db()
    await db.execute(
        """
        INSERT OR REPLACE INTO stock_data 
        (ticker, trade_date, open_price, high_price, low_price, close_price, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (ticker, trade_date.isoformat(), open_price, high_price, low_price, close_price, volume),
    )
    await db.commit()


async def get_stock_data(ticker: str, days: int = 30) -> list[dict]:
    """Get data OHLCV untuk ticker, N hari terakhir."""
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT * FROM stock_data 
        WHERE ticker = ? 
        ORDER BY trade_date DESC 
        LIMIT ?
        """,
        (ticker, days),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────
# Signals CRUD
# ──────────────────────────────────────────────
async def save_signal(signal, report_type: str = "scan"):
    """Simpan sinyal TA yang di-generate."""
    db = await get_db()
    # Gunakan field yang ada di TradingSignal
    await db.execute(
        """
        INSERT INTO signals
        (ticker, company_name, signal_date, status, score,
         entry_low, entry_high, take_profit_1, take_profit_2, stop_loss,
         risk_reward, rsi_value, macd_signal, bb_signal, adx_trend,
         volume_spike, candle_pattern,
         score_trend, score_momentum, score_volatility, score_volume,
         ai_analysis, report_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            signal.ticker, signal.company_name, date.today().isoformat(),
            signal.status, signal.score,
            signal.entry_low, signal.entry_high,
            signal.take_profit_1, signal.take_profit_2, signal.stop_loss,
            signal.risk_reward,
            signal.rsi_value, signal.macd_signal, signal.bb_signal, signal.adx_trend,
            signal.volume_spike, signal.candle_pattern,
            signal.score_trend, signal.score_momentum, signal.score_volatility, signal.score_volume,
            signal.ai_analysis, report_type,
        ),
    )
    await db.commit()


async def get_signals_today() -> list[dict]:
    """Get semua sinyal hari ini."""
    db = await get_db()
    today = date.today().isoformat()
    cursor = await db.execute(
        """
        SELECT * FROM signals
        WHERE signal_date = ?
        ORDER BY score DESC
        """,
        (today,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_signal_history(ticker: str, days: int = 30) -> list[dict]:
    """Get signal history untuk satu ticker."""
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT * FROM signals
        WHERE ticker = ?
        ORDER BY signal_date DESC
        LIMIT ?
        """,
        (ticker, days),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────
# Scan Log
# ──────────────────────────────────────────────
async def log_scan_start(scan_type: str) -> int:
    """Log mulai scan, return scan_id."""
    db = await get_db()
    cursor = await db.execute(
        """
        INSERT INTO scan_log (scan_type, started_at, status)
        VALUES (?, ?, 'running')
        """,
        (scan_type, datetime.now().isoformat()),
    )
    await db.commit()
    return cursor.lastrowid


async def log_scan_complete(
    scan_id: int, total_scanned: int, total_signals: int, error: str = None
):
    """Log scan selesai."""
    db = await get_db()
    status = "error" if error else "completed"
    await db.execute(
        """
        UPDATE scan_log
        SET total_scanned = ?, total_signals = ?, completed_at = ?, 
            status = ?, error_message = ?
        WHERE id = ?
        """,
        (total_scanned, total_signals, datetime.now().isoformat(), status, error, scan_id),
    )
    await db.commit()


# ──────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────
async def cleanup_old_data(days: int = None):
    """Hapus data yang lebih tua dari N hari."""
    if days is None:
        days = config.DATA_RETENTION_DAYS
    db = await get_db()
    cleanup_sql = CLEANUP_SQL.format(days=days)
    await db.executescript(cleanup_sql)
    await db.commit()
    logger.info(f"Cleaned up data older than {days} days")
