"""
Smart Money Tracker — IDX Scanner
Scan saham IDX menggunakan Technical Analysis murni (yfinance + TA indicators).
Tanpa broker flow / foreign flow — semua data dari OHLCV gratis.

Scoring system (total 100):
  - Trend (MACD, EMA, ADX): 30 pts
  - Momentum (RSI, Stochastic): 25 pts
  - Volume: 20 pts
  - Volatility/Price Action (BB, ATR, S/R): 25 pts
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import numpy as np

from analysis.indicators import (
    rsi, macd, bollinger_bands, atr, adx, stochastic,
    support_resistance, candle_pattern, sma, ema, MACDResult,
    BollingerResult, ADXResult, StochasticResult, SupportResistanceResult,
)
from data.yfinance_client import fetch_ohlcv, fetch_bulk_ohlcv
from data.stock_list import get_watchlist, get_yf_ticker, get_company_name

import config

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Result Data Classes
# ──────────────────────────────────────────────

@dataclass
class TrendResult:
    """Hasil analisis trend."""
    macd_crossover: str          # "BULLISH", "BEARISH", "NONE"
    macd_histogram: float        # Nilai histogram MACD terakhir
    ema_short: float             # EMA20
    ema_long: float              # EMA50
    ema_position: str            # "ABOVE", "BELOW", "CROSSED"
    adx_trend: str               # "STRONG", "MODERATE", "WEAK"
    adx_direction: str           # "BULLISH", "BEARISH"
    score: float                 # 0-30
    detail: str = ""



@dataclass
class MomentumResult:
    """Hasil analisis momentum."""
    rsi_value: float             # RSI terakhir
    rsi_status: str              # "OVERSOLD", "OVERBOUGHT", "NORMAL"
    stochastic_status: str       # "OVERSOLD", "OVERBOUGHT", "NORMAL"
    stochastic_crossover: str    # "BULLISH", "BEARISH", "NONE"
    score: float                 # 0-25
    detail: str = ""


@dataclass
class VolatilityResult:
    """Hasil analisis volatilitas dan price action."""
    bb_position: float           # 0 (lower) - 1 (upper)
    bb_squeeze: bool             # Apakah Bollinger squeeze
    bb_signal: str               # "BOUNCE", "BREAKOUT", "NORMAL"
    atr_value: float             # ATR terakhir
    pattern: str                 # Candlestick pattern
    support: float               # Level support
    resistance: float            # Level resistance
    score: float                 # 0-25
    detail: str = ""


@dataclass
class VolumeResult:
    """Hasil analisis volume."""
    spike_ratio: float           # Volume / rata-rata 20 hari
    is_spike: bool
    volume_trend: str            # "INCREASING", "DECREASING", "STABLE"
    obv_trend: str               # On-Balance Volume trend
    score: float                 # 0-20
    detail: str = ""


@dataclass
class TAResult:
    """Hasil analisis TA gabungan."""
    ticker: str
    company_name: str
    current_price: float
    total_score: float           # 0-100
    category: str                # STRONG_BUY, BUY, NEUTRAL, SELL
    trend: TrendResult
    momentum: MomentumResult
    volatility: VolatilityResult
    volume: VolumeResult
    summary: str = ""


# ──────────────────────────────────────────────
# Analysis Functions
# ──────────────────────────────────────────────

def analyze_trend(df: pd.DataFrame) -> TrendResult:
    """
    Analisis trend menggunakan MACD, EMA crossover, ADX.
    Score: 0-30
    """
    score = 0.0
    details = []
    closes = df["Close"]

    # 1. MACD Crossover (max 10 pts)
    macd_result = macd(closes)
    if macd_result.crossover == "BULLISH":
        score += 10
        details.append("MACD bullish crossover")
    elif macd_result.crossover == "BEARISH":
        score -= 5
        details.append("MACD bearish crossover")
    elif macd_result.macd_line.iloc[-1] > macd_result.signal_line.iloc[-1]:
        score += 5
        details.append("MACD di atas signal line (bullish)")

    # 2. EMA Position (max 10 pts)
    ema20 = ema(closes, 20).iloc[-1]
    ema50 = ema(closes, 50).iloc[-1] if len(closes) >= 50 else ema(closes, 20).iloc[-1]
    current_price = closes.iloc[-1]

    if current_price > ema20 > ema50:
        score += 10
        details.append("Harga > EMA20 > EMA50 (bullish alignment)")
    elif current_price > ema20:
        score += 5
        details.append("Harga di atas EMA20")
    elif current_price < ema20 and current_price > ema50:
        score += 2
        details.append("Harga di antara EMA20 dan EMA50")
    else:
        score -= 3
        details.append("Harga di bawah EMA50 (bearish)")

    ema_position = "ABOVE" if current_price > ema20 else "BELOW"

    # 3. ADX (max 10 pts)
    if len(df) >= 30:
        adx_result = adx(df)
        if adx_result.trend == "STRONG" and adx_result.direction == "BULLISH":
            score += 10
            details.append(f"ADX kuat ({adx_result.adx.iloc[-1]:.1f}), bullish")
        elif adx_result.trend == "STRONG" and adx_result.direction == "BEARISH":
            score += 3
            details.append(f"ADX kuat ({adx_result.adx.iloc[-1]:.1f}), bearish (hati-hati)")
        elif adx_result.trend == "MODERATE" and adx_result.direction == "BULLISH":
            score += 6
            details.append("ADX moderate, bullish")
        elif adx_result.trend == "WEAK":
            score += 2
            details.append("ADX weak (ranging market)")
    else:
        adx_result = None

    score = max(-5, min(30, score))

    return TrendResult(
        macd_crossover=macd_result.crossover,
        macd_histogram=float(macd_result.histogram.iloc[-1]),
        ema_short=float(ema20),
        ema_long=float(ema50),
        ema_position=ema_position,
        adx_trend=adx_result.trend if adx_result else "NONE",
        adx_direction=adx_result.direction if adx_result else "NONE",
        score=score,
        detail=" | ".join(details),
    )


def analyze_momentum(df: pd.DataFrame) -> MomentumResult:
    """
    Analisis momentum menggunakan RSI dan Stochastic.
    Score: 0-25
    """
    score = 0.0
    details = []
    closes = df["Close"]

    # 1. RSI (max 15 pts)
    rsi_series = rsi(closes)
    rsi_val = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50

    if rsi_val < 30:
        score += 15
        details.append(f"RSI {rsi_val:.1f} (oversold — potensi bounce)")
        rsi_status = "OVERSOLD"
    elif rsi_val < 40:
        score += 10
        details.append(f"RSI {rsi_val:.1f} (mendekati oversold)")
        rsi_status = "OVERSOLD"
    elif rsi_val > 70:
        score -= 5
        details.append(f"RSI {rsi_val:.1f} (overbought — hati-hati)")
        rsi_status = "OVERBOUGHT"
    elif rsi_val > 60:
        score += 5
        details.append(f"RSI {rsi_val:.1f} (mendekati overbought)")
        rsi_status = "NORMAL"
    elif rsi_val > 40:
        score += 8
        details.append(f"RSI {rsi_val:.1f} (netral, bullish bias)")
        rsi_status = "NORMAL"
    else:
        score += 3
        details.append(f"RSI {rsi_val:.1f} (netral)")
        rsi_status = "NORMAL"

    # 2. Stochastic (max 10 pts)
    if len(df) >= 15:
        stoch = stochastic(df)
        stoch_status = stoch.status
        if stoch.status == "OVERSOLD" and stoch.crossover == "BULLISH":
            score += 10
            details.append("Stochastic oversold + bullish crossover")
        elif stoch.status == "OVERSOLD":
            score += 6
            details.append("Stochastic oversold")
        elif stoch.status == "OVERBOUGHT" and stoch.crossover == "BEARISH":
            score -= 3
            details.append("Stochastic overbought + bearish crossover")
        elif stoch.status == "OVERBOUGHT":
            score -= 1
            details.append("Stochastic overbought")
        else:
            score += 4
            details.append(f"Stochastic normal ({float(stoch.k.iloc[-1]):.1f})")
    else:
        stoch_status = "NORMAL"
        stoch_crossover = "NONE"

    score = max(-5, min(25, score))

    return MomentumResult(
        rsi_value=round(rsi_val, 1),
        rsi_status=rsi_status,
        stochastic_status=stoch_status if len(df) >= 15 else "NORMAL",
        stochastic_crossover=stoch.crossover if len(df) >= 15 else "NONE",
        score=score,
        detail=" | ".join(details),
    )


def analyze_volatility(df: pd.DataFrame) -> VolatilityResult:
    """
    Analisis volatilitas menggunakan Bollinger Bands, ATR, Price Action.
    Score: 0-25
    """
    score = 0.0
    details = []
    closes = df["Close"]
    current_price = float(closes.iloc[-1])

    # 1. Bollinger Bands (max 12 pts)
    if len(df) >= 20:
        bb = bollinger_bands(closes)
        bb_signal = "NORMAL"

        if bb.position <= 0.05:
            # Price near lower band — potential bounce
            score += 10
            bb_signal = "BOUNCE"
            details.append(f"Harga di lower BB (posisi {bb.position:.0%})")
        elif bb.position <= 0.2:
            score += 6
            bb_signal = "BOUNCE"
            details.append(f"Harga mendekati lower BB (posisi {bb.position:.0%})")
        elif bb.position >= 0.95:
            bb_signal = "BREAKOUT"
            score += 3
            details.append(f"Harga di upper BB (posisi {bb.position:.0%})")
        elif bb.squeeze:
            score += 2
            bb_signal = "NORMAL"
            details.append("Bollinger squeeze — potensi breakout")

        # Sudah di-handle di atas dengan bonus score

    else:
        bb = None
        bb_signal = "NORMAL"

    # 2. Candlestick Pattern (max 8 pts)
    pattern = candle_pattern(df)
    if pattern in ("BULLISH_ENGULFING", "HAMMER"):
        score += 8
        details.append(f"Pola {pattern} (bullish)")
    elif pattern in ("BEARISH_ENGULFING", "SHOOTING_STAR"):
        score -= 3
        details.append(f"Pola {pattern} (bearish)")
    elif pattern in ("DOJI", "SPINNING_TOP"):
        score += 1
        details.append(f"Pola {pattern} (indecision)")

    # 3. Support/Resistance (max 5 pts)
    if len(df) >= 10:
        sr = support_resistance(df)
        if sr.distance_to_support < 3:
            score += 5
            details.append(f"Dekat support (jarak {sr.distance_to_support:.1f}%) — potensi bounce")
        elif sr.distance_to_resistance < 3:
            score += 2
            details.append(f"Dekat resistance (jarak {sr.distance_to_resistance:.1f}%) — hati-hati")
    else:
        sr = None

    score = max(-5, min(25, score))

    return VolatilityResult(
        bb_position=bb.position if bb else 0.5,
        bb_squeeze=bb.squeeze if bb else False,
        bb_signal=bb_signal,
        atr_value=float(atr(df).iloc[-1]) if len(df) >= 14 else 0,
        pattern=pattern,
        support=sr.support if sr else 0,
        resistance=sr.resistance if sr else 0,
        score=score,
        detail=" | ".join(details),
    )


def analyze_volume_ta(df: pd.DataFrame) -> VolumeResult:
    """
    Analisis volume (diperkuat dari volume_analysis.py).
    Score: 0-20
    """
    score = 0.0
    details = []

    if df is None or len(df) < 5:
        return VolumeResult(spike_ratio=0, is_spike=False, volume_trend="STABLE",
                            obv_trend="NONE", score=0, detail="Data tidak cukup")

    volumes = df["Volume"].values.astype(float)
    closes = df["Close"].values.astype(float)

    # 1. Volume spike (max 8 pts)
    lookback = min(20, len(volumes))
    avg_vol = float(np.mean(volumes[-lookback:]))
    current_vol = float(volumes[-1])
    spike_ratio = current_vol / avg_vol if avg_vol > 0 else 0

    if spike_ratio >= 3.0:
        score += 8
        details.append(f"Volume spike {spike_ratio:.1f}x (signifikan)")
    elif spike_ratio >= 2.0:
        score += 6
        details.append(f"Volume spike {spike_ratio:.1f}x")
    elif spike_ratio >= 1.5:
        score += 3
        details.append(f"Volume di atas rata-rata ({spike_ratio:.1f}x)")

    # 2. Volume trend (max 6 pts)
    if len(volumes) >= 10:
        recent_avg = float(np.mean(volumes[-5:]))
        prior_avg = float(np.mean(volumes[-10:-5]))
        if prior_avg > 0:
            vol_change = (recent_avg - prior_avg) / prior_avg
            if vol_change > 0.3:
                volume_trend = "INCREASING"
                score += 6
                details.append("Volume trend meningkat")
            elif vol_change < -0.3:
                volume_trend = "DECREASING"
                score -= 2
                details.append("Volume trend menurun")
            else:
                volume_trend = "STABLE"
                score += 2
                details.append("Volume stabil")
        else:
            volume_trend = "STABLE"
    else:
        volume_trend = "STABLE"

    # 3. On-Balance Volume sederhana (max 6 pts)
    if len(closes) >= 5 and len(volumes) >= 5:
        # Price-volume confirmation
        price_change_5d = (closes[-1] - closes[-5]) / closes[-5] * 100
        vol_avg_5d = float(np.mean(volumes[-5:]))

        bullish = price_change_5d > 0 and vol_avg_5d > avg_vol
        bearish = price_change_5d < 0 and vol_avg_5d > avg_vol
        distribution = price_change_5d < 0 and vol_avg_5d > avg_vol * 1.2

        if bullish:
            score += 6
            obv_trend = "BULLISH"
            details.append("Price-volume confirmation (bullish)")
        elif bearish and distribution:
            score -= 3
            obv_trend = "BEARISH"
            details.append("Distribusi (harga turun, volume tinggi)")
        elif bearish:
            obv_trend = "BEARISH"
            details.append("Harga turun, volume sedang")
        else:
            obv_trend = "NEUTRAL"
    else:
        obv_trend = "NONE"

    score = max(0, min(20, score))

    return VolumeResult(
        spike_ratio=round(spike_ratio, 2),
        is_spike=spike_ratio >= config.VOLUME_SPIKE_THRESHOLD,
        volume_trend=volume_trend,
        obv_trend=obv_trend,
        score=score,
        detail=" | ".join(details),
    )


# ──────────────────────────────────────────────
# Main Analysis Functions
# ──────────────────────────────────────────────

def analyze_stock(ticker: str, df: pd.DataFrame) -> Optional[TAResult]:
    """
    Analisis TA lengkap untuk satu saham.
    
    Args:
        ticker: Kode IDX (e.g., 'BBCA')
        df: DataFrame OHLCV
    
    Returns:
        TAResult atau None jika data tidak cukup.
    """
    if df is None or len(df) < 20:
        logger.warning(f"{ticker}: Data tidak cukup ({len(df) if df is not None else 0} baris)")
        return None

    # Analisis per komponen
    trend_result = analyze_trend(df)
    momentum_result = analyze_momentum(df)
    vol_result = analyze_volatility(df)
    volume_result = analyze_volume_ta(df)

    # Total score
    total = (trend_result.score + momentum_result.score +
             vol_result.score + volume_result.score)

    # Normalisasi ke 0-100
    total = max(0, min(100, total))

    # Kategori
    if total >= config.SCORE_STRONG_BUY:
        category = "STRONG_BUY"
    elif total >= config.SCORE_BUY:
        category = "BUY"
    elif total >= config.SCORE_NEUTRAL:
        category = "NEUTRAL"
    else:
        category = "SELL"

    # Summary
    summary_parts = []
    if trend_result.adx_trend == "STRONG":
        summary_parts.append(f"Trend {trend_result.adx_direction} kuat")
    if momentum_result.rsi_status == "OVERSOLD" and trend_result.score > 10:
        summary_parts.append("RSI oversold + trend bullish")
    else:
        summary_parts.append(f"RSI {momentum_result.rsi_value}")
    if volume_result.is_spike:
        summary_parts.append(f"Volume spike {volume_result.spike_ratio}x")
    if vol_result.bb_signal == "BOUNCE":
        summary_parts.append("Harga di lower BB (potensi bounce)")
    if vol_result.pattern in ("BULLISH_ENGULFING", "HAMMER"):
        summary_parts.append(f"Pola {vol_result.pattern}")

    summary = " | ".join(summary_parts) if summary_parts else "Tidak ada sinyal signifikan"

    return TAResult(
        ticker=ticker,
        company_name=get_company_name(ticker),
        current_price=float(df["Close"].iloc[-1]),
        total_score=total,
        category=category,
        trend=trend_result,
        momentum=momentum_result,
        volatility=vol_result,
        volume=volume_result,
        summary=summary,
    )


async def scan_single_stock(ticker: str) -> Optional[TAResult]:
    """
    Scan satu saham IDX: fetch data + analisis TA.
    
    Args:
        ticker: Kode IDX (e.g., 'BBCA')
    
    Returns:
        TAResult atau None.
    """
    yf_ticker = get_yf_ticker(ticker)
    df = await fetch_ohlcv(yf_ticker, period="2mo")

    if df is None or df.empty:
        logger.warning(f"No data for {ticker}")
        return None

    return analyze_stock(ticker, df)


async def scan_full_watchlist() -> list[TAResult]:
    """
    Scan semua saham di watchlist LQ45.
    
    Returns:
        List of TAResult sorted by score (highest first).
    """
    watchlist = get_watchlist()
    tickers = [code for _, code, _ in watchlist]
    yf_tickers = [get_yf_ticker(code) for code in tickers]

    logger.info(f"Scanning {len(tickers)} IDX stocks with TA...")

    # Fetch all OHLCV data
    ohlcv_data = await fetch_bulk_ohlcv(yf_tickers, period="2mo")

    # Analyze each stock
    results = []
    for _, code, _ in watchlist:
        yf_t = get_yf_ticker(code)
        df = ohlcv_data.get(yf_t)
        if df is not None and not df.empty:
            result = analyze_stock(code, df)
            if result:
                results.append(result)

    # Sort by score descending
    results.sort(key=lambda r: r.total_score, reverse=True)

    logger.info(f"TA scan complete: {len(results)} stocks analyzed")
    return results
