"""
Smart Money Tracker — yFinance Client
Fetch OHLCV dan data harga dari Yahoo Finance untuk saham IDX.
"""

import logging
import asyncio
from typing import Optional

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


async def fetch_ohlcv(
    ticker: str,
    period: str = "1mo",
    interval: str = "1d",
) -> Optional[pd.DataFrame]:
    """
    Fetch data OHLCV untuk satu ticker.
    
    Args:
        ticker: Ticker yfinance (e.g. 'BBCA.JK')
        period: Period data ('1mo', '3mo', '6mo', '1y')
        interval: Interval data ('1d', '1h')
    
    Returns:
        DataFrame dengan kolom: Open, High, Low, Close, Volume
        atau None jika gagal.
    """
    try:
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None,
            lambda: yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
            ),
        )

        if df is None or df.empty:
            logger.warning(f"No data returned for {ticker}")
            return None

        # Flatten MultiIndex columns jika ada
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Pastikan kolom standar ada
        required = ["Open", "High", "Low", "Close", "Volume"]
        for col in required:
            if col not in df.columns:
                logger.warning(f"Missing column {col} for {ticker}")
                return None

        df = df[required].copy()
        df.dropna(inplace=True)

        logger.info(f"Fetched {len(df)} rows for {ticker}")
        return df

    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return None


async def fetch_current_price(ticker: str) -> Optional[dict]:
    """
    Fetch harga terakhir dan info ringkas untuk satu ticker.
    
    Returns:
        Dict dengan keys: price, change, change_pct, volume, prev_close
        atau None jika gagal.
    """
    try:
        loop = asyncio.get_event_loop()
        stock = await loop.run_in_executor(None, lambda: yf.Ticker(ticker))
        info = await loop.run_in_executor(None, lambda: stock.fast_info)

        result = {
            "price": getattr(info, "last_price", 0),
            "prev_close": getattr(info, "previous_close", 0),
            "volume": getattr(info, "last_volume", 0),
            "market_cap": getattr(info, "market_cap", 0),
        }

        if result["prev_close"] and result["prev_close"] > 0:
            result["change"] = result["price"] - result["prev_close"]
            result["change_pct"] = (result["change"] / result["prev_close"]) * 100
        else:
            result["change"] = 0
            result["change_pct"] = 0

        return result

    except Exception as e:
        logger.error(f"Error fetching current price for {ticker}: {e}")
        return None


async def fetch_bulk_ohlcv(
    tickers: list[str],
    period: str = "1mo",
    interval: str = "1d",
    batch_size: int = 10,
) -> dict[str, pd.DataFrame]:
    """
    Fetch data OHLCV untuk banyak ticker sekaligus.
    
    Args:
        tickers: List of yfinance tickers
        period: Period data
        interval: Interval data
        batch_size: Jumlah ticker per batch

    Returns:
        Dict mapping ticker -> DataFrame
    """
    results = {}

    # Process in batches untuk menghindari rate limiting
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        logger.info(f"Fetching batch {i // batch_size + 1}: {batch}")

        tasks = [fetch_ohlcv(t, period, interval) for t in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for ticker, result in zip(batch, batch_results):
            if isinstance(result, Exception):
                logger.error(f"Exception for {ticker}: {result}")
                continue
            if result is not None:
                results[ticker] = result

        # Delay antar batch
        if i + batch_size < len(tickers):
            await asyncio.sleep(1)

    logger.info(f"Fetched data for {len(results)}/{len(tickers)} tickers")
    return results
