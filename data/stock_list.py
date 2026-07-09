"""
Smart Money Tracker — Stock List
Daftar saham watchlist (LQ45) untuk monitoring.
"""

# ──────────────────────────────────────────────
# LQ45 — 45 Saham Paling Likuid di IDX
# Format: (ticker_yfinance, kode_idx, nama_perusahaan)
# ──────────────────────────────────────────────
LQ45_STOCKS = [
    ("ACES.JK", "ACES", "Ace Hardware Indonesia"),
    ("ADRO.JK", "ADRO", "Adaro Energy"),
    ("AKRA.JK", "AKRA", "AKR Corporindo"),
    ("AMRT.JK", "AMRT", "Sumber Alfaria Trijaya"),
    ("ANTM.JK", "ANTM", "Aneka Tambang"),
    ("ASII.JK", "ASII", "Astra International"),
    ("BBCA.JK", "BBCA", "Bank Central Asia"),
    ("BBNI.JK", "BBNI", "Bank Negara Indonesia"),
    ("BBRI.JK", "BBRI", "Bank Rakyat Indonesia"),
    ("BBTN.JK", "BBTN", "Bank Tabungan Negara"),
    ("BMRI.JK", "BMRI", "Bank Mandiri"),
    ("BRIS.JK", "BRIS", "Bank Syariah Indonesia"),
    ("BRPT.JK", "BRPT", "Barito Pacific"),
    ("BUKA.JK", "BUKA", "Bukalapak"),
    ("CPIN.JK", "CPIN", "Charoen Pokphand Indonesia"),
    ("EMTK.JK", "EMTK", "Elang Mahkota Teknologi"),
    ("ESSA.JK", "ESSA", "Surya Esa Perkasa"),
    ("EXCL.JK", "EXCL", "XL Axiata"),
    ("GGRM.JK", "GGRM", "Gudang Garam"),
    ("GOTO.JK", "GOTO", "GoTo Gojek Tokopedia"),
    ("HRUM.JK", "HRUM", "Harum Energy"),
    ("ICBP.JK", "ICBP", "Indofood CBP Sukses Makmur"),
    ("INCO.JK", "INCO", "Vale Indonesia"),
    ("INDF.JK", "INDF", "Indofood Sukses Makmur"),
    ("INKP.JK", "INKP", "Indah Kiat Pulp & Paper"),
    ("INTP.JK", "INTP", "Indocement Tunggal Prakarsa"),
    ("ITMG.JK", "ITMG", "Indo Tambangraya Megah"),
    ("KLBF.JK", "KLBF", "Kalbe Farma"),
    ("MAPI.JK", "MAPI", "Mitra Adiperkasa"),
    ("MDKA.JK", "MDKA", "Merdeka Copper Gold"),
    ("MEDC.JK", "MEDC", "Medco Energi Internasional"),
    ("MIKA.JK", "MIKA", "Mitra Keluarga Karyasehat"),
    ("PGAS.JK", "PGAS", "Perusahaan Gas Negara"),
    ("PGEO.JK", "PGEO", "Pertamina Geothermal Energy"),
    ("PTBA.JK", "PTBA", "Bukit Asam"),
    ("SMGR.JK", "SMGR", "Semen Indonesia"),
    ("TBIG.JK", "TBIG", "Tower Bersama Infrastructure"),
    ("TINS.JK", "TINS", "Timah"),
    ("TLKM.JK", "TLKM", "Telkom Indonesia"),
    ("TOWR.JK", "TOWR", "Sarana Menara Nusantara"),
    ("TPIA.JK", "TPIA", "Chandra Asri Petrochemical"),
    ("UNTR.JK", "UNTR", "United Tractors"),
    ("UNVR.JK", "UNVR", "Unilever Indonesia"),
    ("SIDO.JK", "SIDO", "Industri Jamu & Farmasi Sido"),
    ("SMRA.JK", "SMRA", "Summarecon Agung"),
]


def get_watchlist():
    """Return daftar saham watchlist aktif."""
    return LQ45_STOCKS


def get_ticker_map():
    """Return dict mapping kode_idx -> (ticker_yfinance, nama_perusahaan)."""
    return {
        code: (ticker, name)
        for ticker, code, name in LQ45_STOCKS
    }


def get_idx_code(yf_ticker: str) -> str:
    """Konversi yfinance ticker ke kode IDX. e.g. 'BBCA.JK' -> 'BBCA'."""
    return yf_ticker.replace(".JK", "")


def get_yf_ticker(idx_code: str) -> str:
    """Konversi kode IDX ke yfinance ticker. e.g. 'BBCA' -> 'BBCA.JK'."""
    return f"{idx_code}.JK"


def get_company_name(idx_code: str) -> str:
    """Return nama perusahaan dari kode IDX."""
    ticker_map = get_ticker_map()
    if idx_code in ticker_map:
        return ticker_map[idx_code][1]
    return idx_code
