"""
Smart Money Tracker — Technical Analysis Indicators
Shared TA library untuk kalkulasi indikator teknikal.
Semua fungsi menerima DataFrame OHLCV dan mengembalikan Series/float.

Sumber data: yfinance (OHLCV) — GRATIS, REAL, tanpa scraping.
"""

import logging
from typing import Optional
from dataclasses import dataclass

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Moving Averages
# ──────────────────────────────────────────────

def sma(series: pd.Series, period: int = 20) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int = 20) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


# ──────────────────────────────────────────────
# RSI — Relative Strength Index
# ──────────────────────────────────────────────

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index.
    RSI > 70 = overbought (potensi turun)
    RSI < 30 = oversold (potensi naik)
    RSI 30-70 = normal
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Fill NaN dari diff pertama agar rolling window punya period non-NaN values
    gain.iloc[0] = 0.0
    loss.iloc[0] = 0.0

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Smoothed RSI (Wilder's method)
    for i in range(period, len(avg_gain)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period

    # Hindari division by zero: jika avg_loss = 0, RSI = 100
    avg_loss = avg_loss.clip(lower=1e-10)
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


# ──────────────────────────────────────────────
# MACD — Moving Average Convergence Divergence
# ──────────────────────────────────────────────

@dataclass
class MACDResult:
    """Hasil kalkulasi MACD."""
    macd_line: pd.Series       # MACD line (EMA12 - EMA26)
    signal_line: pd.Series     # Signal line (EMA9 dari MACD)
    histogram: pd.Series       # Histogram (MACD - Signal)
    crossover: str             # "BULLISH", "BEARISH", "NONE"


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> MACDResult:
    """
    MACD Indicator.
    - MACD line = EMA(fast) - EMA(slow)
    - Signal line = EMA(signal) of MACD line
    - Histogram = MACD line - Signal line
    
    Bullish crossover = MACD line crosses ABOVE signal line
    Bearish crossover = MACD line crosses BELOW signal line
    """
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)

    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line

    # Detect crossover
    crossover = "NONE"
    if len(macd_line) >= 2:
        prev_macd = macd_line.iloc[-2]
        prev_signal = signal_line.iloc[-2]
        curr_macd = macd_line.iloc[-1]
        curr_signal = signal_line.iloc[-1]

        if prev_macd <= prev_signal and curr_macd > curr_signal:
            crossover = "BULLISH"
        elif prev_macd >= prev_signal and curr_macd < curr_signal:
            crossover = "BEARISH"

    return MACDResult(
        macd_line=macd_line,
        signal_line=signal_line,
        histogram=histogram,
        crossover=crossover,
    )


# ──────────────────────────────────────────────
# Bollinger Bands
# ──────────────────────────────────────────────

@dataclass
class BollingerResult:
    """Hasil kalkulasi Bollinger Bands."""
    upper: pd.Series        # Upper band (SMA + k * std)
    middle: pd.Series       # Middle band (SMA)
    lower: pd.Series        # Lower band (SMA - k * std)
    bandwidth: pd.Series    # Bandwidth ((upper - lower) / middle)
    position: float         # Posisi harga terakhir di dalam bands (0-1)
    squeeze: bool           # Apakah bandwidth menyempit (squeeze)


def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> BollingerResult:
    """
    Bollinger Bands.
    - Middle = SMA(period)
    - Upper = Middle + k * std(period)
    - Lower = Middle - k * std(period)
    
    Squeeze = bandwidth mendekati minimum (indikasi breakout imminent)
    """
    middle = sma(series, period)
    std = series.rolling(window=period).std(ddof=0)

    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    bandwidth = (upper - lower) / middle

    # Posisi harga terakhir dalam bands (0 = lower, 1 = upper)
    current_price = series.iloc[-1]
    current_lower = lower.iloc[-1]
    current_upper = upper.iloc[-1]

    if current_upper != current_lower:
        position = (current_price - current_lower) / (current_upper - current_lower)
    else:
        position = 0.5

    # Squeeze detection: bandwidth < 20% dari rata-rata bandwidth 20 hari
    if len(bandwidth) >= 20:
        avg_bandwidth = bandwidth.iloc[-20:].mean()
        squeeze = bandwidth.iloc[-1] < avg_bandwidth * 0.8
    else:
        squeeze = False

    return BollingerResult(
        upper=upper,
        middle=middle,
        lower=lower,
        bandwidth=bandwidth,
        position=min(1.0, max(0.0, position)),
        squeeze=squeeze,
    )


# ──────────────────────────────────────────────
# ATR — Average True Range
# ──────────────────────────────────────────────

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range — mengukur volatilitas.
    ATR tinggi = volatilitas tinggi
    ATR rendah = volatilitas rendah
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.rolling(window=period).mean()


# ──────────────────────────────────────────────
# ADX — Average Directional Index
# ──────────────────────────────────────────────

@dataclass
class ADXResult:
    """Hasil kalkulasi ADX."""
    adx: pd.Series          # ADX value (0-100)
    plus_di: pd.Series      # +DI (positive directional)
    minus_di: pd.Series     # -DI (negative directional)
    trend: str              # "STRONG", "WEAK", "NONE"
    direction: str          # "BULLISH" (+DI > -DI), "BEARISH" (-DI > +DI)


def adx(df: pd.DataFrame, period: int = 14) -> ADXResult:
    """
    Average Directional Index — mengukur kekuatan trend.
    ADX > 25 = trend kuat
    ADX < 20 = ranging/weak trend
    +DI > -DI = bullish trend
    -DI > +DI = bearish trend
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    # True Range
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_series = true_range.rolling(window=period).mean()

    # Directional Movement
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=df.index)
    minus_dm = pd.Series(0.0, index=df.index)

    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move

    # Smoothed DM
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr_series.replace(0, np.nan))
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr_series.replace(0, np.nan))

    # ADX
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx_series = dx.rolling(window=period).mean()

    # Trend strength
    current_adx = adx_series.iloc[-1] if not pd.isna(adx_series.iloc[-1]) else 0
    if current_adx >= 25:
        trend = "STRONG"
    elif current_adx >= 20:
        trend = "MODERATE"
    else:
        trend = "WEAK"

    # Direction
    curr_plus = plus_di.iloc[-1] if not pd.isna(plus_di.iloc[-1]) else 0
    curr_minus = minus_di.iloc[-1] if not pd.isna(minus_di.iloc[-1]) else 0
    direction = "BULLISH" if curr_plus > curr_minus else "BEARISH"

    return ADXResult(
        adx=adx_series,
        plus_di=plus_di,
        minus_di=minus_di,
        trend=trend,
        direction=direction,
    )


# ──────────────────────────────────────────────
# Stochastic Oscillator
# ──────────────────────────────────────────────

@dataclass
class StochasticResult:
    """Hasil kalkulasi Stochastic."""
    k: pd.Series        # %K line (fast)
    d: pd.Series        # %D line (slow/signal)
    status: str         # "OVERBOUGHT", "OVERSOLD", "NORMAL"
    crossover: str      # "BULLISH", "BEARISH", "NONE"


def stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> StochasticResult:
    """
    Stochastic Oscillator.
    %K > 80 = overbought
    %K < 20 = oversold
    Bullish crossover = %K crosses above %D
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    low_min = low.rolling(window=k_period).min()
    high_max = high.rolling(window=k_period).max()

    k = 100 * ((close - low_min) / (high_max - low_min).replace(0, np.nan))
    d = k.rolling(window=d_period).mean()

    # Status
    curr_k = k.iloc[-1] if not pd.isna(k.iloc[-1]) else 50
    if curr_k >= 80:
        status = "OVERBOUGHT"
    elif curr_k <= 20:
        status = "OVERSOLD"
    else:
        status = "NORMAL"

    # Crossover
    crossover = "NONE"
    if len(k) >= 2:
        prev_k, curr_k = k.iloc[-2], k.iloc[-1]
        prev_d, curr_d = d.iloc[-2], d.iloc[-1]
        if prev_k <= prev_d and curr_k > curr_d:
            crossover = "BULLISH"
        elif prev_k >= prev_d and curr_k < curr_d:
            crossover = "BEARISH"

    return StochasticResult(k=k, d=d, status=status, crossover=crossover)


# ──────────────────────────────────────────────
# Support & Resistance
# ──────────────────────────────────────────────

@dataclass
class SupportResistanceResult:
    """Level support dan resistance."""
    support: float          # Support terdekat
    resistance: float       # Resistance terdekat
    support_strength: str   # "STRONG", "MODERATE", "WEAK"
    resistance_strength: str
    distance_to_support: float  # Jarak harga ke support (%)
    distance_to_resistance: float  # Jarak harga ke resistance (%)


def support_resistance(df: pd.DataFrame, lookback: int = 20) -> SupportResistanceResult:
    """
    Deteksi level support dan resistance sederhana.
    Menggunakan local minima/maxima dalam periode lookback.
    """
    high = df["High"].iloc[-lookback:]
    low = df["Low"].iloc[-lookback:]
    close = df["Close"].iloc[-1]

    # Cari swing highs dan swing lows
    highs_list = []
    lows_list = []

    for i in range(2, len(high) - 2):
        # Local high
        if (high.iloc[i] > high.iloc[i - 1] and
            high.iloc[i] > high.iloc[i - 2] and
            high.iloc[i] > high.iloc[i + 1] and
            high.iloc[i] > high.iloc[i + 2]):
            highs_list.append(high.iloc[i])

        # Local low
        if (low.iloc[i] < low.iloc[i - 1] and
            low.iloc[i] < low.iloc[i - 2] and
            low.iloc[i] < low.iloc[i + 1] and
            low.iloc[i] < low.iloc[i + 2]):
            lows_list.append(low.iloc[i])

    # Support = rata-rata dari swing lows terdekat di bawah harga
    supports_below = [l for l in lows_list if l < close]
    resistance_above = [h for h in highs_list if h > close]

    if supports_below:
        support = max(supports_below)  # Support terdekat
        # Hitung strength: berapa kali level ini disentuh
        touch_count = sum(1 for l in lows_list if abs(l - support) / support < 0.01)
        if touch_count >= 3:
            support_strength = "STRONG"
        elif touch_count >= 2:
            support_strength = "MODERATE"
        else:
            support_strength = "WEAK"
    else:
        support = low.min()
        support_strength = "WEAK"

    if resistance_above:
        resistance = min(resistance_above)  # Resistance terdekat
        touch_count = sum(1 for h in highs_list if abs(h - resistance) / resistance < 0.01)
        if touch_count >= 3:
            resistance_strength = "STRONG"
        elif touch_count >= 2:
            resistance_strength = "MODERATE"
        else:
            resistance_strength = "WEAK"
    else:
        resistance = high.max()
        resistance_strength = "WEAK"

    # Distance
    dist_to_support = ((close - support) / close) * 100 if support > 0 else 0
    dist_to_resistance = ((resistance - close) / close) * 100 if close > 0 else 0

    return SupportResistanceResult(
        support=support,
        resistance=resistance,
        support_strength=support_strength,
        resistance_strength=resistance_strength,
        distance_to_support=dist_to_support,
        distance_to_resistance=dist_to_resistance,
    )


# ──────────────────────────────────────────────
# VWAP — Volume Weighted Average Price
# ──────────────────────────────────────────────

def vwap(df: pd.DataFrame) -> pd.Series:
    """
    Volume Weighted Average Price.
    VWAP = kumulatif(Price * Volume) / kumulatif(Volume)
    
    Harga tinggi = VWAP di atas harga = bullish (harga di atas VWAP)
    Harga rendah = VWAP di bawah harga = bearish
    """
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    volume = df["Volume"]
    
    cum_vol_price = (typical_price * volume).cumsum()
    cum_volume = volume.cumsum()
    
    return cum_vol_price / cum_volume.replace(0, np.nan)


# ──────────────────────────────────────────────
# Auto-Fibonacci Retracement
# ──────────────────────────────────────────────

@dataclass
class FibonacciResult:
    """Level retracement Fibonacci."""
    high: float                # Swing high
    low: float                 # Swing low
    levels: dict               # {level_name: price}
    nearest_support: str       # Level Fibonacci terdekat di bawah harga
    nearest_resistance: str    # Level Fibonacci terdekat di atas harga


def auto_fibonacci(df: pd.DataFrame, lookback: int = 60) -> FibonacciResult:
    """
    Auto-Fibonacci retracement levels.
    Mencari swing high dan swing low dalam periode lookback,
    lalu menghitung level-level Fibonacci retracement.
    
    Level: 0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0
    """
    high = df["High"].iloc[-lookback:]
    low = df["Low"].iloc[-lookback:]
    close = df["Close"].iloc[-1]
    
    # Cari swing high dan swing low
    swing_highs = []
    swing_lows = []
    
    for i in range(2, len(high) - 2):
        if (high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and
            high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]):
            swing_highs.append(high.iloc[i])
        if (low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and
            low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]):
            swing_lows.append(low.iloc[i])
    
    # Ambil swing high tertinggi dan swing low terendah
    fib_high = max(swing_highs) if swing_highs else float(high.max())
    fib_low = min(swing_lows) if swing_lows else float(low.min())
    
    # Pastikan fib_high > fib_low
    if fib_high <= fib_low:
        fib_high = float(high.max())
        fib_low = float(low.min())
    
    range_price = fib_high - fib_low
    
    # Level Fibonacci standar
    fib_ratios = {
        "0.0%": 0.0,
        "23.6%": 0.236,
        "38.2%": 0.382,
        "50.0%": 0.5,
        "61.8%": 0.618,
        "78.6%": 0.786,
        "100%": 1.0,
    }
    
    levels = {}
    for name, ratio in fib_ratios.items():
        # Dari high ke low (uptrend retracement)
        price = fib_high - (range_price * ratio)
        levels[name] = round(price, 2)
    
    # Cari level support dan resistance terdekat
    nearest_support = "0.0%"
    nearest_resistance = "100%"
    min_dist_above = float('inf')
    min_dist_below = float('inf')
    
    for name, price in levels.items():
        if price > close:
            dist = price - close
            if dist < min_dist_above:
                min_dist_above = dist
                nearest_resistance = name
        elif price < close:
            dist = close - price
            if dist < min_dist_below:
                min_dist_below = dist
                nearest_support = name
    
    return FibonacciResult(
        high=fib_high,
        low=fib_low,
        levels=levels,
        nearest_support=nearest_support,
        nearest_resistance=nearest_resistance,
    )


