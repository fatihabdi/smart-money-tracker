"""
Smart Money Tracker — US Stock Scanner
Scan saham US menggunakan yfinance + shared TA indicators.

Scoring system (sama dengan IDX, total 100):
  - Trend (MACD, EMA, ADX): 30 pts
  - Momentum (RSI, Stochastic): 25 pts
  - Volume: 20 pts
  - Volatility/Price Action (BB, ATR, S/R): 25 pts
"""

import logging
import asyncio
from typing import Optional

import pandas as pd
import numpy as np

from analysis.idx_scanner import (
    TrendResult, MomentumResult, VolatilityResult, VolumeResult,
    TAResult,
    analyze_trend, analyze_momentum, analyze_volatility, analyze_volume_ta,
)
from data.yfinance_client import fetch_ohlcv, fetch_bulk_ohlcv
from data.finnhub_client import finnhub_client
from data.us_stocks import get_us_watchlist, get_us_tickers, get_us_company_name, get_us_sector

import config

logger = logging.getLogger(__name__)


def analyze_us_stock(ticker: str, df: pd.DataFrame) -> Optional[TAResult]:
    """
    Analisis TA lengkap untuk satu saham US.
    Menggunakan fungsi analisis yang sama dengan IDX (shared indicators).
    
    Args:
        ticker: Ticker US (e.g., 'AAPL')
        df: DataFrame OHLCV
    
    Returns:
        TAResult atau None jika data tidak cukup.
    """
    if df is None or len(df) < 20:
        logger.warning(f"{ticker}: Data tidak cukup ({len(df) if df is not None else 0} baris)")
        return None

    trend_result = analyze_trend(df)
    momentum_result = analyze_momentum(df)
    vol_result = analyze_volatility(df)
    volume_result = analyze_volume_ta(df)

    total = (trend_result.score + momentum_result.score +
             vol_result.score + volume_result.score)
    total = max(0, min(100, total))

    if total >= config.SCORE_STRONG_BUY:
        category = "STRONG_BUY"
    elif total >= config.SCORE_BUY:
        category = "BUY"
    elif total >= config.SCORE_NEUTRAL:
        category = "NEUTRAL"
    else:
        category = "SELL"

    summary_parts = []
    if trend_result.adx_trend == "STRONG":
        summary_parts.append(f"Trend {trend_result.adx_direction} kuat")
    if momentum_result.rsi_status == "OVERSOLD":
        summary_parts.append("RSI oversold")
    elif momentum_result.rsi_status == "OVERBOUGHT":
        summary_parts.append("RSI overbought")
    if volume_result.is_spike:
        summary_parts.append(f"Volume spike {volume_result.spike_ratio}x")
    if vol_result.bb_signal == "BOUNCE":
        summary_parts.append("Harga di lower BB")
    summary = " | ".join(summary_parts) if summary_parts else "Tidak ada sinyal signifikan"

    return TAResult(
        ticker=ticker,
        company_name=get_us_company_name(ticker),
        current_price=float(df["Close"].iloc[-1]),
        total_score=total,
        category=category,
        trend=trend_result,
        momentum=momentum_result,
        volatility=vol_result,
        volume=volume_result,
        summary=summary,
    )


async def scan_single_us_stock(ticker: str) -> tuple[Optional[TAResult], Optional[pd.DataFrame]]:
    """
    Scan satu saham US: fetch data dari yfinance + analisis TA.
    
    Args:
        ticker: Ticker US (e.g., 'AAPL')
    
    Returns:
        Tuple (TAResult, DataFrame) atau (None, None) jika gagal.
    """
    # 100+ candles untuk TA lebih akurat (US market 252 hari/tahun)
    df = await fetch_ohlcv(ticker, period="6mo")

    if df is None or df.empty:
        logger.warning(f"No data for {ticker} from yfinance")
        return None, None

    result = analyze_us_stock(ticker, df)
    return result, df


async def scan_full_us_watchlist() -> list[tuple[TAResult, pd.DataFrame]]:
    """
    Scan semua saham di US watchlist via yfinance.
    
    Returns:
        List of (TAResult, DataFrame) sorted by score (highest first).
    """
    tickers = get_us_tickers()
    logger.info(f"Scanning {len(tickers)} US stocks with yfinance + TA...")

    # 100+ candles untuk TA lebih akurat
    ohlcv_data = await fetch_bulk_ohlcv(tickers, period="6mo")

    results = []
    for ticker in tickers:
        df = ohlcv_data.get(ticker)
        if df is not None and not df.empty:
            result = analyze_us_stock(ticker, df)
            if result:
                results.append((result, df))

    results.sort(key=lambda r: r[0].total_score, reverse=True)
    logger.info(f"US TA scan complete: {len(results)} stocks analyzed")
    return results
