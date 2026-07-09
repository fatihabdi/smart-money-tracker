"""
Smart Money Tracker — Telegram Bot
Handler utama bot Telegram: commands, security, dan message delivery.

Menggunakan analisis Technical Analysis (TA) dari data yfinance.
"""

import logging
import asyncio
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

import config
from bot.formatters import (
    format_signal,
    format_pre_market_summary,
    format_post_market_report,
    format_status_message,
    format_help_message,
    format_us_signal,
    format_us_summary,
)
from data.stock_list import get_watchlist, get_yf_ticker, get_company_name
from data.yfinance_client import fetch_ohlcv, fetch_bulk_ohlcv
from data.finnhub_client import finnhub_client
from data.us_stocks import get_us_tickers, get_us_company_name
from analysis.idx_scanner import analyze_stock, scan_full_watchlist
from analysis.us_scanner import analyze_us_stock, scan_single_us_stock, scan_full_us_watchlist
from analysis.chart_engine import render_daily_chart, cleanup_old_charts
from analysis.scoring import from_ta_result
from signals.signal_generator import generate_signal, generate_bulk_signals
from ai.gemini_analyst import generate_analysis, generate_vision_analysis

logger = logging.getLogger(__name__)

# Global state
_app: Application = None
_start_time: datetime = None
_last_scan_time: str = "Belum pernah"
_signals_today: int = 0


def _is_authorized(update: Update) -> bool:
    """Cek apakah user authorized (hanya owner)."""
    chat_id = str(update.effective_chat.id)
    authorized = chat_id == config.TELEGRAM_CHAT_ID
    if not authorized:
        logger.warning(f"Unauthorized access from chat_id: {chat_id}")
    return authorized


