"""
Versi one-shot scheduler — dijalankan via GitHub Actions setiap jam.
Cek sinyal sekali lalu keluar.
"""
import logging
from datetime import datetime

from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, WATCH_LIST, DATA_PERIOD
from bot.telegram import send_message
from bot.alert import check_stocks, format_alert

logging.basicConfig(level=logging.INFO, format='%(asctime)s — %(message)s')


def main():
    if not TELEGRAM_TOKEN or 'ISI_' in TELEGRAM_TOKEN:
        print("ERROR: TELEGRAM_TOKEN belum di-set di GitHub Secrets")
        return

    # Skip weekend
    if datetime.utcnow().weekday() >= 5:
        logging.info("Weekend — bursa tutup, skip.")
        return

    logging.info(f"Cek {len(WATCH_LIST)} saham: {', '.join(WATCH_LIST)}")

    try:
        alerts = check_stocks(WATCH_LIST, DATA_PERIOD)

        if alerts:
            for alert in alerts:
                msg = format_alert(alert)
                ok = send_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)
                logging.info(f"[{alert['ticker']}] {alert['signal']} — {'terkirim' if ok else 'GAGAL'}")
        else:
            logging.info("Tidak ada sinyal baru.")

    except Exception as e:
        logging.error(f"Error: {e}")
        send_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
                     f"⚠️ <b>Bot Error</b>\n{e}\n{datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC")


if __name__ == '__main__':
    main()
