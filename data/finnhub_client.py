"""
Smart Money Tracker — Finnhub Client
Mengambil data saham US dari Finnhub API (GRATIS, real-time).

Free tier: 60 API calls/minute, real-time US stock data, WebSocket support.
Sign up: https://finnhub.io (free API key)
"""

import logging
import time
from datetime import datetime, date, timedelta
from typing import Optional

import finnhub
import pandas as pd
import numpy as np

import config

logger = logging.getLogger(__name__)


class FinnhubClient:
    """Client untuk Finnhub API."""

    def __init__(self):
        self._api_key = config.FINNHUB_API_KEY
        self._client: Optional[finnhub.Client] = None
        self._last_request_time = 0.0

    def _ensure_client(self):
        """Initialize Finnhub client jika API key tersedia."""
        if self._client is None:
            if not self._api_key:
                logger.error("FINNHUB_API_KEY tidak di set di .env")
                raise ValueError("FINNHUB_API_KEY tidak ditemukan. Daftar di https://finnhub.io")
            self._client = finnhub.Client(api_key=self._api_key)

    def _rate_limit(self):
        """Rate limiting: max 55 calls/minute (free tier = 60/menit, kita sisakan buffer)."""
        now = time.time()
        elapsed = now - self._last_request_time
        min_interval = 60.0 / 55  # ~1.09 detik antar request
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    def fetch_ohlcv(
        self,
        symbol: str,
        period: str = "2mo",
        interval: str = "D",
    ) -> Optional[pd.DataFrame]:
        """
        Fetch data OHLCV untuk saham US.
        
        Args:
            symbol: Ticker US (e.g., 'AAPL', 'MSFT')
            period: Periode data ('1mo', '2mo', '3mo', '6mo', '1y')
            interval: Resolusi ('1'=1min, '5'=5min, '15'=15min, '30'=30min, '60'=60min, 'D'=daily, 'W'=weekly, 'M'=monthly)
        
        Returns:
            DataFrame dengan kolom: Open, High, Low, Close, Volume
            atau None jika gagal.
        """
        self._ensure_client()
        self._rate_limit()

        # Konversi period ke timestamp Unix
        to_ts = int(time.time())
        period_map = {
            "1mo": 30, "2mo": 60, "3mo": 90,
            "6mo": 180, "1y": 365,
        }
        days = period_map.get(period, 60)
        from_ts = to_ts - (days * 24 * 60 * 60)

        try:
            logger.info(f"Fetching {symbol} from Finnhub ({period}, {interval})...")
            candles = self._client.stock_candles(symbol, interval, from_ts, to_ts)

            if candles is None or candles.get("s") != "ok":
                logger.warning(f"Finnhub returned no data for {symbol}: {candles}")
                return None

            # Convert response ke DataFrame
            df = pd.DataFrame({
                "Open": candles["o"],
                "High": candles["h"],
                "Low": candles["l"],
                "Close": candles["c"],
                "Volume": candles["v"],
            }, index=pd.to_datetime(candles["t"], unit="s"))

            df.sort_index(inplace=True)
            df.dropna(inplace=True)

            # Filter hanya hari kerja (bukan weekend)
            df = df[df.index.dayofweek < 5]

            logger.info(f"Fetched {len(df)} rows for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error fetching {symbol} from Finnhub: {e}")
            return None

    def fetch_quote(self, symbol: str) -> Optional[dict]:
        """
        Fetch quote real-time untuk saham US.
        
        Returns:
            Dict dengan keys: c (current), h (high), l (low), 
            o (open), pc (prev close), dp (change %), d (change $)
        """
        self._ensure_client()
        self._rate_limit()

        try:
            quote = self._client.quote(symbol)
            if quote:
                # Hitung change
                current = quote.get("c", 0)
                prev_close = quote.get("pc", 0)
                if prev_close and prev_close > 0:
                    quote["d"] = round(current - prev_close, 2)
                    quote["dp"] = round(((current - prev_close) / prev_close) * 100, 2)
                return quote
            return None
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None

    def search_symbol(self, query: str) -> list[dict]:
        """
        Cari simbol saham US.
        
        Returns:
            List of {symbol, description, type, ...}
        """
        self._ensure_client()
        self._rate_limit()

        try:
            result = self._client.symbol_lookup(query)
            return result.get("result", [])
        except Exception as e:
            logger.error(f"Error searching {query}: {e}")
            return []


# Global instance
finnhub_client = FinnhubClient()
