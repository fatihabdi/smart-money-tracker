"""
Smart Money Tracker — Gemini AI Analyst
Menggunakan Google Gemini API untuk menghasilkan analisis
dan rekomendasi trading dalam Bahasa Indonesia.
"""

import logging
import asyncio
import time
from typing import Optional
from dataclasses import dataclass
import os

from google import genai
from PIL import Image

import config

logger = logging.getLogger(__name__)

# Rate limiting state
_last_request_time = 0
_request_count = 0
_request_window_start = 0


async def _rate_limit():
    """Enforce rate limiting untuk Gemini API free tier."""
    global _last_request_time, _request_count, _request_window_start

    now = time.time()

    # Reset window setiap menit
    if now - _request_window_start > 60:
        _request_count = 0
        _request_window_start = now

    # Max requests per minute
    if _request_count >= config.GEMINI_MAX_REQUESTS_PER_MINUTE:
        wait_time = 60 - (now - _request_window_start)
        if wait_time > 0:
            logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
            _request_count = 0
            _request_window_start = time.time()

    # Min delay antar request (1 detik)
    elapsed = now - _last_request_time
    if elapsed < 1.0:
        await asyncio.sleep(1.0 - elapsed)

    _request_count += 1
    _last_request_time = time.time()


def _build_prompt(signal) -> str:
    """
    Buat prompt untuk Gemini berdasarkan data sinyal TA.
    
    Args:
        signal: TradingSignal object
    
    Returns:
        Prompt string.
    """
    prompt = f"""Kamu adalah analis teknikal profesional untuk pasar saham.
Berdasarkan data analisis berikut, berikan analisis singkat dalam 1 paragraf (maksimal 4 kalimat) dalam Bahasa Indonesia.

DATA ANALISIS TA:
- Saham: {signal.ticker} ({signal.company_name})
- Harga Terakhir: {signal.current_price}
- TA Score: {signal.score}/100
- Status: {signal.status.replace('_', ' ')}

TREND:
- {signal.trend_detail[:200] if signal.trend_detail else 'N/A'}

MOMENTUM:
- RSI: {signal.rsi_value:.0f} ({signal.rsi_status})
- {signal.momentum_detail[:200] if signal.momentum_detail else 'N/A'}

VOLATILITAS:
- {signal.volatility_detail[:200] if signal.volatility_detail else 'N/A'}

VOLUME:
- Volume Spike: {signal.volume_spike:.1f}x dari rata-rata
- {signal.volume_detail[:200] if signal.volume_detail else 'N/A'}

CANDLE PATTERN:
- {signal.candle_pattern if signal.candle_pattern else 'Tidak ada pola signifikan'}

LEVEL:
- Support: {signal.support:.0f}
- Resistance: {signal.resistance:.0f}

SCORE BREAKDOWN:
- Trend: {signal.score_trend}/{config.SCORE_TREND_MAX}
- Momentum: {signal.score_momentum}/{config.SCORE_MOMENTUM_MAX}
- Volatility: {signal.score_volatility}/{config.SCORE_VOLATILITY_MAX}
- Volume: {signal.score_volume}/{config.SCORE_VOLUME_MAX}

R:R: 1:{signal.risk_reward}

INSTRUKSI:
1. Jelaskan MENGAPA saham ini mendapat score tersebut berdasarkan data TA
2. Sebutkan faktor utama (trend, momentum, volatilitas, atau volume)
3. Berikan pandangan untuk swing trading 1-4 minggu ke depan
4. Gunakan bahasa yang mudah dipahami trader ritel Indonesia
5. JANGAN berikan disclaimer investasi — fokus pada analisis data saja
6. Tulis dalam 1 paragraf singkat (3-4 kalimat)"""

    return prompt


async def generate_analysis(signal) -> str:
    """
    Generate analisis AI untuk satu sinyal trading.
    
    Args:
        signal: TradingSignal object
    
    Returns:
        String analisis 1 paragraf dalam Bahasa Indonesia.
    """
    if not config.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, returning placeholder analysis")
        return _fallback_analysis(signal)

    try:
        await _rate_limit()

        prompt = _build_prompt(signal)

        # Initialize client
        client = genai.Client(api_key=config.GEMINI_API_KEY)

        # Generate content (run in executor karena synchronous)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
            ),
        )

        if response and response.text:
            analysis = response.text.strip()
            # Remove markdown formatting jika ada
            analysis = analysis.replace("**", "").replace("*", "")
            logger.info(f"AI analysis generated for {signal.ticker} ({len(analysis)} chars)")
            return analysis
        else:
            logger.warning(f"Empty response from Gemini for {signal.ticker}")
            return _fallback_analysis(signal)

    except Exception as e:
        logger.error(f"Gemini API error for {signal.ticker}: {e}")
        return _fallback_analysis(signal)


