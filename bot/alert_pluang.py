import json
import os
from datetime import datetime

from data.fetcher_pluang import (
    get_gold_data, get_crypto_ohlcv, get_us_stock_data, get_usd_idr,
    CRYPTO_LIST, CRYPTO_NAMES, US_STOCKS, TROY_OZ_TO_GRAM,
)
from analysis.technical import compute_indicators
from analysis.signal import generate_signals, get_latest_signal

STATE_FILE = os.path.join(os.path.dirname(__file__), 'state_pluang.json')


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def _save_state(state: dict):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def _make_alert(ticker, name, asset_class, signal, info, usd_idr, state) -> dict | None:
    prev_signal = state.get(ticker, {}).get('signal', 'HOLD')
    if signal == prev_signal or signal not in ('BUY', 'SELL'):
        return None
    price_usd = info.get('close', 0)
    return {
        'ticker':      ticker,
        'name':        name,
        'asset_class': asset_class,
        'signal':      signal,
        'prev_signal': prev_signal,
        'price_usd':   price_usd,
        'price_idr':   price_usd * usd_idr,
        'rsi':         info.get('rsi', 0),
        'score':       info.get('score', 0),
        'ma50':        info.get('ma50', 0),
        'reasons':     info.get('reasons', []),
    }


def check_gold(usd_idr: float) -> list:
    state = _load_state()
    alerts = []
    try:
        df = get_gold_data('3mo')
        if df.empty or len(df) < 50:
            return alerts
        df = compute_indicators(df)
        df = generate_signals(df)
        info = get_latest_signal(df)
        if not info:
            return alerts

        signal = info.get('signal', 'HOLD')
        price_usd = info.get('close', 0)
        price_idr_gram = price_usd * usd_idr / TROY_OZ_TO_GRAM

        alert = _make_alert('XAUUSD', 'Emas (Gold)', 'gold', signal, info, usd_idr, state)
        if alert:
            alert['price_idr_gram'] = price_idr_gram
            alerts.append(alert)

        state['XAUUSD'] = {
            'signal':        signal,
            'price_usd_oz':  price_usd,
            'price_idr_gram': price_idr_gram,
            'last_check':    datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
    except Exception as e:
        print(f"[Gold] Error: {e}")
    _save_state(state)
    return alerts


def check_crypto(tickers: list, usd_idr: float) -> list:
    state = _load_state()
    alerts = []
    for ticker in tickers:
        coin_id = CRYPTO_LIST.get(ticker)
        if not coin_id:
            continue
        try:
            df = get_crypto_ohlcv(coin_id, days=90)
            if df.empty or len(df) < 30:
                continue
            df = compute_indicators(df)
            df = generate_signals(df)
            info = get_latest_signal(df)
            if not info:
                continue

            signal = info.get('signal', 'HOLD')
            alert = _make_alert(ticker, CRYPTO_NAMES.get(ticker, ticker), 'crypto', signal, info, usd_idr, state)
            if alert:
                alerts.append(alert)

            state[ticker] = {
                'signal':     signal,
                'price_usd':  info.get('close', 0),
                'price_idr':  info.get('close', 0) * usd_idr,
                'last_check': datetime.now().strftime('%Y-%m-%d %H:%M'),
            }
        except Exception as e:
            print(f"[Crypto] Error {ticker}: {e}")
    _save_state(state)
    return alerts


def check_us_stocks(tickers: list, usd_idr: float) -> list:
    state = _load_state()
    alerts = []
    for ticker in tickers:
        try:
            df = get_us_stock_data(ticker, period='3mo')
            if df.empty or len(df) < 50:
                continue
            df = compute_indicators(df)
            df = generate_signals(df)
            info = get_latest_signal(df)
            if not info:
                continue

            signal = info.get('signal', 'HOLD')
            alert = _make_alert(ticker, US_STOCKS.get(ticker, ticker), 'us_stock', signal, info, usd_idr, state)
            if alert:
                alerts.append(alert)

            state[ticker] = {
                'signal':     signal,
                'price_usd':  info.get('close', 0),
                'price_idr':  info.get('close', 0) * usd_idr,
                'last_check': datetime.now().strftime('%Y-%m-%d %H:%M'),
            }
        except Exception as e:
            print(f"[US] Error {ticker}: {e}")
    _save_state(state)
    return alerts


def format_pluang_alert(alert: dict) -> str:
    signal = alert['signal']
    emoji_s = '🟢' if signal == 'BUY' else '🔴'
    action  = 'BELI' if signal == 'BUY' else 'JUAL'

    ac = alert.get('asset_class', '')
    if ac == 'gold':
        emoji_a   = '🥇'
        price_str = (f"${alert['price_usd']:,.2f}/troy oz\n"
                     f"   ≈ Rp {alert.get('price_idr_gram', 0):,.0f}/gram")
    elif ac == 'crypto':
        emoji_a   = '₿' if alert['ticker'] == 'BTC' else '🪙'
        price_str = (f"${alert['price_usd']:,.4f}\n"
                     f"   ≈ Rp {alert['price_idr']:,.0f}")
    else:
        emoji_a   = '🇺🇸'
        price_str = (f"${alert['price_usd']:,.2f}\n"
                     f"   ≈ Rp {alert['price_idr']:,.0f}")

    reasons = '\n'.join(f"  • {r}" for r in alert.get('reasons', []))
    vs_ma50 = ''
    if alert.get('ma50') and alert.get('price_usd'):
        pct = (alert['price_usd'] - alert['ma50']) / alert['ma50'] * 100
        vs_ma50 = f"\n📈 Vs MA50: {pct:+.1f}%"

    return (
        f"{emoji_s} <b>SINYAL {action} — {alert['ticker']}</b> {emoji_a}\n"
        f"{alert['name']}\n\n"
        f"💰 Harga : {price_str}"
        f"{vs_ma50}\n"
        f"📊 RSI   : {alert['rsi']:.1f}\n"
        f"⚡ Score  : {alert['score']:.2f}\n"
        f"📋 Sebelumnya: {alert['prev_signal']}\n\n"
        f"<b>Alasan:</b>\n{reasons if reasons else '  —'}\n\n"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')} WIT\n"
        f"⚠️ <i>Bukan rekomendasi investasi</i>"
    )
