"""
Runner Pluang: sinyal emas, crypto, US stocks + portofolio + price targets.
Dijalankan via GitHub Actions setiap jam.
"""
import logging
from datetime import datetime

from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PLUANG_WATCHLIST
from bot.telegram import send_message
from bot.alert_pluang import check_gold, check_crypto, check_us_stocks, format_pluang_alert
from bot.portfolio import format_portfolio_summary
from bot.price_targets import check_price_targets, format_target_alert
from data.fetcher_pluang import get_usd_idr

logging.basicConfig(level=logging.INFO, format='%(asctime)s — %(message)s')

# Kirim ringkasan portfolio setiap hari jam 08:00 WIT = 23:00 UTC (malam sebelumnya)
PORTFOLIO_HOUR_UTC = 23


def main():
    if not TELEGRAM_TOKEN or 'ISI_' in TELEGRAM_TOKEN:
        print("ERROR: TELEGRAM_TOKEN belum diset di GitHub Secrets")
        return

    now = datetime.utcnow()
    logging.info(f"=== Pluang Bot — {now.strftime('%Y-%m-%d %H:%M')} UTC ===")

    # Kurs USD/IDR
    usd_idr = get_usd_idr()
    logging.info(f"USD/IDR: Rp {usd_idr:,.0f}")

    alerts = []

    # Emas (ikut jam US market, tapi boleh cek kapan saja)
    logging.info("Cek sinyal emas...")
    alerts += check_gold(usd_idr)

    # Crypto (24/7)
    logging.info(f"Cek crypto: {PLUANG_WATCHLIST['crypto']}")
    alerts += check_crypto(PLUANG_WATCHLIST['crypto'], usd_idr)

    # US Stocks (data hanya berubah saat market buka, tapi aman cek kapan saja)
    logging.info(f"Cek US stocks: {PLUANG_WATCHLIST['us_stocks']}")
    alerts += check_us_stocks(PLUANG_WATCHLIST['us_stocks'], usd_idr)

    for alert in alerts:
        msg = format_pluang_alert(alert)
        ok  = send_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)
        logging.info(f"[{alert['ticker']}] {alert['signal']} — {'terkirim' if ok else 'GAGAL'}")

    # Price targets
    triggered = check_price_targets(usd_idr)
    for t in triggered:
        msg = format_target_alert(t)
        send_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)
        logging.info(f"[Target] {t['ticker']} tercapai @ Rp {t['current_price']:,.0f}")

    # Ringkasan portfolio (sekali sehari jam 08:00 WIT)
    if now.hour == PORTFOLIO_HOUR_UTC:
        logging.info("Kirim ringkasan portfolio harian...")
        msg = format_portfolio_summary(usd_idr)
        send_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

    if not alerts and not triggered:
        logging.info("Tidak ada sinyal baru.")


if __name__ == '__main__':
    main()
