"""
Smart Money Tracker — Utility Helpers
Fungsi-fungsi utilitas untuk logging, formatting, retry, dll.
"""

import logging
import asyncio
import functools
from datetime import datetime

import config


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format=config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("smart_money_tracker.log", encoding="utf-8"),
        ],
    )

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def format_rupiah(value: float) -> str:
    """Format angka ke Rupiah dengan separator ribuan."""
    if value >= 0:
        return f"Rp {value:,.0f}"
    else:
        return f"-Rp {abs(value):,.0f}"


def format_rupiah_short(value: float) -> str:
    """Format angka ke Rupiah ringkas (T/M/Jt)."""
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


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format persentase."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_number(value: float) -> str:
    """Format angka dengan separator ribuan."""
    return f"{value:,.0f}"


def retry_async(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator untuk retry async functions.
    
    Usage:
        @retry_async(max_retries=3, delay=2.0)
        async def my_function():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logging.getLogger(__name__).warning(
                            f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
            raise last_error
        return wrapper
    return decorator


def is_trading_day() -> bool:
    """Cek apakah hari ini hari trading (Senin-Jumat)."""
    return datetime.now().weekday() < 5


def get_current_session() -> str:
    """
    Tentukan sesi trading saat ini berdasarkan waktu WIB.
    
    Returns:
        'pre_market': sebelum 09:00
        'session_1': 09:00-11:30
        'break': 11:30-13:30
        'session_2': 13:30-16:00
        'post_market': setelah 16:00
        'closed': weekend
    """
    if not is_trading_day():
        return "closed"

    now = datetime.now()
    hour = now.hour
    minute = now.minute
    time_val = hour * 100 + minute

    if time_val < 900:
        return "pre_market"
    elif time_val < 1130:
        return "session_1"
    elif time_val < 1330:
        return "break"
    elif time_val < 1600:
        return "session_2"
    else:
        return "post_market"