async def generate_bulk_analysis(signals: list) -> list:
    """
    Generate analisis AI untuk banyak sinyal.
    Menambahkan ai_analysis ke setiap signal object.
    
    Args:
        signals: List of TradingSignal objects
    
    Returns:
        Sama list signals, dengan ai_analysis terisi.
    """
    for signal in signals:
        analysis = await generate_analysis(signal)
        signal.ai_analysis = analysis

    return signals


def _fallback_analysis(signal) -> str:
    """
    Generate analisis fallback tanpa AI.
    Digunakan ketika Gemini API tidak tersedia.
    """
    parts = []

    # Status
    if signal.status == "STRONG_BUY":
        parts.append(
            f"{signal.ticker} menunjukkan sinyal strong buy dengan TA Score {signal.score}/100."
        )
    elif signal.status == "BUY":
        parts.append(
            f"{signal.ticker} menunjukkan sinyal buy dengan score {signal.score}/100."
        )
    elif signal.status == "NEUTRAL":
        parts.append(
            f"{signal.ticker} dalam fase netral dengan score {signal.score}/100."
        )
    else:
        parts.append(
            f"{signal.ticker} dalam fase bearish dengan score {signal.score}/100."
        )

    # TA signals
    if signal.rsi_status == "OVERSOLD":
        parts.append(
            f"RSI {signal.rsi_value:.0f} oversold, berpotensi rebound."
        )
    elif signal.rsi_status == "OVERBOUGHT":
        parts.append(
            f"RSI {signal.rsi_value:.0f} overbought, waspada koreksi."
        )

    # Volume
    if signal.volume_spike >= 2.0:
        parts.append(
            f"Volume melonjak {signal.volume_spike:.1f}x dari rata-rata."
        )

    # Outlook
    if signal.risk_reward >= 2.0:
        parts.append(
            f"Dengan R:R 1:{signal.risk_reward}, saham ini layak dipertimbangkan."
        )

    return " ".join(parts) if parts else (
        f"{signal.ticker} dalam tahap monitoring dengan score {signal.score}/100."
    )


# ══════════════════════════════════════════════
# AI Vision Analysis (Chart-based) — Strategy Agent
# ══════════════════════════════════════════════

@dataclass
class VisionDecision:
    """Hasil keputusan dari AI Vision Strategy Agent."""
    decision: str           # BUY / WATCHLIST / IGNORE
    reasoning: str          # Penjelasan singkat (2-3 kalimat)
    confidence: str         # HIGH / MEDIUM / LOW


async def generate_vision_analysis(
    chart_path: str,
    ticker: str,
    signal_score: float,
    signal_status: str,
) -> str:
    """
    Generate analisis berdasarkan chart menggunakan Gemini Vision.
    Output memiliki format terstruktur: DECISION + reasoning.
    
    Decision: BUY / WATCHLIST / IGNORE
      - BUY: Chart mengkonfirmasi sinyal beli
      - WATCHLIST: Menarik tapi perlu konfirmasi lebih lanjut
      - IGNORE: Tidak ada setup yang jelas atau sinyal bearish
    
    Args:
        chart_path: Path ke file PNG chart
        ticker: Ticker symbol
        signal_score: TA score (0-100)
        signal_status: Kategori sinyal (BUY/NEUTRAL/SELL)
    
    Returns:
        String analisis terformat dengan DECISION + reasoning.
    """
    if not config.GEMINI_API_KEY:
        return _vision_fallback(ticker, signal_score, signal_status)

    if not chart_path or not os.path.exists(chart_path):
        return _vision_fallback(ticker, signal_score, signal_status)

    try:
        await _rate_limit()

        prompt = (
            f"Kamu adalah **Strategy Agent** — analis teknikal profesional yang membaca chart\n"
            f"dan memberikan KEPUTUSAN TRADING. Analisis chart {ticker} ini secara visual.\n\n"
            f"TA Score: {signal_score:.0f}/100 | Status: {signal_status}\n\n"
            "Amati dengan seksama:\n"
            "1. TREND: Posisi harga relatif terhadap EMA20 (emas) dan EMA50 (oranye).\n"
            "2. RSI: Di subplot kedua — overbought (>70) atau oversold (<30)?\n"
            "3. MACD: Di subplot ketiga — bullish/bearish crossover? Histogram positif/negatif?\n"
            "4. BOLLINGER: Garis putus-putus — harga di upper/lower band?\n"
            "5. VOLUME: Batang volume di subplot pertama — ada lonjakan?\n"
            "6. FIBONACCI: Level ungu — support/resistance terdekat?\n\n"
            "\n"
            "WAJIB berikan output DENGAN FORMAT INI PERSIS:\n"
            "\n"
            "DECISION: [BUY atau WATCHLIST atau IGNORE]\n"
            "CONFIDENCE: [HIGH atau MEDIUM atau LOW]\n"
            "REASONING: [2 kalimat maksimal, jelaskan alasan visual utama]\n"
            "\n"
            "PEDOMAN:\n"
            "- BUY = Konfirmasi visual kuat: trend naik + RSI tidak overbought + MACD bullish\n"
            "- WATCHLIST = Menarik tapi ada keraguan (RSI overbought, MACD mixed, volume kurang)\n"
            "- IGNORE = Setup tidak jelas, trend turun, atau sinyal bertentangan\n"
            "- Gunakan Bahasa Indonesia untuk REASONING\n"
            "- Jangan pakai tanda bintang/garis miring — langsung tulis teks saja"
        )

        client = genai.Client(api_key=config.GEMINI_API_KEY)
        image = Image.open(chart_path)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=[prompt, image],
            ),
        )

        if response and response.text:
            raw = response.text.strip()
            parsed = _parse_vision_decision(raw, ticker, signal_score, signal_status)
            return _format_vision_output(parsed)
        else:
            logger.warning(f"Empty vision response from Gemini for {ticker}")
            return _vision_fallback(ticker, signal_score, signal_status)

    except Exception as e:
        logger.error(f"Gemini Vision API error for {ticker}: {e}")
        return _vision_fallback(ticker, signal_score, signal_status)


