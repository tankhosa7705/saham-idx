import json
import os
from datetime import datetime

from data.fetcher import get_stock_data, IDX_STOCKS
from analysis.technical import compute_indicators
from analysis.signal import generate_signals, get_latest_signal

STATE_FILE = os.path.join(os.path.dirname(__file__), 'state.json')


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def _save_state(state: dict):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def check_stocks(tickers: list, period: str = '3mo') -> list:
    """
    Cek semua ticker, kembalikan list alert jika sinyal berubah ke BUY/SELL.
    Hanya kirim alert sekali per perubahan sinyal (tidak spam).
    """
    state  = _load_state()
    alerts = []

    for ticker in tickers:
        try:
            df = get_stock_data(ticker, period)
            if df.empty or len(df) < 50:
                continue

            df   = compute_indicators(df)
            df   = generate_signals(df)
            info = get_latest_signal(df)
            if not info:
                continue

            signal      = info.get('signal', 'HOLD')
            prev_signal = state.get(ticker, {}).get('signal', 'HOLD')

            # Alert hanya saat sinyal berubah menjadi BUY atau SELL
            if signal != prev_signal and signal in ('BUY', 'SELL'):
                alerts.append({
                    'ticker':      ticker,
                    'name':        IDX_STOCKS.get(ticker, ticker),
                    'signal':      signal,
                    'prev_signal': prev_signal,
                    'price':       info.get('close', 0),
                    'rsi':         info.get('rsi', 0),
                    'score':       info.get('score', 0),
                    'ma50':        info.get('ma50', 0),
                    'reasons':     info.get('reasons', []),
                })

            state[ticker] = {
                'signal':     signal,
                'price':      info.get('close', 0),
                'last_check': datetime.now().strftime('%Y-%m-%d %H:%M'),
            }

        except Exception as e:
            print(f"[Alert] Error {ticker}: {e}")

    _save_state(state)
    return alerts


def format_alert(alert: dict) -> str:
    signal = alert['signal']
    emoji  = '🟢' if signal == 'BUY' else '🔴'
    action = 'BELI' if signal == 'BUY' else 'JUAL'

    reasons = '\n'.join(f"  • {r}" for r in alert.get('reasons', []))
    vs_ma50 = ''
    if alert.get('ma50') and alert.get('price'):
        pct = (alert['price'] - alert['ma50']) / alert['ma50'] * 100
        vs_ma50 = f"\n📈 Vs MA50: {pct:+.1f}%"

    return (
        f"{emoji} <b>SINYAL {action} — {alert['ticker']}</b>\n"
        f"{alert['name']}\n\n"
        f"💰 Harga  : Rp {alert['price']:,.0f}"
        f"{vs_ma50}\n"
        f"📊 RSI    : {alert['rsi']:.1f}\n"
        f"⚡ Score  : {alert['score']:.2f}\n"
        f"📋 Sebelumnya: {alert['prev_signal']}\n\n"
        f"<b>Alasan:</b>\n{reasons if reasons else '  —'}\n\n"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')} WIT\n"
        f"⚠️ <i>Bukan rekomendasi investasi</i>"
    )