# ──────────────────────────────────────────────
# Command Handlers
# ──────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /start command."""
    if not _is_authorized(update):
        await update.message.reply_text("⛔ Unauthorized. Bot ini hanya untuk pemilik.")
        return

    welcome = ("🤖 *Smart Money Tracker - TA Edition*\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Selamat datang! Bot ini menganalisis saham dari *DUA pasar* menggunakan Technical Analysis:\n\n"
        "🇮🇩 *IDX* - 45 saham LQ45 via yfinance (gratis)\n"
        "🇺🇸 *US* - 50 saham SP500 via Finnhub (real-time)\n\n"
        "📈 *Trend* - MACD, EMA crossover, ADX\n"
        "⚡ *Momentum* - RSI, Stochastic\n"
        "📉 *Volatility* - Bollinger Bands, ATR\n"
        "📊 *Volume* - Volume spike, OBV trend\n"
        "🤖 *AI Analysis* - Gemini AI\n\n"
        "*Commands:*\n"
        "🇮🇩 /check BBCA - Cek IDX\n"
        "🇺🇸 /uscheck AAPL - Cek US\n"
        "🔄 /scan - Scan IDX\n"
        "🔄 /usscan - Scan US\n\n"
        "*Sinyal otomatis:* - IDX: 08:30 & 16:30 WIB\n\n"
        "Ketik /help untuk detail lengkap.")

    await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /help command."""
    if not _is_authorized(update):
        return
    await update.message.reply_text(format_help_message(), parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /status command."""
    if not _is_authorized(update):
        return

    uptime = "N/A"
    if _start_time:
        delta = datetime.now() - _start_time
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        uptime = f"{hours}h {minutes}m"

    msg = format_status_message(
        last_scan=_last_scan_time,
        total_signals_today=_signals_today,
        bot_uptime=uptime,
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /watchlist command."""
    if not _is_authorized(update):
        return

    stocks = get_watchlist()
    lines = ["📋 *Watchlist \\\\(LQ45\\\\)*\\n━━━━━━━━━━━━━━━━━━━\\n"]

    for i, (_, code, name) in enumerate(stocks, 1):
        from bot.formatters import _escape_md
        lines.append(f"{i}\\\\. `{_escape_md(code)}` — {_escape_md(name)}")

    lines.append(f"\\n_Total: {len(stocks)} saham_")

    await update.message.reply_text(
        "\\n".join(lines),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler untuk /check <TICKER> — cek satu saham spesifik.
    Contoh: /check BBCA
    """
    if not _is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Gunakan: /check BBCA\\n\\nContoh: `/check BBRI`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    ticker = context.args[0].upper().replace(".JK", "")
    yf_ticker = get_yf_ticker(ticker)

    # Loading message
    loading_msg = await update.message.reply_text(
        f"🔄 Scanning {ticker} dengan TA..."
    )

    try:
        signal = await scan_single_stock(ticker)

        if signal:
            # Generate AI analysis
            analysis = await generate_analysis(signal)
            signal.ai_analysis = analysis

            msg = format_signal(signal, report_type=f"Manual Check \\- {ticker}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            
            # AI Strategy Decision
            await _send_strategy_decision(
                context.bot,
                update.effective_chat.id,
                ticker,
                signal_score=signal.score,
                signal_status=signal.status,
            )
        else:
            from bot.formatters import _escape_md
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚪ *{_escape_md(ticker)}* \\- Tidak ada sinyal TA yang kuat\\\\.\\nScore di bawah threshold \\\\({config.MIN_SIGNAL_SCORE}\\\\)\\\\.\\n*Detail:* Data OHLCV mungkin tidak cukup untuk analisis\\\\.\\n\\nTips: Pastikan ticker IDX valid \\(contoh: BBCA, BBRI, TLKM\\)\\\\.\\.\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
            )

        await loading_msg.delete()

    except Exception as e:
        logger.error(f"Error scanning {ticker}: {e}")
        await loading_msg.edit_text(f"❌ Error scanning {ticker}: {str(e)[:200]}")


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /scan — full scan IDX watchlist."""
    if not _is_authorized(update):
        return

    loading_msg = await update.message.reply_text(
        "🔄 IDX Full scan TA sedang berjalan... ~30 detik."
    )

    try:
        signals = await run_full_scan()

        if signals:
            header = format_post_market_report(signals)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=header,
                parse_mode=ParseMode.MARKDOWN_V2,
            )

            for signal in signals[:5]:
                msg = format_signal(signal, report_type="Manual Scan")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=msg,
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                await asyncio.sleep(1)
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚪ Tidak ada sinyal TA kuat saat ini\\.\n\n_Score threshold: \\(>\\){config.MIN_SIGNAL_SCORE}/100_\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
            )

        await loading_msg.delete()

    except Exception as e:
        logger.error(f"Error during scan: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)[:200]}")


# ══════════════════════════════════════════════
# US Stock Commands
# ══════════════════════════════════════════════

async def cmd_uscheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler untuk /uscheck <TICKER> — cek saham US spesifik.
    Contoh: /uscheck AAPL
    """
    if not _is_authorized(update):
        return

    if not config.FINNHUB_API_KEY:
        await update.message.reply_text(
            "❌ FINNHUB_API_KEY belum di set di \\.env\n\nDaftar gratis di https://finnhub\\.io lalu tambahkan ke file \\.env",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Gunakan: /uscheck AAPL\n\nContoh: `/uscheck MSFT`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    ticker = context.args[0].upper()

    loading_msg = await update.message.reply_text(
        f"🇺🇸 Scanning {ticker} via yfinance + Finnhub live..."
    )

    try:
        signal = await scan_single_us_stock_wrapper(ticker, attach_live_price=True)

        if signal:
            # Generate AI analysis
            analysis = await generate_analysis(signal)
            signal.ai_analysis = analysis

            msg = format_us_signal(signal, report_type=f"US Check \\- {ticker}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            
            # AI Strategy Decision
            await _send_strategy_decision(
                context.bot,
                update.effective_chat.id,
                ticker,
                signal_score=signal.score,
                signal_status=signal.status,
            )
        else:
            from bot.formatters import _escape_md
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚪ *{_escape_md(ticker)}* \\- Tidak ada sinyal TA yang kuat\\.\nScore di bawah threshold \\({config.MIN_SIGNAL_SCORE}\\)\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
            )

        await loading_msg.delete()

    except Exception as e:
        logger.error(f"Error scanning US {ticker}: {e}")
        await loading_msg.edit_text(f"❌ Error scanning {ticker}: {str(e)[:200]}")


async def cmd_usscan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /usscan — full scan US watchlist."""
    if not _is_authorized(update):
        return

    if not config.FINNHUB_API_KEY:
        await update.message.reply_text(
            "❌ FINNHUB_API_KEY belum di set di \\.env\n\nDaftar gratis di https://finnhub\\.io",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    loading_msg = await update.message.reply_text(
        "🇺🇸 Full scan US stocks via Finnhub... ~2 menit (50 saham)"
    )

    try:
        signals = await run_full_us_scan()

        if signals:
            # Send header
            header = format_us_summary(signals)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=header,
                parse_mode=ParseMode.MARKDOWN_V2,
            )

            # Send top 5 signals
            for signal in signals[:5]:
                msg = format_us_signal(signal, report_type="US Scan")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=msg,
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                await asyncio.sleep(1)
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚪ Tidak ada sinyal US stocks kuat saat ini\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
            )

        await loading_msg.delete()

    except Exception as e:
        logger.error(f"Error during US scan: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)[:200]}")


# ──────────────────────────────────────────────
# Core Scan Functions (TA-based)
# ──────────────────────────────────────────────
async def scan_single_stock(ticker: str):
    """
    Scan satu saham menggunakan TA.
    Returns TradingSignal atau None.
    """
    from analysis.idx_scanner import scan_single_stock as ta_scan

    # 1. Fetch + analyze dengan TA
    ta_result = await ta_scan(ticker)

    if ta_result is None:
        logger.warning(f"TA scan returned None for {ticker}")
        return None

    # 2. Fetch OHLCV untuk entry levels
    yf_ticker = get_yf_ticker(ticker)
    df = await fetch_ohlcv(yf_ticker, period="2mo")

    if df is None or df.empty:
        logger.warning(f"No OHLCV data for {ticker}")
        return None

    # 3. Convert ke SignalResult + TradingSignal
    signal_result = from_ta_result(ta_result, df)
    trading_signal = generate_signal(ticker, signal_result)

    return trading_signal


async def run_full_scan() -> list:
    """
    Full scan semua saham LQ45 menggunakan TA.
    Return list of TradingSignal sorted by score.
    """
    global _last_scan_time, _signals_today

    logger.info("Starting full TA scan of LQ45 stocks...")

    # 1. Scan semua saham
    ta_results = await scan_full_watchlist()

    # 2. Fetch OHLCV untuk entry levels
    watchlist = get_watchlist()
    ohlcv_data = await fetch_bulk_ohlcv(
        [get_yf_ticker(code) for _, code, _ in watchlist],
        period="2mo",
    )

    # 3. Generate sinyal
    signals = []
    for ta_result in ta_results:
        yf_t = get_yf_ticker(ta_result.ticker)
        df = ohlcv_data.get(yf_t)
        if df is not None and not df.empty:
            signal_result = from_ta_result(ta_result, df)
            signal = generate_signal(ta_result.ticker, signal_result)
            if signal:
                signals.append(signal)

    # 4. AI analysis untuk top signals
    if signals:
        top_signals = signals[:5]
        from ai.gemini_analyst import generate_bulk_analysis
        await generate_bulk_analysis(top_signals)

    # Update state
    _last_scan_time = datetime.now().strftime("%d %b %Y %H:%M WIB")
    _signals_today += len(signals)

    logger.info(f"TA scan complete: {len(signals)} signals from {len(ta_results)} stocks")
    return signals


# ──────────────────────────────────────────────
# US Stock Scan Functions
# ──────────────────────────────────────────────
async def scan_single_us_stock_wrapper(ticker: str, attach_live_price: bool = False):
    """
    Scan satu saham US via yfinance + TA.
    
    Args:
        ticker: Ticker US (e.g., 'AAPL')
        attach_live_price: Jika True, fetch live price dari Finnhub dan update signal
    
    Returns:
        TradingSignal atau None.
    """
    ta_result, df = await scan_single_us_stock(ticker)

    if ta_result is None or df is None:
        logger.warning(f"US scan returned None for {ticker}")
        return None

    signal_result = from_ta_result(ta_result, df)
    trading_signal = generate_signal(ticker, signal_result)

    # Attach live price dari Finnhub jika diminta
    if attach_live_price and trading_signal and config.FINNHUB_API_KEY:
        try:
            loop = asyncio.get_event_loop()
            quote = await loop.run_in_executor(
                None, lambda: finnhub_client.fetch_quote(ticker)
            )
            if quote and quote.get("c", 0) > 0:
                live_price = quote["c"]
                trading_signal.current_price = live_price
                # Recalculate entry levels based on live price
                signal_result.current_price = live_price
                from analysis.scoring import _calculate_entry_levels
                el, eh, tp1, tp2, sl, rr = _calculate_entry_levels(live_price, df)
                trading_signal.entry_low = el
                trading_signal.entry_high = eh
                trading_signal.take_profit_1 = tp1
                trading_signal.take_profit_2 = tp2
                trading_signal.stop_loss = sl
                trading_signal.risk_reward = rr
                logger.info(f"Live price attached for {ticker}: \\${live_price:.2f}")
        except Exception as e:
            logger.warning(f"Failed to attach live price for {ticker}: {e}")

    return trading_signal


async def run_full_us_scan() -> list:
    """
    Full scan semua saham US watchlist via Finnhub.
    Return list of TradingSignal sorted by score.
    """
    global _last_scan_time, _signals_today

    logger.info("Starting full US TA scan...")

    # 1. Scan semua saham US
    us_results = scan_full_us_watchlist()

    # 2. Generate sinyal
    signals = []
    for ta_result, df in us_results:
        signal_result = from_ta_result(ta_result, df)
        signal = generate_signal(ta_result.ticker, signal_result)
        if signal:
            signals.append(signal)

    # 3. AI analysis untuk top signals
    if signals:
        top_signals = signals[:3]
        from ai.gemini_analyst import generate_bulk_analysis
        await generate_bulk_analysis(top_signals)

    _last_scan_time = datetime.now().strftime("%d %b %Y %H:%M WIB")
    _signals_today += len(signals)

    logger.info(f"US TA scan complete: {len(signals)} signals from {len(us_results)} stocks")
    return signals


# ──────────────────────────────────────────────
# Send Functions (untuk scheduler)
# ──────────────────────────────────────────────
async def send_message(text: str, parse_mode: str = ParseMode.MARKDOWN_V2):
    """Kirim pesan ke owner via bot."""
    if _app and _app.bot:
        try:
            await _app.bot.send_message(
                chat_id=config.TELEGRAM_CHAT_ID,
                text=text,
                parse_mode=parse_mode,
            )
        except Exception as e:
            logger.error(f"Error sending message: {e}")


async def _send_strategy_decision(
    bot,
    chat_id: int,
    ticker: str,
    signal_score: float = 0,
    signal_status: str = "",
):
    """
    Kirim AI Vision Strategy Decision ke Telegram (tanpa chart image).
    
    Flow:
      1. Render chart secara internal (untuk dibaca AI Vision)
      2. Gemini Vision baca chart → output DECISION (BUY/WATCHLIST/IGNORE)
      3. Kirim decision saja ke Telegram (tanpa foto chart)
    """
    try:
        if ".JK" not in ticker and ticker.upper() == ticker:
            from data.stock_list import get_watchlist
            watchlist_codes = [c for _, c, _ in get_watchlist()]
            yf_ticker = f"{ticker}.JK" if ticker in watchlist_codes else ticker
        else:
            yf_ticker = ticker
        
        df = await fetch_ohlcv(yf_ticker, period="6mo")
        if df is None or df.empty:
            logger.warning(f"No data for {ticker}")
            return
        
        chart_ticker = ticker.replace(".JK", "")
        chart_path = render_daily_chart(chart_ticker, df)
        
        if not chart_path:
            return
        
        # AI Vision → Strategy Decision
        if signal_score > 0:
            vision_text = await generate_vision_analysis(
                chart_path=chart_path,
                ticker=chart_ticker,
                signal_score=signal_score,
                signal_status=signal_status or "ANALYSIS",
            )
            
            if vision_text and len(vision_text) > 30:
                full_msg = f"🤖 AI STRATEGY AGENT\n{'-'*33}\n\n{vision_text}"
                await bot.send_message(
                    chat_id=chat_id,
                    text=full_msg,
                )
    except Exception as e:
        logger.warning(f"Strategy decision failed for {ticker}: {e}")
    
    cleanup_old_charts(hours=48)


async def send_pre_market():
    """Kirim pre-market watchlist + AI Strategy Decision."""
    logger.info("Sending pre-market watchlist (TA)...")
    signals = await run_full_scan()
    if signals:
        summary = format_pre_market_summary(signals)
        await send_message(summary)
        await asyncio.sleep(1)
        
        # AI Strategy Decision untuk top 3 signals
        for signal in signals[:3]:
            await asyncio.sleep(2)
            await _send_strategy_decision(
                _app.bot,
                int(config.TELEGRAM_CHAT_ID),
                signal.ticker,
                signal_score=signal.score,
                signal_status=signal.status,
            )
    else:
        await send_message(
            "📋 *Pre\\-Market Watchlist*\n\nTidak ada sinyal TA kuat hari ini\\.",
        )


async def send_post_market():
    """Kirim post-market report IDX + AI Strategy Decision."""
    logger.info("Sending IDX post-market report...")
    signals = await run_full_scan()

    if signals:
        header = format_post_market_report(signals)
        await send_message(header)
        await asyncio.sleep(1)

        for signal in signals[:5]:
            msg = format_signal(signal, report_type="Post\\-Market Report")
            await send_message(msg)
            await asyncio.sleep(1)
            
            # AI Strategy Decision untuk setiap signal
            await _send_strategy_decision(
                _app.bot,
                int(config.TELEGRAM_CHAT_ID),
                signal.ticker,
                signal_score=signal.score,
                signal_status=signal.status,
            )
            await asyncio.sleep(2)
    else:
        await send_message(
            "📊 *Post\\-Market Report*\n\nTidak ada sinyal TA kuat hari ini\\.",
        )


# ══════════════════════════════════════════════
# 🇺🇸 US Auto Send Functions (for scheduler)
# ══════════════════════════════════════════════

async def send_us_pre_market():
    """
    US Pre-Market signal: 19:30 WIB (08:30 ET).
    Analisis 100 candle + live price + AI Strategy Decision.
    """
    logger.info("Sending US pre-market analysis...")
    
    if not config.FINNHUB_API_KEY:
        await send_message("⚠️ FINNHUB_API_KEY belum di set, US signal tidak bisa dikirim otomatis.")
        return
    
    signals = await run_full_us_scan()
    
    if signals:
        header = "🇺🇸 *US PRE\\-MARKET ANALYSIS*\n━━━━━━━━━━━━━━━━━━━\n\n📊 Analisis 50 saham US \\(100 candle OHLCV\\)\n💰 Harga *live* via Finnhub API\n\n"
        await send_message(header)
        await asyncio.sleep(1)
        
        for signal in signals[:5]:
            msg = format_us_signal(signal, "US Pre\\-Market")
            await send_message(msg)
            await asyncio.sleep(1)
            
            # AI Strategy Decision
            await _send_strategy_decision(
                _app.bot,
                int(config.TELEGRAM_CHAT_ID),
                signal.ticker,
                signal_score=signal.score,
                signal_status=signal.status,
            )
            await asyncio.sleep(2)
    else:
        await send_message(
            "🇺🇸 *US Pre\\-Market*\n\nTidak ada sinyal kuat saat ini\\.",
        )


async def send_us_post_open():
    """
    US Post-Open Signal: 21:30 WIB (10:30 ET).
    1 jam setelah market open + AI Strategy Decision.
    """
    logger.info("Sending US post-open signal...")
    
    if not config.FINNHUB_API_KEY:
        return
    
    signals = await run_full_us_scan()
    
    if signals:
        header = "🇺🇸 *US POST\\-OPEN SIGNAL*\n━━━━━━━━━━━━━━━━━━━\n\n📊 1 jam setelah market open \\(10:30 ET\\)\n\n"
        await send_message(header)
        await asyncio.sleep(1)
        
        for signal in signals[:3]:
            msg = format_us_signal(signal, "US Post\\-Open")
            await send_message(msg)
            await asyncio.sleep(1)
            
            # AI Strategy Decision
            await _send_strategy_decision(
                _app.bot,
                int(config.TELEGRAM_CHAT_ID),
                signal.ticker,
                signal_score=signal.score,
                signal_status=signal.status,
            )
            await asyncio.sleep(2)
    else:
        await send_message("🇺🇸 *Post\\-Open:* Tidak ada sinyal kuat\\.")


async def send_us_mid_session():
    """
    US Mid-Session Signal: 00:30 WIB (13:30 ET).
    Mid-day check + AI Strategy Decision.
    """
    logger.info("Sending US mid-session signal...")
    
    if not config.FINNHUB_API_KEY:
        return
    
    signals = await run_full_us_scan()
    
    if signals:
        header = "🇺🇸 *US MID\\-SESSION SIGNAL*\n━━━━━━━━━━━━━━━━━━━\n\n📊 Mid\\-day check \\(13:30 ET\\)\n\n"
        await send_message(header)
        await asyncio.sleep(1)
        
        for signal in signals[:3]:
            msg = format_us_signal(signal, "US Mid\\-Session")
            await send_message(msg)
            await asyncio.sleep(1)
            
            # AI Strategy Decision
            await _send_strategy_decision(
                _app.bot,
                int(config.TELEGRAM_CHAT_ID),
                signal.ticker,
                signal_score=signal.score,
                signal_status=signal.status,
            )
            await asyncio.sleep(2)
    else:
        await send_message("🇺🇸 *Mid\\-Session:* Tidak ada sinyal kuat\\.")


# ──────────────────────────────────────────────
# Bot Initialization
# ──────────────────────────────────────────────
def create_bot() -> Application:
    """Create dan configure bot application."""
    global _app, _start_time

    if not config.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")

    _app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    _start_time = datetime.now()

    # Register handlers
    _app.add_handler(CommandHandler("start", cmd_start))
    _app.add_handler(CommandHandler("help", cmd_help))
    _app.add_handler(CommandHandler("status", cmd_status))
    _app.add_handler(CommandHandler("watchlist", cmd_watchlist))
    _app.add_handler(CommandHandler("check", cmd_check))
    _app.add_handler(CommandHandler("scan", cmd_scan))
    _app.add_handler(CommandHandler("uscheck", cmd_uscheck))
    _app.add_handler(CommandHandler("usscan", cmd_usscan))

    logger.info("Telegram bot created and handlers registered")
    return _app


def get_bot_app() -> Application:
    """Get bot application instance."""
    return _app


async def test_connection():
    """Test koneksi bot dengan mengirim pesan test."""
    app = create_bot()
    async with app:
        me = await app.bot.get_me()
        logger.info(f"Bot connected: @{me.username}")
        await app.bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            text="✅ Smart Money Tracker TA connected\\\\!",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return True
