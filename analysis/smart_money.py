"""
Smart Money Tracker — Smart Money Scoring Engine
Menggabungkan semua analisis (foreign flow, broker flow, volume, price action)
menjadi satu Smart Money Score untuk deteksi akumulasi/distribusi institusi.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import numpy as np

import config
from analysis.foreign_flow import ForeignFlowResult
from analysis.broker_flow import BrokerFlowResult
from analysis.volume_analysis import VolumeResult

logger = logging.getLogger(__name__)


@dataclass
class ScoreBreakdown:
    """Breakdown skor per komponen."""
    foreign_flow: float = 0
    broker_flow: float = 0
    volume: float = 0
    price_action: float = 0


@dataclass
class SmartMoneyResult:
    """Hasil analisis Smart Money gabungan."""
    ticker: str
    total_score: float                 # Score 0-100
    category: str                      # STRONG_ACCUMULATION, ACCUMULATION, NEUTRAL, DISTRIBUTION
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    foreign_flow: Optional[ForeignFlowResult] = None
    broker_flow: Optional[BrokerFlowResult] = None
    volume: Optional[VolumeResult] = None
    price_action_detail: str = ""      # Deskripsi price action
    summary: str = ""                  # Ringkasan singkat
    has_simulated_data: bool = False


def analyze_price_action(
    ticker: str,
    df: pd.DataFrame,
) -> tuple[float, str]:
    """
    Analisis price action sederhana untuk scoring.
    
    Logika:
    - Harga di atas SMA20 = bullish
    - Higher lows (uptrend) = bullish
    - Harga dekat support = entry opportunity
    - Candle pattern: bullish engulfing, etc.
    
    Returns:
        (score, detail_description)
    """
    max_score = config.SCORE_PRICE_ACTION_MAX
    score = 0.0
    details = []

    if df is None or len(df) < 10:
        return 0, "Data tidak cukup untuk analisis price action"

    closes = df["Close"].values
    highs = df["High"].values
    lows = df["Low"].values

    current_price = closes[-1]

    # 1. SMA20 position (max 5 poin)
    sma20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else float(np.mean(closes))
    if current_price > sma20:
        score += 5
        details.append(f"Harga di atas SMA20 ({sma20:,.0f})")
    elif current_price > sma20 * 0.97:
        score += 2
        details.append(f"Harga mendekati SMA20 ({sma20:,.0f})")
    else:
        details.append(f"Harga di bawah SMA20 ({sma20:,.0f})")

    # 2. Higher lows pattern (max 4 poin)
    if len(lows) >= 10:
        recent_lows = []
        # Cari swing lows sederhana (local minima)
        for i in range(2, min(len(lows) - 2, 15)):
            if lows[-(i+1)] < lows[-i] and lows[-(i+1)] < lows[-(i+2)]:
                recent_lows.append(lows[-(i+1)])
                if len(recent_lows) >= 3:
                    break

        if len(recent_lows) >= 2:
            if recent_lows[0] > recent_lows[1]:
                score += 4
                details.append("Pola higher lows (uptrend)")
            elif recent_lows[0] < recent_lows[1]:
                details.append("Pola lower lows (downtrend)")
                score -= 2

    # 3. Jarak dari support/low (max 3 poin)
    recent_low = float(np.min(lows[-10:])) if len(lows) >= 10 else float(np.min(lows))
    recent_high = float(np.max(highs[-10:])) if len(highs) >= 10 else float(np.max(highs))

    price_range = recent_high - recent_low
    if price_range > 0:
        position_in_range = (current_price - recent_low) / price_range
        if 0.2 <= position_in_range <= 0.5:
            score += 3
            details.append("Harga di area support (20-50% range)")
        elif position_in_range < 0.2:
            score += 2
            details.append("Harga dekat low (potensi bounce)")
        elif position_in_range > 0.8:
            details.append("Harga dekat high (hati-hati)")

    # 4. Momentum (max 3 poin)
    if len(closes) >= 5:
        pct_change_5d = ((closes[-1] - closes[-5]) / closes[-5]) * 100
        if 1 <= pct_change_5d <= 5:
            score += 3
            details.append(f"Momentum positif moderat (+{pct_change_5d:.1f}% 5 hari)")
        elif 0 <= pct_change_5d <= 1:
            score += 1
            details.append(f"Konsolidasi (+{pct_change_5d:.1f}% 5 hari)")
        elif pct_change_5d > 5:
            score += 1  # Sudah naik banyak, kurang menarik untuk entry
            details.append(f"Rally kuat (+{pct_change_5d:.1f}% 5 hari) — kurang ideal untuk entry")
        else:
            details.append(f"Momentum negatif ({pct_change_5d:.1f}% 5 hari)")

    # Clamp
    score = max(0, min(score, max_score))

    return score, " | ".join(details)


def calculate_smart_money_score(
    ticker: str,
    foreign_result: ForeignFlowResult,
    broker_result: BrokerFlowResult,
    volume_result: VolumeResult,
    ohlcv_df: Optional[pd.DataFrame] = None,
) -> SmartMoneyResult:
    """
    Hitung Smart Money Score gabungan.
    
    Scoring breakdown (total: 100):
    - Foreign Flow: 0-35
    - Broker Flow:  0-30
    - Volume:       0-20
    - Price Action: 0-15
    
    Kategori:
    - >= 75: STRONG_ACCUMULATION
    - >= 55: ACCUMULATION
    - >= 35: NEUTRAL
    - <  35: DISTRIBUTION
    """
    # Price action score
    pa_score, pa_detail = analyze_price_action(ticker, ohlcv_df)

    # Breakdown
    breakdown = ScoreBreakdown(
        foreign_flow=foreign_result.score,
        broker_flow=broker_result.score,
        volume=volume_result.score,
        price_action=pa_score,
    )

    total_score = (
        breakdown.foreign_flow
        + breakdown.broker_flow
        + breakdown.volume
        + breakdown.price_action
    )

    # Clamp to 0-100
    total_score = max(0, min(100, total_score))

    # Category
    if total_score >= config.SCORE_STRONG_ACCUMULATION:
        category = "STRONG_ACCUMULATION"
    elif total_score >= config.SCORE_ACCUMULATION:
        category = "ACCUMULATION"
    elif total_score >= config.SCORE_NEUTRAL:
        category = "NEUTRAL"
    else:
        category = "DISTRIBUTION"

    # Summary
    summary_parts = []
    if foreign_result.status in ("STRONG_BUY", "BUY"):
        summary_parts.append(f"Foreign net buy {_format_rupiah(foreign_result.net_value_total)}")
    if broker_result.institutional_dominance in ("STRONG", "MODERATE"):
        summary_parts.append(f"Institusi dominan ({broker_result.institutional_buy_pct:.0f}% buy)")
    if volume_result.is_spike:
        summary_parts.append(f"Volume spike {volume_result.spike_ratio}x")

    summary = ". ".join(summary_parts) if summary_parts else "Tidak ada sinyal signifikan"

    # Check simulated data
    has_simulated = foreign_result.is_simulated or broker_result.is_simulated

    return SmartMoneyResult(
        ticker=ticker,
        total_score=total_score,
        category=category,
        breakdown=breakdown,
        foreign_flow=foreign_result,
        broker_flow=broker_result,
        volume=volume_result,
        price_action_detail=pa_detail,
        summary=summary,
        has_simulated_data=has_simulated,
    )


def _format_rupiah(value: float) -> str:
    """Format angka ke format Rupiah ringkas."""
    abs_val = abs(value)
    sign = "+" if value >= 0 else "-"
    if abs_val >= 1_000_000_000_000:
        return f"{sign}Rp {abs_val / 1_000_000_000_000:.1f}T"
    elif abs_val >= 1_000_000_000:
        return f"{sign}Rp {abs_val / 1_000_000_000:.1f}M"
    elif abs_val >= 1_000_000:
        return f"{sign}Rp {abs_val / 1_000_000:.1f}Jt"
    else:
        return f"{sign}Rp {abs_val:,.0f}"
