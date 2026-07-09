"""
Smart Money Tracker — US Stock List
Daftar saham US untuk monitoring via Finnhub API.

Sumber: SP500 top market cap + saham tech/growth populer.
Update berkala direkomendasikan.
"""

# ──────────────────────────────────────────────
# US Watchlist — Top 50 Stocks by Market Cap
# Format: (ticker, nama_perusahaan, sektor)
# ──────────────────────────────────────────────
US_WATCHLIST = [
    # Tech Megacap
    ("AAPL", "Apple Inc.", "Technology"),
    ("MSFT", "Microsoft Corp.", "Technology"),
    ("GOOGL", "Alphabet Inc.", "Technology"),
    ("AMZN", "Amazon.com Inc.", "Consumer Cyclical"),
    ("NVDA", "NVIDIA Corp.", "Technology"),
    ("META", "Meta Platforms Inc.", "Technology"),
    ("TSLA", "Tesla Inc.", "Consumer Cyclical"),
    ("AVGO", "Broadcom Inc.", "Technology"),

    # Tech & Software
    ("ORCL", "Oracle Corp.", "Technology"),
    ("CRM", "Salesforce Inc.", "Technology"),
    ("ADBE", "Adobe Inc.", "Technology"),
    ("INTC", "Intel Corp.", "Technology"),
    ("AMD", "Advanced Micro Devices", "Technology"),
    ("CSCO", "Cisco Systems Inc.", "Technology"),
    ("IBM", "International Business Machines", "Technology"),

    # Internet & E-commerce
    ("NFLX", "Netflix Inc.", "Communication"),
    ("DIS", "Walt Disney Co.", "Communication"),
    ("PYPL", "PayPal Holdings Inc.", "Financial"),

    # Banking & Finance
    ("JPM", "JPMorgan Chase & Co.", "Financial"),
    ("BAC", "Bank of America Corp.", "Financial"),
    ("GS", "Goldman Sachs Group Inc.", "Financial"),
    ("V", "Visa Inc.", "Financial"),
    ("MA", "Mastercard Inc.", "Financial"),
    ("BLK", "BlackRock Inc.", "Financial"),

    # Healthcare
    ("UNH", "UnitedHealth Group Inc.", "Healthcare"),
    ("JNJ", "Johnson & Johnson", "Healthcare"),
    ("PFE", "Pfizer Inc.", "Healthcare"),
    ("MRK", "Merck & Co. Inc.", "Healthcare"),
    ("ABBV", "AbbVie Inc.", "Healthcare"),
    ("LLY", "Eli Lilly and Co.", "Healthcare"),

    # Consumer
    ("WMT", "Walmart Inc.", "Consumer Defensive"),
    ("COST", "Costco Wholesale Corp.", "Consumer Defensive"),
    ("PG", "Procter & Gamble Co.", "Consumer Defensive"),
    ("KO", "The Coca-Cola Co.", "Consumer Defensive"),
    ("PEP", "PepsiCo Inc.", "Consumer Defensive"),
    ("MCD", "McDonald's Corp.", "Consumer Cyclical"),
    ("SBUX", "Starbucks Corp.", "Consumer Cyclical"),
    ("NKE", "Nike Inc.", "Consumer Cyclical"),

    # Energy & Industrial
    ("XOM", "Exxon Mobil Corp.", "Energy"),
    ("CVX", "Chevron Corp.", "Energy"),
    ("CAT", "Caterpillar Inc.", "Industrial"),
    ("BA", "Boeing Co.", "Industrial"),
    ("GE", "General Electric Co.", "Industrial"),
    ("HON", "Honeywell International Inc.", "Industrial"),

    # Telecommunications
    ("T", "AT&T Inc.", "Communication"),
    ("VZ", "Verizon Communications Inc.", "Communication"),
    ("TMUS", "T-Mobile US Inc.", "Communication"),

    # Semiconductors
    ("QCOM", "Qualcomm Inc.", "Technology"),
    ("TXN", "Texas Instruments Inc.", "Technology"),
    ("MU", "Micron Technology Inc.", "Technology"),
]

# Indeks utama untuk referensi
US_INDICES = {
    "SPY": "SPDR S&P 500 ETF",
    "QQQ": "Invesco QQQ Trust (Nasdaq)",
    "DIA": "SPDR Dow Jones Industrial Average",
    "IWM": "iShares Russell 2000 ETF",
}


def get_us_watchlist() -> list[tuple[str, str, str]]:
    """Return daftar saham US watchlist."""
    return US_WATCHLIST


def get_us_tickers() -> list[str]:
    """Return list of US ticker symbols."""
    return [ticker for ticker, _, _ in US_WATCHLIST]


def get_us_company_name(ticker: str) -> str:
    """Return nama perusahaan dari ticker."""
    for t, name, _ in US_WATCHLIST:
        if t == ticker:
            return name
    return ticker


def get_us_sector(ticker: str) -> str:
    """Return sektor dari ticker."""
    for t, _, sector in US_WATCHLIST:
        if t == ticker:
            return sector
    return "Unknown"
