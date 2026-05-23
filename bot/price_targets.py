import json
import os
from datetime import datetime

from data.fetcher_pluang import (
    get_gold_data, get_crypto_price_usd, get_us_stock_data,
    CRYPTO_LIST, TROY_OZ_TO_GRAM,
)
from data.fetcher import get_stock_data

TARGETS_FILE = os.path.join(os.path.dirname(__file__), 'price_targets.json')


def load_targets() -> list:
    if os.path.exists(TARGETS_FILE):
        with open(TARGETS_FILE) as f:
            data = json.load(f)
        return [x for x in data if not x.get('_note')]
    return []


def save_targets(targets: list):
    with open(TARGETS_FILE, 'w') as f:
        json.dump(targets, f, indent=2)


def _current_price_idr(item: dict, usd_idr: float) -> float:
    ac     = item.get('asset_class', 'idx')
    ticker = item.get('ticker', '')
    try:
        if ac == 'idx':
            df = get_stock_data(ticker, period='5d')
            if not df.empty:
                return float(df['Close'].iloc[-1])
        elif ac == 'gold':
            df = get_gold_data('5d')
            if not df.empty:
                return float(df['Close'].iloc[-1]) * usd_idr / TROY_OZ_TO_GRAM
        elif ac == 'crypto':
            coin_id = CRYPTO_LIST.get(ticker)
            if coin_id:
                return get_crypto_price_usd(coin_id) * usd_idr
        elif ac == 'us_stock':
            df = get_us_stock_data(ticker, period='5d')
            if not df.empty:
                return float(df['Close'].iloc[-1]) * usd_idr
    except Exception as e:
        print(f"[Target] Error harga {ticker}: {e}")
    return 0.0


def check_price_targets(usd_idr: float) -> list:
    """Kembalikan list target yang sudah tercapai, lalu hapus dari file."""
    targets = load_targets()
    if not targets:
        return []

    triggered = []
    remaining = []

    for t in targets:
        current = _current_price_idr(t, usd_idr)
        if current == 0:
            remaining.append(t)
            continue

        direction    = t.get('direction', 'above')
        target_price = float(t.get('target_price', 0))

        hit = (direction == 'above' and current >= target_price) or \
              (direction == 'below' and current <= target_price)

        if hit:
            triggered.append({**t, 'current_price': current})
        else:
            remaining.append(t)

    if triggered:
        save_targets(remaining)

    return triggered


def format_target_alert(t: dict) -> str:
    direction_str = '📈 naik ke' if t.get('direction') == 'above' else '📉 turun ke'
    note = t.get('note', '')
    return (
        f"🎯 <b>TARGET TERCAPAI — {t['ticker']}</b>\n"
        + (f"{note}\n" if note else '')
        + f"\nTarget : Rp {t['target_price']:,.0f} ({direction_str})\n"
        f"Skrg   : Rp {t['current_price']:,.0f}\n"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')} WIT"
    )
