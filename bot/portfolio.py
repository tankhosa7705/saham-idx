import json
import os
from datetime import datetime

from data.fetcher_pluang import (
    get_gold_data, get_crypto_price_usd, get_us_stock_data,
    CRYPTO_LIST, TROY_OZ_TO_GRAM,
)
from data.fetcher import get_stock_data

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), 'portfolio.json')

_AC_LABEL = {
    'idx':      '🇮🇩 IDX',
    'gold':     '🥇 Emas',
    'crypto':   '🪙 Crypto',
    'us_stock': '🇺🇸 US Stock',
}


def load_portfolio() -> list:
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE) as f:
            data = json.load(f)
        return [x for x in data if not x.get('_note')]
    return []


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
                # GC=F: USD per troy oz → IDR per gram
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
        print(f"[Portfolio] Error harga {ticker}: {e}")
    return 0.0


def format_portfolio_summary(usd_idr: float) -> str:
    holdings = load_portfolio()
    if not holdings:
        return (
            "📂 <b>Portfolio kosong.</b>\n"
            "Edit <code>bot/portfolio.json</code> untuk menambah aset.\n\n"
            "Contoh entry:\n"
            "<pre>{\n"
            '  "ticker": "BTC",\n'
            '  "asset_class": "crypto",\n'
            '  "quantity": 0.001,\n'
            '  "avg_buy_price_idr": 1500000000,\n'
            '  "note": "Beli Mei 2026"\n'
            "}</pre>"
        )

    grouped: dict[str, list] = {}
    for item in holdings:
        grouped.setdefault(item.get('asset_class', 'idx'), []).append(item)

    lines = [f"📊 <b>Ringkasan Portfolio</b>  |  💱 USD/IDR Rp {usd_idr:,.0f}\n"]
    total_modal = total_nilai = 0.0

    for ac, items in grouped.items():
        lines.append(f"\n<b>{_AC_LABEL.get(ac, ac)}</b>")
        for item in items:
            ticker   = item['ticker']
            qty      = item.get('quantity', 0)
            avg_buy  = item.get('avg_buy_price_idr', 0)
            note     = item.get('note', '')

            current  = _current_price_idr(item, usd_idr)
            modal    = qty * avg_buy
            nilai    = qty * current
            pl       = nilai - modal
            pl_pct   = (pl / modal * 100) if modal > 0 else 0
            total_modal += modal
            total_nilai += nilai

            pl_e = '🟢' if pl >= 0 else '🔴'
            unit = 'gram' if ac == 'gold' else 'unit'
            lines.append(
                f"  <b>{ticker}</b>  {qty:g} {unit}"
                + (f"  <i>{note}</i>" if note else '') + '\n'
                f"  Beli Rp {avg_buy:,.0f}  →  Skrg Rp {current:,.0f}\n"
                f"  {pl_e} P&L: Rp {pl:+,.0f}  ({pl_pct:+.1f}%)"
            )

    total_pl    = total_nilai - total_modal
    total_pl_e  = '🟢' if total_pl >= 0 else '🔴'
    total_pl_pct = (total_pl / total_modal * 100) if total_modal > 0 else 0

    lines.append(
        f"\n{'─'*28}\n"
        f"💼 Modal : Rp {total_modal:,.0f}\n"
        f"💰 Nilai : Rp {total_nilai:,.0f}\n"
        f"{total_pl_e} P&L  : Rp {total_pl:+,.0f}  ({total_pl_pct:+.1f}%)\n"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')} WIT"
    )

    return '\n'.join(lines)
