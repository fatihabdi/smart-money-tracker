"""
Smart Money Tracker — Volume Analysis
Deteksi volume spike dan analisis korelasi volume-price untuk sinyal akumulasi.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import numpy as np

import config

logger = logging.getLogger(__name__)


@dataclass
class VolumeResult:
    """Hasil analisis volume."""
    ticker: str
    avg_volume_20d: float          # Rata-rata volume 20 hari
    current_volume: float          # Volume terakhir
    spike_ratio: float             # current / average
    is_spike: bool                 # spike_ratio > threshold
    volume_trend: str              # "INCREASING", "DECREASING", "STABLE"
    price_volume_corr: str         # "BULLISH", "BEARISH", "NEUTRAL"
    consecutive_high_vol_days: int # Hari berturut volume diatas rata-rata
    score: float                   # Score 0 - SCORE_VOLUME_MAX


def analyze_volume(
    ticker: str,
    df: pd.DataFrame,
    avg_days: int = None,
) -> VolumeResult:
    """
    Analisis volume untuk satu saham.
    
    Logika:
    - Volume spike (> 2x average) = sinyal ada aktivitas
    - Volume spike + harga naik = bullish (kemungkinan akumulasi)
    - Volume spike + harga turun = bearish (kemungkinan distribusi)
    - Volume trend meningkat secara konsisten = ada interest
    
    Args:
        ticker: Kode saham
        df: DataFrame OHLCV
        avg_days: Jumlah hari untuk rata-rata (default: 20)
    
    Returns:
        VolumeResult dengan skor dan detail.
    """
    if avg_days is None:
        avg_days = config.VOLUME_AVG_DAYS

    if df is None or len(df) < 5:
        return VolumeResult(
            ticker=ticker,
            avg_volume_20d=0,
            current_volume=0,
            spike_ratio=0,
            is_spike=False,
            volume_trend="STABLE",
            price_volume_corr="NEUTRAL",
            consecutive_high_vol_days=0,
            score=0,
        )

    volumes = df["Volume"].values
    closes = df["Close"].values

    # ── Metrics dasar ──
    lookback = min(avg_days, len(volumes))
    avg_vol = float(np.mean(volumes[-lookback:]))
    current_vol = float(volumes[-1])

    spike_ratio = current_vol / avg_vol if avg_vol > 0 else 0
    is_spike = spike_ratio >= config.VOLUME_SPIKE_THRESHOLD

    # ── Volume Trend ──
    # Bandingkan average volume 5 hari terakhir vs 5 hari sebelumnya
    if len(volumes) >= 10:
        recent_avg = float(np.mean(volumes[-5:]))
        prior_avg = float(np.mean(volumes[-10:-5]))
        if prior_avg > 0:
            vol_change = (recent_avg - prior_avg) / prior_avg
            if vol_change > 0.3:
                volume_trend = "INCREASING"
            elif vol_change < -0.3:
                volume_trend = "DECREASING"
            else:
                volume_trend = "STABLE"
        else:
            volume_trend = "STABLE"
    else:
        volume_trend = "STABLE"

    # ── Price-Volume Correlation ──
    # Korelasi antara perubahan harga dan volume (5 hari terakhir)
    if len(closes) >= 5 and len(volumes) >= 5:
        price_changes = np.diff(closes[-6:])   # 5 price changes
        vol_last5 = volumes[-5:]

        # Volume tinggi + harga naik = bullish
        # Volume tinggi + harga turun = bearish
        recent_price_change = closes[-1] - closes[-5] if len(closes) >= 5 else 0
        recent_vol_avg = float(np.mean(vol_last5))

        if recent_vol_avg > avg_vol and recent_price_change > 0:
            price_volume_corr = "BULLISH"
        elif recent_vol_avg > avg_vol and recent_price_change < 0:
            price_volume_corr = "BEARISH"
        else:
            price_volume_corr = "NEUTRAL"
    else:
        price_volume_corr = "NEUTRAL"

    # ── Consecutive high volume days ──
    consecutive = 0
    for v in reversed(volumes):
        if v > avg_vol:
            consecutive += 1
        else:
            break

    # ── Scoring (max: SCORE_VOLUME_MAX = 20) ──
    score = 0.0
    max_score = config.SCORE_VOLUME_MAX

    # 1. Volume spike ratio (max 8 poin)
    if spike_ratio >= 4.0:
        score += 8
    elif spike_ratio >= 3.0:
        score += 6
    elif spike_ratio >= 2.0:
        score += 4
    elif spike_ratio >= 1.5:
        score += 2

    # 2. Price-volume correlation (max 6 poin)
    if price_volume_corr == "BULLISH":
        score += 6
    elif price_volume_corr == "BEARISH":
        score -= 2  # Penalti
    # NEUTRAL = 0

    # 3. Volume trend (max 3 poin)
    if volume_trend == "INCREASING":
        score += 3
    elif volume_trend == "DECREASING":
        score -= 1

    # 4. Consecutive high vol days (max 3 poin)
    if consecutive >= 5:
        score += 3
    elif consecutive >= 3:
        score += 2
    elif consecutive >= 2:
        score += 1

    # Clamp
    score = max(0, min(score, max_score))

    return VolumeResult(
        ticker=ticker,
        avg_volume_20d=avg_vol,
        current_volume=current_vol,
        spike_ratio=round(spike_ratio, 2),
        is_spike=is_spike,
        volume_trend=volume_trend,
        price_volume_corr=price_volume_corr,
        consecutive_high_vol_days=consecutive,
        score=score,
    )
