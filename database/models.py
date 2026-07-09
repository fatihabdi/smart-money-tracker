"""
Smart Money Tracker — Database Models
Definisi tabel SQLite untuk menyimpan data historis.

Tidak lagi menyimpan foreign flow / broker data.
Fokus: OHLCV cache, TA signals, scan log.
"""

CREATE_TABLES_SQL = """
-- Tabel: Cache data OHLCV dari yFinance
CREATE TABLE IF NOT EXISTS stock_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(ticker, trade_date)
);

-- Tabel: Generated TA signals log
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    company_name TEXT,
    signal_date TEXT NOT NULL,
    status TEXT,                     -- STRONG_BUY, BUY, NEUTRAL, SELL
    score REAL,
    entry_low REAL,
    entry_high REAL,
    take_profit_1 REAL,
    take_profit_2 REAL,
    stop_loss REAL,
    risk_reward REAL,

    -- TA Metrics
    rsi_value REAL,
    macd_signal TEXT,
    bb_signal TEXT,
    adx_trend TEXT,
    volume_spike REAL,
    candle_pattern TEXT,

    -- Score breakdown
    score_trend REAL,
    score_momentum REAL,
    score_volatility REAL,
    score_volume REAL,

    -- AI
    ai_analysis TEXT,
    report_type TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Tabel: Scan execution log
CREATE TABLE IF NOT EXISTS scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_type TEXT NOT NULL,          -- pre_market, post_market, manual
    source TEXT DEFAULT 'TA',         -- TA, US, etc
    total_scanned INTEGER DEFAULT 0,
    total_signals INTEGER DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    status TEXT DEFAULT 'running',
    error_message TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_stock_data_ticker_date ON stock_data(ticker, trade_date);
CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(signal_date);
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker);
CREATE INDEX IF NOT EXISTS idx_scan_log_date ON scan_log(started_at);
"""

CLEANUP_SQL = """
DELETE FROM stock_data WHERE created_at < datetime('now', '-{days} days');
DELETE FROM signals WHERE created_at < datetime('now', '-{days} days');
DELETE FROM scan_log WHERE started_at < datetime('now', '-{days} days');
"""
