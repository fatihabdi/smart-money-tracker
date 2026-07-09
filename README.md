# 🧠 AI Smart Money Tracker

Bot Telegram pribadi untuk deteksi akumulasi institusi di saham IDX (Indonesia) menggunakan foreign flow, broker flow, volume spike analysis, dan Gemini AI.

## Fitur
- **Foreign Flow Analysis**: Deteksi net buy asing dan trend.
- **Broker Flow Analysis**: Deteksi aktivitas broker institusi.
- **Volume Analysis**: Deteksi volume spike & price-volume correlation.
- **Smart Money Score (0-100)**: Klasifikasi *Strong Accumulation, Accumulation, Neutral, Distribution*.
- **Trading Signal**: Entry area, TP1, TP2, Stop Loss, Risk:Reward ratio.
- **AI Analysis**: Analisis singkat menggunakan Google Gemini API.
- **Automated Scheduling**: 
  - 08:30 WIB — Pre-Market Watchlist
  - 16:30 WIB — Post-Market Report

## Persiapan Awal
1. Clone repositori ini.
2. Buat file `.env` (lihat `.env.example`).
3. Dapatkan **Telegram Bot Token** dari [@BotFather](https://t.me/BotFather).
4. Dapatkan **Chat ID** Telegram Anda (gunakan [@userinfobot](https://t.me/userinfobot)).
5. Dapatkan **Gemini API Key** dari [Google AI Studio](https://aistudio.google.com/) (Gratis).

## Instalasi
```bash
# Buat virtual environment (opsional)
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

# Install dependensi
pip install -r requirements.txt
```

## Penggunaan
```bash
# Jalankan bot
python main.py

# (Opsional) Jalankan full scan untuk test (tanpa mengirim ke Telegram)
python main.py --test-scan
```

## Bot Commands
Di dalam aplikasi Telegram Anda, gunakan perintah berikut ke bot Anda:
- `/start` — Lihat status & bantuan
- `/scan` — Jalankan manual scan keseluruhan
- `/check BBCA` — Cek satu saham secara instan
- `/watchlist` — Lihat daftar pantauan (LQ45)
- `/status` — Lihat status sistem & scheduler

## Disclaimer
Bot ini dibuat untuk tujuan edukasi dan analisis. Semua keputusan investasi dan trading berada di tangan Anda sendiri. Analisis dari bot dan AI bukanlah saran keuangan profesional.
