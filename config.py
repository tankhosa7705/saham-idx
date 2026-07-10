import os

# ── Telegram ─────────────────────────────────────────────────
# JANGAN tulis token di file ini — repo PUBLIC, token yang ter-commit
# otomatis dicabut Telegram (GitHub secret scanning). Token hanya boleh di:
#   - GitHub Actions: Settings > Secrets (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
#   - Lokal: file config_local.py (di-gitignore)
try:
    from config_local import TELEGRAM_TOKEN as _LOCAL_TOKEN, TELEGRAM_CHAT_ID as _LOCAL_CHAT
except ImportError:
    _LOCAL_TOKEN = ''; _LOCAL_CHAT = ''
TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_TOKEN',   _LOCAL_TOKEN)
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', _LOCAL_CHAT)

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

# ── Pluang watchlist ──────────────────────────────────────────
PLUANG_WATCHLIST = {
    'crypto':    ['BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'AVAX'],
    'us_stocks': ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA'],
}
