"""
Smart Money Tracker — Configuration
Konfigurasi utama, constants, dan environment variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ──────────────────────────────────────────────
# Telegram Configuration
# ──────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ──────────────────────────────────────────────
# Gemini AI Configuration
# ──────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"  # Free tier model
GEMINI_MAX_REQUESTS_PER_MINUTE = 10

# ──────────────────────────────────────────────
# Timezone & Schedule
# ──────────────────────────────────────────────
TIMEZONE = "Asia/Jakarta"  # WIB (UTC+7)

# Jadwal sinyal IDX (jam, menit) — WIB
SCHEDULE_PRE_MARKET = (8, 30)    # 08:30 WIB — Pre-Market Watchlist
SCHEDULE_POST_MARKET = (16, 30)  # 16:30 WIB — Post-Market Report (swing trade)

# Jadwal sinyal US (jam, menit) — WIB
# US market: Pre 04:00-09:30 ET | Open 09:30 ET | Close 16:00 ET
# Konversi ke WIB (+11 jam): Pre 15:00-20:30 | Open 20:30 | Close 03:00+1
US_SCHEDULE_PRE_MARKET = (19, 30)    # 19:30 WIB = 08:30 ET (pre-market analysis)
US_SCHEDULE_POST_OPEN = (21, 30)     # 21:30 WIB = 10:30 ET (1 jam after open)
US_SCHEDULE_MID_SESSION = (0, 30)    # 00:30 WIB = 13:30 ET (mid-session)

# ──────────────────────────────────────────────
# Trading Parameters
# ──────────────────────────────────────────────
TP_PERCENT_1 = 10.0   # TP1: +10%
TP_PERCENT_2 = 20.0   # TP2: +20%
SL_PERCENT = 5.0      # SL: -5%
MIN_RR_RATIO = 2.0    # Minimum Risk:Reward ratio
ENTRY_BUFFER_PERCENT = 2.0  # Buffer 2% dari support

# ──────────────────────────────────────────────
# TA Scoring Parameters (total: 100)
# ──────────────────────────────────────────────
SCORE_TREND_MAX = 30      # Max score untuk trend (MACD, EMA, ADX)
SCORE_MOMENTUM_MAX = 25   # Max score untuk momentum (RSI, Stochastic)
SCORE_VOLATILITY_MAX = 25 # Max score untuk volatility (Bollinger, ATR, S/R)
SCORE_VOLUME_MAX = 20     # Max score untuk volume

# Threshold kategori sinyal
SCORE_STRONG_BUY = 75     # Score >= 75 = Strong Buy
SCORE_BUY = 55            # Score >= 55 = Buy
SCORE_NEUTRAL = 35        # Score >= 35 = Neutral
# Score < 35 = Sell

# Minimum score untuk generate sinyal
MIN_SIGNAL_SCORE = 55

# ──────────────────────────────────────────────
# Technical Analysis Parameters
# ──────────────────────────────────────────────
# RSI
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_PERIOD = 14

# MACD
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Bollinger Bands
BB_PERIOD = 20
BB_STD_DEV = 2.0

# ADX
ADX_PERIOD = 14
ADX_STRONG = 25

# ATR
ATR_PERIOD = 14

# Stochastic
STOCH_K_PERIOD = 14
STOCH_D_PERIOD = 3

# Volume
VOLUME_AVG_DAYS = 20
VOLUME_SPIKE_THRESHOLD = 2.0

# Support/Resistance
SR_LOOKBACK = 20

# ──────────────────────────────────────────────
# Data Collection
# ──────────────────────────────────────────────
YFINANCE_PERIOD = "2mo"       # Download 2 bulan data (untuk EMA50, ADX)
YFINANCE_INTERVAL = "1d"      # Interval harian

# US Data Collection
US_CANDLES_COUNT = 100        # 100 candle OHLCV untuk US stocks

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "tracking.db")
DATA_RETENTION_DAYS = 60

# ──────────────────────────────────────────────
# Finnhub API (US Stocks)
# ──────────────────────────────────────────────
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# US market schedules (Eastern Time)
US_PRE_MARKET = (9, 0)     # 09:00 ET — Pre-market setup
US_MARKET_OPEN = (9, 30)   # 09:30 ET — Market open scan
US_MARKET_CLOSE = (16, 0)  # 16:00 ET — Market close scan

# US watchlist
US_SCAN_INTERVAL_MINUTES = 60  # Scan ulang setiap 60 menit selama market hours

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
