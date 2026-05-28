"""
Kirim ringkasan sinyal harian ke Telegram setiap pagi 09:00 WIT.
Dijalankan via GitHub Actions workflow daily_summary.yml.
"""
import json
import logging
import os
from datetime import datetime

from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, WATCH_LIST, DATA_PERIOD
from bot.telegram import send_message
from data.fetcher import get_stock_data, IDX_STOCKS
from analysis.technical import compute_indicators
from analysis.signal import generate_signals, get_latest_signal

logging.basicConfig(level=logging.INFO, format='%(asctime)s — %(message)s')

STATE_FILE = os.path.join(os.path.dirname(__file__), 'bot', 'state.json')


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def format_summary(results: list, date_str: str) -> str:
    buy_list  = [r for r in results if r['signal'] == 'BUY']
    sell_list = [r for r in results if r['signal'] == 'SELL']
    hold_list = [r for r in results if r['signal'] == 'HOLD']
    err_list  = [r for r in results if r['signal'] == 'ERROR']

    lines = [
        f"📋 <b>RINGKASAN SINYAL HARIAN</b>",
        f"📅 {date_str} • IDX",
        f"",
    ]

    if buy_list:
        lines.append(f"🟢 <b>BUY ({len(buy_list)})</b>")
        for r in buy_list:
            lines.append(f"  • <b>{r['ticker']}</b> — Rp {r['price']:,.0f}  |  RSI {r['rsi']:.0f}  |  Score {r['score']:+.1f}")
        lines.append("")

    if sell_list:
        lines.append(f"🔴 <b>SELL ({len(sell_list)})</b>")
        for r in sell_list:
            lines.append(f"  • <b>{r['ticker']}</b> — Rp {r['price']:,.0f}  |  RSI {r['rsi']:.0f}  |  Score {r['score']:+.1f}")
        lines.append("")

    if hold_list:
        tickers_hold = ', '.join(r['ticker'] for r in hold_list)
        lines.append(f"⚪ <b>HOLD ({len(hold_list)})</b>: {tickers_hold}")
        lines.append("")

    if err_list:
        tickers_err = ', '.join(r['ticker'] for r in err_list)
        lines.append(f"⚠️ Gagal fetch: {tickers_err}")
        lines.append("")

    lines.append(f"⚠️ <i>Bukan rekomendasi investasi</i>")
    return '\n'.join(lines)


def main():
    if not TELEGRAM_TOKEN or 'ISI_' in TELEGRAM_TOKEN:
        print("ERROR: TELEGRAM_TOKEN belum di-set")
        return

    # Skip weekend
    if datetime.utcnow().weekday() >= 5:
        logging.info("Weekend — skip.")
        return

    wit_now  = datetime.utcnow()
    date_str = wit_now.strftime('%A, %d %b %Y')  # akan tampil hari dalam bahasa Inggris

    logging.info(f"Menyiapkan ringkasan harian untuk {len(WATCH_LIST)} saham...")

    results = []
    for ticker in WATCH_LIST:
        try:
            df = get_stock_data(ticker, DATA_PERIOD)
            if df.empty or len(df) < 50:
                results.append({'ticker': ticker, 'signal': 'ERROR', 'price': 0, 'rsi': 0, 'score': 0})
                continue

            df   = compute_indicators(df)
            df   = generate_signals(df)
            info = get_latest_signal(df)

            results.append({
                'ticker': ticker,
                'signal': info.get('signal', 'HOLD'),
                'price':  info.get('close', 0),
                'rsi':    info.get('rsi', 0),
                'score':  info.get('score', 0),
            })
            logging.info(f"  {ticker}: {info.get('signal','?')} (RSI {info.get('rsi',0):.1f})")
        except Exception as e:
            logging.error(f"  {ticker}: ERROR — {e}")
            results.append({'ticker': ticker, 'signal': 'ERROR', 'price': 0, 'rsi': 0, 'score': 0})

    msg = format_summary(results, date_str)
    ok  = send_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)
    logging.info(f"Ringkasan terkirim: {ok}")

    if not ok:
        logging.error("Gagal kirim ringkasan ke Telegram.")


if __name__ == '__main__':
    main()
