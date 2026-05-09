"""
Jalankan dengan: python scheduler.py
Bot akan cek sinyal saham secara otomatis dan kirim notifikasi ke Telegram.
"""
import time
import logging
import schedule
from datetime import datetime

from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, WATCH_LIST, CHECK_INTERVAL_MINUTES, DATA_PERIOD
from bot.telegram import send_message
from bot.alert import check_stocks, format_alert

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s — %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('bot/scheduler.log', encoding='utf-8'),
        logging.StreamHandler(),
    ]
)


def run_check():
    # Skip weekend (Sabtu=5, Minggu=6) — bursa tutup
    if datetime.now().weekday() >= 5:
        logging.info("Weekend — bursa tutup, skip.")
        return

    logging.info(f"Mengecek {len(WATCH_LIST)} saham: {', '.join(WATCH_LIST)}")
    try:
        alerts = check_stocks(WATCH_LIST, DATA_PERIOD)

        if alerts:
            for alert in alerts:
                msg = format_alert(alert)
                ok  = send_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)
                status = "✅ terkirim" if ok else "❌ gagal"
                logging.info(f"  [{alert['ticker']}] {alert['signal']} — {status}")
        else:
            logging.info("  Tidak ada sinyal baru.")

    except Exception as e:
        logging.error(f"Error saat cek: {e}")
        send_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
                     f"⚠️ <b>Bot Error</b>\n{e}\n{datetime.now().strftime('%d/%m/%Y %H:%M')}")


def main():
    # Validasi config
    if 'ISI_' in TELEGRAM_TOKEN or 'ISI_' in str(TELEGRAM_CHAT_ID):
        print("❌ ERROR: Isi dulu TELEGRAM_TOKEN dan TELEGRAM_CHAT_ID di config.py!")
        return

    logging.info("=" * 50)
    logging.info("  Saham IDX Alert Bot — STARTED")
    logging.info(f"  Watch list : {', '.join(WATCH_LIST)}")
    logging.info(f"  Interval   : setiap {CHECK_INTERVAL_MINUTES} menit")
    logging.info("=" * 50)

    # Notifikasi startup ke Telegram
    send_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
        f"🤖 <b>Saham IDX Alert Bot aktif!</b>\n"
        f"Memantau: {', '.join(WATCH_LIST)}\n"
        f"Cek setiap {CHECK_INTERVAL_MINUTES} menit\n"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Langsung cek saat pertama start
    run_check()

    # Jadwalkan cek berikutnya
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(run_check)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == '__main__':
    main()
