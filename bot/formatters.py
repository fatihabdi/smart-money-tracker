"""
Smart Money Tracker — Message Formatters
Format sinyal trading TA ke format Telegram MarkdownV2.
"""

import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)


def _escape_md(text: str) -> str:
    """Escape karakter khusus untuk Telegram MarkdownV2."""
    special_chars = ['_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def _format_price(price: float) -> str:
    """Format harga dengan separator ribuan."""
    return f"{price:,.0f}".replace(",", "\\.")


def _status_emoji(status: str) -> str:
    return {
        "STRONG_BUY": "🟢",
        "BUY": "🟡",
        "NEUTRAL": "⚪",
        "SELL": "🔴",
    }.get(status, "⚪")


def _status_label(status: str) -> str:
    return {
        "STRONG_BUY": "STRONG BUY",
        "BUY": "BUY",
        "NEUTRAL": "NEUTRAL",
        "SELL": "SELL",
    }.get(status, status)


def format_signal(signal, report_type: str = "TA Scan") -> str:
    """
    Format satu sinyal trading TA ke Telegram MarkdownV2.
    """
    status_em = _status_emoji(signal.status)
    status_lbl = _escape_md(_status_label(signal.status))

    # Score breakdown
    score_trend = f"{signal.score_trend:.0f}"
    score_mom = f"{signal.score_momentum:.0f}"
    score_vol = f"{signal.score_volatility:.0f}"
    score_vol_vol = f"{signal.score_volume:.0f}"

    # TA Details
    trend_detail = _escape_md(signal.trend_detail[:200]) if signal.trend_detail else "—"
    momentum_detail = _escape_md(signal.momentum_detail[:200]) if signal.momentum_detail else "—"
    volatility_detail = _escape_md(signal.volatility_detail[:200]) if signal.volatility_detail else "—"
    volume_detail = _escape_md(signal.volume_detail[:200]) if signal.volume_detail else "—"

    # R:R check mark
    rr_mark = "✅" if signal.risk_reward >= 2.0 else "⚠️"

    # Summary
    summary = _escape_md(signal.summary[:300]) if signal.summary else "—"

    # Candlestick pattern
    candle = signal.candle_pattern if signal.candle_pattern else "—"

    # AI Analysis
    ai_text = _escape_md(signal.ai_analysis[:500]) if signal.ai_analysis else "Analisis tidak tersedia"

    # Timestamp
    now = datetime.now()
    date_str = _escape_md(now.strftime("%d %b %Y"))

    msg = f"""📊 *TECHNICAL SIGNAL*
━━━━━━━━━━━━━━━━━━━

🏢 *{_escape_md(signal.ticker)}* — {_escape_md(signal.company_name)}
📈 Status: {status_em} *{status_lbl}*
📊 Score: *{signal.score:.0f}/100*
💰 Harga: Rp {_format_price(signal.current_price)}

📈 *Trend* [{score_trend}/30]
   {trend_detail}

⚡ *Momentum* [{score_mom}/25]
   {momentum_detail}

📉 *Volatility \\& Price* [{score_vol}/25]
   {volatility_detail}

📊 *Volume* [{score_vol_vol}/20]
   {volume_detail}

🕯️ *Candle Pattern*: {_escape_md(candle)}

🎯 *Trading Plan*
   Entry : Rp {_format_price(signal.entry_low)} — Rp {_format_price(signal.entry_high)}
   TP1   : Rp {_format_price(signal.take_profit_1)} \\\\(\\+{signal.tp1_pct}%\\)
   TP2   : Rp {_format_price(signal.take_profit_2)} \\\\(\\+{signal.tp2_pct}%\\)
   SL    : Rp {_format_price(signal.stop_loss)} \\\\(\\-{signal.sl_pct}%\\)
   R:R   : 1 : {signal.risk_reward} {rr_mark}

📊 *Score Breakdown*
   Trend: {score_trend} \\| Momentum: {score_mom} \\| Volatility: {score_vol} \\| Volume: {score_vol_vol}

🤖 *AI Analysis*
{ai_text}

⏰ {date_str} \\| {report_type}"""

    return msg


def format_pre_market_summary(signals: list) -> str:
    """Format ringkasan pre-market watchlist."""
    if not signals:
        return _escape_md("📋 Pre-Market Watchlist\n\nTidak ada saham dengan sinyal kuat saat ini.")

    header = "📋 *Pre\\\\-Market Watchlist*\\n━━━━━━━━━━━━━━━━━━━\\n\\n"

    lines = []
    for i, s in enumerate(signals[:10], 1):
        em = _status_emoji(s.status)
        ticker = _escape_md(s.ticker)
        name = _escape_md(s.company_name)
        lines.append(
            f"{i}\\\\. {em} *{ticker}* — {name}\\n"
            f"   Score: {s.score:.0f}/100 \\\\| RSI: {_escape_md(str(s.rsi_value))} \\\\| Vol: {s.volume_spike}x"
        )

    body = "\\n\\n".join(lines)
    footer = f"\\n\\n_Total: {len(signals)} sinyal_"

    now = datetime.now()
    date_str = _escape_md(now.strftime("%d %b %Y %H:%M WIB"))
    footer += f"\\n⏰ {date_str}"

    return header + body + footer


def format_post_market_report(signals: list) -> str:
    """Format header untuk post-market report."""
    total = len(signals)
    strong = sum(1 for s in signals if s.status == "STRONG_BUY")
    buy = sum(1 for s in signals if s.status == "BUY")

    header = f"""📊 *POST\\\\-MARKET REPORT*
━━━━━━━━━━━━━━━━━━━

📈 Hasil TA scan 45 saham LQ45

🟢 Strong Buy: *{strong}* saham
🟡 Buy: *{buy}* saham
📊 Total sinyal: *{total}* saham

_Detail sinyal di bawah \\\\.\\\\.\\\\._"""

    return header


def format_status_message(
    last_scan: str = "Belum pernah",
    total_signals_today: int = 0,
    bot_uptime: str = "N/A",
) -> str:
    """Format pesan status bot."""
    return f"""🤖 *Smart Money Tracker Status*
━━━━━━━━━━━━━━━━━━━

📊 Last Scan: {_escape_md(last_scan)}
📈 Signals Today: {total_signals_today}
⏰ Uptime: {_escape_md(bot_uptime)}

🗓️ *Schedule \\(WIB\\):*
🇮🇩 IDX:
   08:30 \\- Pre\\-Market Watchlist
   16:30 \\- Post\\-Market \\(Swing\\)

🇺🇸 US:
   19:30 \\- Pre\\-Market Analysis
   21:30 \\- Post\\-Open Signal
   00:30 \\- Mid\\-Session Signal

✅ Bot berjalan normal
📡 IDX: yfinance \\| US: yfinance + Finnhub
🔧 Analysis: TA \\(Trend, Momentum, Volatility, Volume\\)"""


def format_help_message() -> str:
    """Format pesan bantuan."""
    return """🤖 *Smart Money Tracker \\- Help*
━━━━━━━━━━━━━━━━━━━

*Commands:*
/start \\- Welcome message
/scan \\- Full scan TA (IDX)
/check BBCA \\- Cek saham IDX
/uscheck AAPL \\- Cek saham US via Finnhub
/usscan \\- Full scan US watchlist
/watchlist \\- Lihat daftar watchlist
/status \\- Status bot
/help \\- Bantuan ini

*Jadwal Sinyal Otomatis:*
⏰ 08:30 WIB \\- Pre\\-Market Watchlist (IDX)
⏰ 16:30 WIB \\- Post\\-Market Report (IDX)

*Scoring System \\- TA (0\\-100):*
🟢 ≥75 \\- Strong Buy
🟡 ≥55 \\- Buy
⚪ ≥35 \\- Neutral
🔴 <35 \\- Sell

*Indikator TA:*
📈 Trend: MACD, EMA crossover, ADX
⚡ Momentum: RSI, Stochastic
📉 Volatility: Bollinger Bands, ATR, S/R
📊 Volume: Spike detection, OBV trend

*Sumber Data:*
🇮🇩 IDX: yfinance (Yahoo Finance)
🇺🇸 US: Finnhub API (real\-time)

*Disclaimer:*
_Bot ini untuk edukasi dan analisis\\, Keputusan investasi sepenuhnya tanggung jawab pengguna\\,_"""


# ══════════════════════════════════════════════
# US Stock Formatters
# ══════════════════════════════════════════════

def _format_us_price(price: float) -> str:
    """Format harga US (dollar) dengan 2 desimal."""
    return f"{price:,.2f}".replace(",", "\\.")


def format_us_signal(signal, report_type: str = "US Scan") -> str:
    """
    Format sinyal trading US stocks ke Telegram MarkdownV2.
    """
    status_em = _status_emoji(signal.status)
    status_lbl = _escape_md(_status_label(signal.status))

    score_trend = f"{signal.score_trend:.0f}"
    score_mom = f"{signal.score_momentum:.0f}"
    score_vol = f"{signal.score_volatility:.0f}"
    score_vol_vol = f"{signal.score_volume:.0f}"

    trend_detail = _escape_md(signal.trend_detail[:200]) if signal.trend_detail else "—"
    momentum_detail = _escape_md(signal.momentum_detail[:200]) if signal.momentum_detail else "—"
    volatility_detail = _escape_md(signal.volatility_detail[:200]) if signal.volatility_detail else "—"
    volume_detail = _escape_md(signal.volume_detail[:200]) if signal.volume_detail else "—"

    rr_mark = "✅" if signal.risk_reward >= 2.0 else "⚠️"
    summary = _escape_md(signal.summary[:300]) if signal.summary else "—"
    candle = signal.candle_pattern if signal.candle_pattern else "—"
    ai_text = _escape_md(signal.ai_analysis[:500]) if signal.ai_analysis else "Analisis tidak tersedia"

    now = datetime.now()
    date_str = _escape_md(now.strftime("%d %b %Y"))

    msg = f"""🇺🇸 *US TECHNICAL SIGNAL*
━━━━━━━━━━━━━━━━━━━

🏢 *{_escape_md(signal.ticker)}* — {_escape_md(signal.company_name)}
📈 Status: {status_em} *{status_lbl}*
📊 Score: *{signal.score:.0f}/100*
💰 Harga: \$ {_format_us_price(signal.current_price)}

📈 *Trend* [{score_trend}/30]
   {trend_detail}

⚡ *Momentum* [{score_mom}/25]
   {momentum_detail}

📉 *Volatility \& Price* [{score_vol}/25]
   {volatility_detail}

📊 *Volume* [{score_vol_vol}/20]
   {volume_detail}

🕯️ *Candle Pattern*: {_escape_md(candle)}

🎯 *Trading Plan*
   Entry : \$ {_format_us_price(signal.entry_low)} — \$ {_format_us_price(signal.entry_high)}
   TP1   : \$ {_format_us_price(signal.take_profit_1)} \({signal.tp1_pct}%\)
   TP2   : \$ {_format_us_price(signal.take_profit_2)} \({signal.tp2_pct}%\)
   SL    : \$ {_format_us_price(signal.stop_loss)} \(\-{signal.sl_pct}%\)
   R:R   : 1 : {signal.risk_reward} {rr_mark}

📊 *Score Breakdown*
   Trend: {score_trend} \| Momentum: {score_mom} \| Volatility: {score_vol} \| Volume: {score_vol_vol}

🤖 *AI Analysis*
{ai_text}

⏰ {date_str} \| {report_type}
📡 Data: Finnhub API (real\-time)"""

    return msg


def format_us_summary(signals: list) -> str:
    """Format header untuk US scan summary."""
    total = len(signals)
    strong = sum(1 for s in signals if s.status == "STRONG_BUY")
    buy = sum(1 for s in signals if s.status == "BUY")

    header = f"""🇺🇸 *US STOCKS SCAN*
━━━━━━━━━━━━━━━━━━━

📈 Hasil TA scan 50 saham US via Finnhub

🟢 Strong Buy: *{strong}* saham
🟡 Buy: *{buy}* saham
📊 Total sinyal: *{total}* saham

_Detail sinyal di bawah \\.\\.\\._
📡 _Data: Finnhub API_"""

    return header


def format_us_watchlist(tickers: list) -> str:
    """Format daftar watchlist US."""
    lines = ["📋 *US Watchlist \\(S&P 500 Top\\)*\n━━━━━━━━━━━━━━━━━━━\n"]

    for i, (ticker, name, sector) in enumerate(tickers, 1):
        lines.append(f"{i}\\. `{_escape_md(ticker)}` — {_escape_md(name)} \\(_{_escape_md(sector)}_\)")

    lines.append(f"\n\n_Total: {len(tickers)} saham US_")
    return "\n".join(lines)
