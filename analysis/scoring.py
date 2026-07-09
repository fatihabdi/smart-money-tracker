"""
Smart Money Tracker — TA Scoring Engine
Menggabungkan semua analisis TA (trend, momentum, volatility, volume)
menjadi satu score 0-100 untuk deteksi sinyal trading.

Menggantikan smart_money.py yang lama (bergantung pada broker/foreign flow dari IDX).
"""

import logging
from dataclasses import dataclass, field

from analysis.idx_scanner import TAResult, TrendResult, MomentumResult, VolatilityResult, VolumeResult
from analysis.indicators import candle_pattern

import config

logger = logging.getLogger(__name__)


@dataclass
class ScoreBreakdown:
    """Breakdown skor per komponen TA."""
    trend: float = 0       # MACD, EMA, ADX (0-30)
    momentum: float = 0    # RSI, Stochastic (0-25)
    volatility: float = 0  # Bollinger, ATR, S/R (0-25)
    volume: float = 0      # Volume analysis (0-20)


@dataclass
class SignalResult:
    """Hasil analisis sinyal TA lengkap."""
    ticker: str
    company_name: str
    total_score: float
    category: str              # STRONG_BUY, BUY, NEUTRAL, SELL
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)

    # Detail TA
    current_price: float = 0
    trend: str = ""
    momentum: str = ""
    volatility: str = ""
    volume_detail: str = ""

    # Candlestick pattern
    candle_pattern: str = ""

    # Entry/SL/TP
    entry_low: float = 0
    entry_high: float = 0
    take_profit_1: float = 0
    take_profit_2: float = 0
    stop_loss: float = 0
    risk_reward: float = 0

    # AI
    ai_analysis: str = ""

    # Summary
    summary: str = ""


def _calculate_entry_levels(
    current_price: float, df,
) -> tuple[float, float, float, float, float, float]:
    """
    Hitung entry area, TP, SL berdasarkan TA.
    Entry = support terdekat atau low 5 hari
    TP = berdasarkan ATR atau % tetap
    SL = berdasarkan ATR atau % tetap
    """
    import numpy as np
    from analysis.indicators import atr

    lows = df["Low"].values
    highs = df["High"].values
    closes = df["Close"].values

    # Support = lowest low 5 hari
    recent_low = float(np.min(lows[-5:]))
    buffer = current_price * (config.ENTRY_BUFFER_PERCENT / 100)

    entry_low = max(recent_low - buffer * 0.5, current_price * 0.95)
    entry_high = min(recent_low + buffer * 0.5, current_price)

    if entry_low > current_price:
        entry_low = current_price * 0.98
        entry_high = current_price

    entry_mid = (entry_low + entry_high) / 2

    # ATR-based TP/SL jika ada data cukup
    if len(df) >= 14:
        atr_val = float(atr(df).iloc[-1])
        # ATR-based: TP = entry + 2*ATR, SL = entry - ATR
        tp1 = entry_mid + atr_val * 2
        tp2 = entry_mid + atr_val * 3
        sl = entry_mid - atr_val * 1.5

        # Clamp ATR-based dengan % fixed
        max_tp_pct = config.TP_PERCENT_1 / 100
        min_sl_pct = config.SL_PERCENT / 100

        tp1 = min(tp1, entry_mid * (1 + max_tp_pct * 2))
        tp2 = min(tp2, entry_mid * (1 + max_tp_pct * 3))
        sl = max(sl, entry_mid * (1 - min_sl_pct))
    else:
        # Fixed % based
        tp1 = entry_mid * (1 + config.TP_PERCENT_1 / 100)
        tp2 = entry_mid * (1 + config.TP_PERCENT_2 / 100)
        sl = entry_low * (1 - config.SL_PERCENT / 100)

    # Round to tick
    from signals.signal_generator import round_to_tick
    entry_low = round_to_tick(entry_low)
    entry_high = round_to_tick(entry_high)
    tp1 = round_to_tick(tp1)
    tp2 = round_to_tick(tp2)
    sl = round_to_tick(sl)

    # Risk:Reward
    risk = entry_mid - sl
    reward = tp1 - entry_mid
    rr = round(reward / risk, 2) if risk > 0 else 0

    return entry_low, entry_high, tp1, tp2, sl, rr


def from_ta_result(ta_result: TAResult, df) -> SignalResult:
    """
    Konversi TAResult ke SignalResult (lengkap dengan entry/TP/SL).
    """
    entry_low, entry_high, tp1, tp2, sl, rr = _calculate_entry_levels(
        ta_result.current_price, df
    )

    breakdown = ScoreBreakdown(
        trend=ta_result.trend.score,
        momentum=ta_result.momentum.score,
        volatility=ta_result.volatility.score,
        volume=ta_result.volume.score,
    )

    # Candlestick pattern
    pattern = candle_pattern(df)

    return SignalResult(
        ticker=ta_result.ticker,
        company_name=ta_result.company_name,
        total_score=ta_result.total_score,
        category=ta_result.category,
        breakdown=breakdown,
        current_price=ta_result.current_price,
        trend=ta_result.trend.detail,
        momentum=ta_result.momentum.detail,
        volatility=ta_result.volatility.detail,
        volume_detail=ta_result.volume.detail,
        candle_pattern=pattern,
        entry_low=entry_low,
        entry_high=entry_high,
        take_profit_1=tp1,
        take_profit_2=tp2,
        stop_loss=sl,
        risk_reward=rr,
        summary=ta_result.summary,
    )
