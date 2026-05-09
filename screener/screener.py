import pandas as pd
import numpy as np
from data.fetcher import IDX_STOCKS, get_stock_data
from analysis.technical import compute_indicators
from analysis.signal import generate_signals, get_latest_signal


def screen_stocks(tickers: list, period: str = '3mo', progress_cb=None) -> pd.DataFrame:
    """
    Analisis semua tickers dan kembalikan DataFrame ranking.
    progress_cb: callable(current, total, ticker) opsional untuk update progress.
    """
    results = []
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        if progress_cb:
            progress_cb(i + 1, total, ticker)

        df = get_stock_data(ticker, period)
        if df.empty or len(df) < 50:
            continue

        df = compute_indicators(df)
        df = generate_signals(df)
        info = get_latest_signal(df)
        if not info:
            continue

        row = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else row

        close    = float(row['Close'])
        prev_cls = float(prev['Close'])
        chg_pct  = ((close - prev_cls) / prev_cls * 100) if prev_cls else 0.0
        ma50     = float(row.get('MA50', close) or close)
        vs_ma50  = ((close - ma50) / ma50 * 100) if ma50 else 0.0

        results.append({
            'Ticker':      ticker,
            'Nama':        IDX_STOCKS.get(ticker, ticker),
            'Harga':       round(close, 0),
            'Perubahan%':  round(chg_pct, 2),
            'RSI':         round(info.get('rsi', 0), 1),
            'Vs MA50%':    round(vs_ma50, 1),
            'MACD Hist':   round(float(row.get('MACD_hist', 0) or 0), 3),
            'Vol Ratio':   round(float(row.get('Volume_ratio', 0) or 0), 2),
            'Signal':      info.get('signal', 'HOLD'),
            'Score':       round(info.get('score', 0), 2),
        })

    if not results:
        return pd.DataFrame()

    return (pd.DataFrame(results)
              .sort_values('Score', ascending=False)
              .reset_index(drop=True))