def _parse_vision_decision(
    raw: str,
    ticker: str,
    signal_score: float,
    signal_status: str,
) -> VisionDecision:
    """Parse output Gemini untuk ekstrak DECISION, CONFIDENCE, dan REASONING."""
    decision = "WATCHLIST"  # default
    confidence = "MEDIUM"
    reasoning = raw[:300]  # fallback: ambil 300 chars pertama

    # Cari DECISION:
    for d in ["BUY", "WATCHLIST", "IGNORE"]:
        for line in raw.split("\n"):
            if f"DECISION: {d}" in line.upper() or f"DECISION:\n{d}" in raw.upper():
                decision = d
                break

    # Cari CONFIDENCE
    for c in ["HIGH", "MEDIUM", "LOW"]:
        for line in raw.split("\n"):
            if f"CONFIDENCE: {c}" in line.upper():
                confidence = c
                break

    # Cari REASONING
    for line in raw.split("\n"):
        if line.upper().startswith("REASONING:"):
            reasoning = line[10:].strip()
            break
    else:
        # Fallback: ambil kalimat terakhir yang relevan
        lines = [l.strip() for l in raw.split("\n") if l.strip() and not l.upper().startswith(("DECISION", "CONFIDENCE"))]
        if lines:
            reasoning = " ".join(lines[-2:])[:300]

    return VisionDecision(
        decision=decision,
        reasoning=reasoning,
        confidence=confidence,
    )


def _format_vision_output(vd: VisionDecision) -> str:
    """Format VisionDecision ke plain text (tanpa markdown, aman untuk Telegram)."""
    emoji_map = {"BUY": "🟢", "WATCHLIST": "🟡", "IGNORE": "🔴"}
    emoji = emoji_map.get(vd.decision, "⚪")
    
    conf_emoji = {"HIGH": "🔥", "MEDIUM": "📊", "LOW": "⚠️"}
    c_emoji = conf_emoji.get(vd.confidence, "")
    
    return (
        f"{emoji} STRATEGY DECISION: {vd.decision} {c_emoji}\n"
        f"\n"
        f"📝 {vd.reasoning}\n"
        f"\n"
        f"Confidence: {vd.confidence}"
    )


def _vision_fallback(ticker: str, signal_score: float, signal_status: str) -> str:
    """Fallback ketika Gemini Vision tidak tersedia. Tentukan decision dari score."""
    if signal_score >= 75:
        decision = "BUY"
        conf = "HIGH"
        reason = f"TA Score {signal_score:.0f}/100 mengindikasikan sinyal kuat secara teknikal."
    elif signal_score >= 55:
        decision = "WATCHLIST"
        conf = "MEDIUM"
        reason = f"TA Score {signal_score:.0f}/100 menunjukkan potensi tapi perlu konfirmasi tambahan."
    else:
        decision = "IGNORE"
        conf = "LOW"
        reason = f"TA Score {signal_score:.0f}/100 terlalu rendah untuk entry yang meyakinkan."
    
    vd = VisionDecision(decision=decision, reasoning=reason, confidence=conf)
    return _format_vision_output(vd)
