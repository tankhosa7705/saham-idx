import os

# ── Telegram ─────────────────────────────────────────────────
# Di Railway: set via environment variables
# Di lokal: langsung isi di sini
TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_TOKEN',   '8766870329:AAHjjEnP3GD8hbEjNwyRXWHFS5-0Wzxsp9w')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '8672645047')

# ── Saham yang dipantau ───────────────────────────────────────
WATCH_LIST = [
    'BBCA', 'BBRI', 'BMRI', 'TLKM', 'ASII',
    'UNVR', 'KLBF', 'ADRO', 'PTBA', 'ANTM',
    'BBNI', 'BRIS', 'PGAS', 'BSDE', 'JPFA',
    'MDKA', 'INCO', 'TOWR', 'ISAT', 'MAPI',
]

# ── Pengaturan ────────────────────────────────────────────────
CHECK_INTERVAL_MINUTES = 60
DATA_PERIOD            = '3mo'
