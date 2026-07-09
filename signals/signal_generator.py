"""
Smart Money Tracker — Signal Generator
Generate sinyal trading berdasarkan TA Score.
Hitung entry area, TP, SL, dan R:R ratio.

Tidak lagi bergantung pada data broker/foreign flow dari IDX.
Semua indikator berasal dari OHLCV (yfinance) melalui TA library.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import numpy as np

import config
from analysis.scoring import SignalResult
from data.stock_list import get_company_name

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """Sinyal trading lengkap (berbasis TA)."""
    ticker: str
    company_name: str
    status: str                    # STRONG_BUY / BUY / NEUTRAL / SELL
    score: float                   # TA score (0-100)

    # Price data
    current_price: float = 0
    entry_low: float = 0
    entry_high: float = 0
    take_profit_1: float = 0
    take_profit_2: float = 0
    stop_loss: float = 0
    risk_reward: float = 0

    # TP/SL percentages
    tp1_pct: float = 0
    tp2_pct: float = 0
    sl_pct: float = 0

    # TA Signals (menggantikan foreign flow & broker)
    rsi_value: float = 0
    rsi_status: str = ""
    macd_signal: str = ""
    bb_signal: str = ""
    bb_position: float = 0
    adx_trend: str = ""
    adx_direction: str = ""
    stochastic_status: str = ""
    candle_pattern: str = ""
    volume_spike: float = 0
    volume_trend: str = ""
    support: float = 0
    resistance: float = 0

    # Score breakdown
    score_trend: float = 0
    score_momentum: float = 0
    score_volatility: float = 0
    score_volume: float = 0

    # AI
    ai_analysis: str = ""

    # Detail
    trend_detail: str = ""
    momentum_detail: str = ""
    volatility_detail: str = ""
    volume_detail: str = ""
    summary: str = ""


def generate_signal(
    ticker: str,
    signal_result: SignalResult,
) -> Optional[TradingSignal]:
    """
    Generate sinyal trading dari SignalResult (hasil TA scoring).
    Hanya generate jika score >= MIN_SIGNAL_SCORE.
    """
    if signal_result.total_score < config.MIN_SIGNAL_SCORE:
        logger.info(f"{ticker}: Score {signal_result.total_score:.0f} < {config.MIN_SIGNAL_SCORE}, skipping")
        return None

    current_price = signal_result.current_price
    entry_mid = (signal_result.entry_low + signal_result.entry_high) / 2

    # TP/SL percentages
    tp1_pct = round(((signal_result.take_profit_1 - entry_mid) / entry_mid) * 100, 1) if entry_mid > 0 else 0
    tp2_pct = round(((signal_result.take_profit_2 - entry_mid) / entry_mid) * 100, 1) if entry_mid > 0 else 0
    sl_pct = round(((entry_mid - signal_result.stop_loss) / entry_mid) * 100, 1) if entry_mid > 0 else 0

    # Map category
    status = signal_result.category  # STRONG_BUY, BUY, NEUTRAL, SELL

    signal = TradingSignal(
        ticker=ticker,
        company_name=signal_result.company_name,
        status=status,
        score=signal_result.total_score,
        current_price=current_price,
        entry_low=signal_result.entry_low,
        entry_high=signal_result.entry_high,
        take_profit_1=signal_result.take_profit_1,
        take_profit_2=signal_result.take_profit_2,
        stop_loss=signal_result.stop_loss,
        risk_reward=signal_result.risk_reward,
        tp1_pct=tp1_pct,
        tp2_pct=tp2_pct,
        sl_pct=sl_pct,
        score_trend=signal_result.breakdown.trend,
        score_momentum=signal_result.breakdown.momentum,
        score_volatility=signal_result.breakdown.volatility,
        score_volume=signal_result.breakdown.volume,
        trend_detail=signal_result.trend,
        momentum_detail=signal_result.momentum,
        volatility_detail=signal_result.volatility,
        volume_detail=signal_result.volume_detail,
        summary=signal_result.summary,
    )

    logger.info(
        f"Signal: {ticker} | Score: {signal.score:.0f} | "
        f"Status: {signal.status} | Entry: {signal.entry_low}-{signal.entry_high} | "
        f"R:R: 1:{signal.risk_reward}"
    )

    return signal


def generate_bulk_signals(
    scan_results: list[tuple[str, SignalResult]],
) -> list[TradingSignal]:
    """
    Generate sinyal untuk banyak saham.
    
    Args:
        scan_results: List of (ticker, SignalResult)
    
    Returns:
        List of TradingSignal, sorted by score (highest first).
    """
    signals = []
    for ticker, result in scan_results:
        signal = generate_signal(ticker, result)
        if signal is not None:
            signals.append(signal)

    signals.sort(key=lambda s: s.score, reverse=True)
    logger.info(f"Generated {len(signals)} signals from {len(scan_results)} scans")
    return signals


def round_to_tick(price: float) -> float:
    """
    Round harga ke tick size IDX.
    Tick size rules (per Jan 2024):
    - Harga < 200: tick 1
    - Harga 200-500: tick 2
    - Harga 500-2000: tick 5
    - Harga 2000-5000: tick 10
    - Harga > 5000: tick 25
    """
    if price < 200:
        tick = 1
    elif price < 500:
        tick = 2
    elif price < 2000:
        tick = 5
    elif price < 5000:
        tick = 10
    else:
        tick = 25
    return round(price / tick) * tick
