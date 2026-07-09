"""
Smart Money Tracker — Chart Engine
Render chart OHLCV profesional dengan indikator TA menggunakan mplfinance.
Chart digunakan untuk AI Vision analysis (Gemini/Claude).

Fitur:
- 2 timeframe: 60 menit + 1 Hari
- Indikator: EMA 20/50, VWAP, Bollinger Bands
- Subplot bawah: RSI, MACD, Volume
- Auto-Fibonacci levels
"""

import logging
import os
from datetime import datetime
from typing import Optional

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend (server-safe)
import matplotlib.pyplot as plt
import mplfinance as mpf

from analysis.indicators import (
    ema, rsi, macd, bollinger_bands, vwap, auto_fibonacci,
)

logger = logging.getLogger(__name__)

# Chart output directory
CHART_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "charts")
os.makedirs(CHART_DIR, exist_ok=True)


def _prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Siapkan DataFrame untuk mplfinance.
    Pastikan index datetime, kolom OHLCV standar.
    """
    required = ["Open", "High", "Low", "Close", "Volume"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")

    plot_df = df[required].copy()

    # Ensure datetime index with timezone info
    if not isinstance(plot_df.index, pd.DatetimeIndex):
        plot_df.index = pd.to_datetime(plot_df.index)

    return plot_df


def _calculate_indicators(df: pd.DataFrame, is_intraday: bool = False):
    """
    Hitung semua indikator untuk overlay di chart.
    Returns dict of indicator series.
    """
    close = df["Close"]

    ind = {}

    # EMA
    ind["ema20"] = ema(close, 20)
    ind["ema50"] = ema(close, 50) if len(close) >= 50 else ema(close, 20)

    # VWAP
    ind["vwap"] = vwap(df)

    # Bollinger Bands
    bb = bollinger_bands(close)
    ind["bb_upper"] = bb.upper
    ind["bb_lower"] = bb.lower

    # RSI (untuk subplot)
    ind["rsi"] = rsi(close, 14)

    # MACD (untuk subplot)
    macd_res = macd(close)
    ind["macd"] = macd_res.macd_line
    ind["macd_signal"] = macd_res.signal_line
    ind["macd_hist"] = macd_res.histogram

    # Fibonacci levels
    ind["fib"] = auto_fibonacci(df)

    return ind


def render_daily_chart(
    ticker: str,
    df: pd.DataFrame,
    save_path: Optional[str] = None,
) -> Optional[str]:
    """
    Render daily chart dengan semua indikator.

    Layout:
      Panel 0: Price (EMA20, EMA50, VWAP, BB, Fibonacci)
      Panel 1: Volume (auto via volume=True)
      Panel 2: RSI subplot
      Panel 3: MACD subplot

    Args:
        ticker: Ticker symbol
        df: OHLCV DataFrame (daily)
        save_path: Path untuk simpan file. Default: auto di CHART_DIR

    Returns:
        Path ke file chart PNG, atau None jika gagal.
    """
    try:
        plot_df = _prepare_data(df)
        indicators = _calculate_indicators(plot_df)
        fib = indicators["fib"]

        # Setup dark theme style
        mc = mpf.make_marketcolors(
            up='#26a69a', down='#ef5350',
            edge='inherit',
            wick='inherit',
            volume='inherit',
        )
        style = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='--',
            gridcolor='#333355',
            facecolor='#1a1a2e',
            y_on_right=False,
            rc={
                'figure.facecolor': '#1a1a2e',
                'axes.labelcolor': '#cccccc',
                'xtick.color': '#cccccc',
                'ytick.color': '#cccccc',
                'axes.titlecolor': '#ffffff',
                'axes.edgecolor': '#333355',
            },
        )

        # RSI subplot (panel 2)
        rsi_series = indicators["rsi"]
        rsi_overbought = pd.Series(70, index=rsi_series.index)
        rsi_oversold = pd.Series(30, index=rsi_series.index)

        # MACD subplot (panel 3)
        macd_series = indicators["macd"]
        macd_signal = indicators["macd_signal"]
        macd_hist = indicators["macd_hist"]
        macd_colors = ['#26a69a' if v >= 0 else '#ef5350' for v in macd_hist]

        # Additional plots: Panel 0 overlays + Panel 2 RSI + Panel 3 MACD
        ap = [
            # Panel 0 overlays
            mpf.make_addplot(indicators["ema20"], color='#ffd700', width=1.2),
            mpf.make_addplot(indicators["ema50"], color='#ff9800', width=1.2),
            mpf.make_addplot(indicators["vwap"], color='#00bcd4', width=1.0, linestyle='--'),
            mpf.make_addplot(indicators["bb_upper"], color='white', width=0.8, linestyle='--', alpha=0.3),
            mpf.make_addplot(indicators["bb_lower"], color='white', width=0.8, linestyle='--', alpha=0.3),
            # Panel 2: RSI
            mpf.make_addplot(rsi_series, panel=2, color='#ce93d8', width=1.2, ylabel='RSI'),
            mpf.make_addplot(rsi_overbought, panel=2, color='#ef5350', width=0.8, linestyle='--', alpha=0.5),
            mpf.make_addplot(rsi_oversold, panel=2, color='#26a69a', width=0.8, linestyle='--', alpha=0.5),
            # Panel 3: MACD
            mpf.make_addplot(macd_series, panel=3, color='#42a5f5', width=1.2, ylabel='MACD'),
            mpf.make_addplot(macd_signal, panel=3, color='#ff7043', width=1.0, linestyle='--'),
            mpf.make_addplot(macd_hist, panel=3, type='bar', color=macd_colors, alpha=0.5),
        ]

        # Plot dengan 4 panel
        fig, axes = mpf.plot(
            plot_df,
            type='candle',
            style=style,
            volume=True,
            addplot=ap,
            figsize=(14, 9),
            panel_ratios=(4, 1.5, 1.5, 2),
            returnfig=True,
            tight_layout=True,
        )

        # Add title
        current_price = plot_df["Close"].iloc[-1]
        price_prefix = "$" if current_price < 1000 else "Rp "
        price_fmt = f"${current_price:.2f}" if current_price < 1000 else f"Rp {current_price:,.0f}"

        ema_bullish = indicators['ema20'].iloc[-1] > indicators['ema50'].iloc[-1]
        axes[0].set_title(
            f"{ticker} - Daily | {price_fmt} | "
            f"EMA20/50: {'BULLISH' if ema_bullish else 'BEARISH'}",
            color='white', fontsize=14, fontweight='bold', pad=15,
        )

        # Add Fibonacci lines on price panel (axes[0])
        fib_color = '#9c27b0'
        for name, price in fib.levels.items():
            axes[0].axhline(y=price, color=fib_color, linestyle=':', alpha=0.4, linewidth=0.8)
            axes[0].text(
                plot_df.index[-1], price, f'  {name}',
                color=fib_color, alpha=0.7, fontsize=7, verticalalignment='bottom',
            )

        # RSI threshold labels
        axes[2].axhline(y=70, color='#ef5350', linestyle='--', alpha=0.3, linewidth=0.8)
        axes[2].axhline(y=30, color='#26a69a', linestyle='--', alpha=0.3, linewidth=0.8)
        axes[2].set_ylim(0, 100)

        # Save
        if save_path is None:
            date_str = datetime.now().strftime("%Y%m%d")
            save_path = os.path.join(CHART_DIR, f"{ticker}_daily_{date_str}.png")

        fig.savefig(save_path, dpi=120, facecolor='#1a1a2e')
        plt.close(fig)

        logger.info(f"Daily chart saved: {save_path} ({os.path.getsize(save_path)/1024:.1f} KB)")
        return save_path

    except Exception as e:
        logger.error(f"Error rendering daily chart for {ticker}: {e}")
        return None


def render_intraday_chart(
    ticker: str,
    df_intraday: pd.DataFrame,
    save_path: Optional[str] = None,
) -> Optional[str]:
    """
    Render 60-minute intraday chart.

    Layout:
      Panel 0: Price (EMA 9, EMA 21, VWAP)
      Panel 1: Volume
      Panel 2: RSI

    Args:
        ticker: Ticker symbol
        df_intraday: OHLCV DataFrame (60m interval)
        save_path: Path untuk simpan file

    Returns:
        Path ke file chart PNG, atau None jika gagal.
    """
    try:
        plot_df = _prepare_data(df_intraday)

        mc = mpf.make_marketcolors(
            up='#26a69a', down='#ef5350',
            edge='inherit', wick='inherit', volume='inherit',
        )
        style = mpf.make_mpf_style(
            marketcolors=mc, gridstyle='--', gridcolor='#333355',
            facecolor='#16213e', y_on_right=False,
            rc={
                'figure.facecolor': '#16213e',
                'axes.labelcolor': '#cccccc',
                'xtick.color': '#cccccc',
                'ytick.color': '#cccccc',
                'axes.titlecolor': '#ffffff',
                'axes.edgecolor': '#333355',
            },
        )

        close = plot_df["Close"]
        ema9 = ema(close, 9)
        ema21 = ema(close, 21)
        vwap_line = vwap(plot_df)
        rsi_series = rsi(close, 14)
        rsi_ob = pd.Series(70, index=rsi_series.index)
        rsi_os = pd.Series(30, index=rsi_series.index)

        ap = [
            mpf.make_addplot(ema9, color='#ffd700', width=1.2),
            mpf.make_addplot(ema21, color='#ff9800', width=1.2),
            mpf.make_addplot(vwap_line, color='#00bcd4', width=1.0, linestyle='--'),
            mpf.make_addplot(rsi_series, panel=2, color='#ce93d8', width=1.2, ylabel='RSI'),
            mpf.make_addplot(rsi_ob, panel=2, color='#ef5350', width=0.8, linestyle='--', alpha=0.5),
            mpf.make_addplot(rsi_os, panel=2, color='#26a69a', width=0.8, linestyle='--', alpha=0.5),
        ]

        fig, axes = mpf.plot(
            plot_df, type='candle', style=style,
            volume=True, addplot=ap,
            figsize=(16, 9),
            panel_ratios=(5, 1.5, 1.5),
            returnfig=True, tight_layout=True,
        )

        current_price = plot_df["Close"].iloc[-1]
        axes[0].set_title(
            f"{ticker} - 60min | ${current_price:.2f}",
            color='white', fontsize=14, fontweight='bold', pad=15,
        )

        axes[2].set_ylim(0, 100)

        if save_path is None:
            date_str = datetime.now().strftime("%Y%m%d")
            save_path = os.path.join(CHART_DIR, f"{ticker}_60m_{date_str}.png")

        fig.savefig(save_path, dpi=120, facecolor='#16213e')
        plt.close(fig)

        logger.info(f"Intraday chart saved: {save_path}")
        return save_path

    except Exception as e:
        logger.error(f"Error rendering intraday chart for {ticker}: {e}")
        return None


def render_dual_chart(
    ticker: str,
    df_daily: pd.DataFrame,
    df_intraday: Optional[pd.DataFrame] = None,
) -> Optional[tuple[str, str]]:
    """
    Render 2 chart (daily + intraday) untuk AI Vision analysis.

    Returns:
        Tuple (daily_chart_path, intraday_chart_path) atau None.
    """
    daily_path = render_daily_chart(ticker, df_daily)
    intra_path = None

    if df_intraday is not None:
        intra_path = render_intraday_chart(ticker, df_intraday)

    if daily_path:
        return (daily_path, intra_path)
    return None


def chart_to_bytes(file_path: str) -> Optional[bytes]:
    """Baca file PNG ke bytes untuk dikirim via Telegram."""
    try:
        with open(file_path, 'rb') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading chart file {file_path}: {e}")
        return None


def cleanup_old_charts(hours: int = 24):
    """Hapus chart yang lebih tua dari N jam."""
    try:
        now = datetime.now().timestamp()
        for f in os.listdir(CHART_DIR):
            f_path = os.path.join(CHART_DIR, f)
            if os.path.isfile(f_path) and f.endswith('.png'):
                if os.path.getmtime(f_path) < now - (hours * 3600):
                    os.remove(f_path)
                    logger.debug(f"Cleaned up old chart: {f}")
    except Exception as e:
        logger.warning(f"Error cleaning up charts: {e}")