# ──────────────────────────────────────────────
# Price Action Helpers
# ──────────────────────────────────────────────

def candle_pattern(df: pd.DataFrame) -> str:
    """
    Deteksi pola candle sederhana.
    Mengembalikan nama pola atau "NO_PATTERN".
    """
    if len(df) < 2:
        return "NO_PATTERN"

    last = df.iloc[-1]
    prev = df.iloc[-2]

    body = abs(last["Close"] - last["Open"])
    upper_wick = last["High"] - max(last["Close"], last["Open"])
    lower_wick = min(last["Close"], last["Open"]) - last["Low"]
    total_range = last["High"] - last["Low"]

    if total_range == 0:
        return "NO_PATTERN"

    body_ratio = body / total_range
    is_green = last["Close"] > last["Open"]

    # Bullish Engulfing
    prev_body = abs(prev["Close"] - prev["Open"])
    if (is_green and
        last["Open"] < prev["Close"] and
        last["Close"] > prev["Open"] and
        body > prev_body * 1.2):
        return "BULLISH_ENGULFING"

    # Bearish Engulfing
    if (not is_green and
        last["Open"] > prev["Close"] and
        last["Close"] < prev["Open"] and
        body > prev_body * 1.2):
        return "BEARISH_ENGULFING"

    # Doji (small body)
    if body_ratio < 0.1 and total_range > 0:
        if upper_wick > body * 2 and lower_wick > body * 2:
            return "DOJI"
        return "SPINNING_TOP"

    # Hammer (small body, long lower wick)
    if is_green and lower_wick > body * 2 and upper_wick < body * 0.5:
        return "HAMMER"

    # Shooting Star (small body, long upper wick)
    if not is_green and upper_wick > body * 2 and lower_wick < body * 0.5:
        return "SHOOTING_STAR"

    # Marubozu (no wick)
    if body_ratio > 0.95:
        return "MARUBOZU_GREEN" if is_green else "MARUBOZU_RED"

    return "NO_PATTERN"
