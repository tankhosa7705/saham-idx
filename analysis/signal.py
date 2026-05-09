import pandas as pd
import numpy as np


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate sinyal BUY/SELL/HOLD berdasarkan kombinasi indikator teknikal."""
    df = df.copy()
    score = pd.Series(0.0, index=df.index)

    close = df['Close'].squeeze()

    # 1. Golden Cross / Death Cross (MA20 vs MA50) — bobot 2
    if 'MA20' in df and 'MA50' in df:
        ma20, ma50 = df['MA20'].squeeze(), df['MA50'].squeeze()
        df['Golden_Cross'] = (ma20 > ma50) & (ma20.shift(1) <= ma50.shift(1))
        df['Death_Cross']  = (ma20 < ma50) & (ma20.shift(1) >= ma50.shift(1))
        score += df['Golden_Cross'].astype(float) * 2
        score -= df['Death_Cross'].astype(float) * 2
        score += ((ma20 > ma50).astype(float) - 0.5) * 0.5  # trend bias

    # 2. RSI — bobot 2 saat crossover, +0.5 trend bias
    if 'RSI' in df:
        rsi = df['RSI'].squeeze()
        df['RSI_Buy']  = (rsi < 30) & (rsi.shift(1) >= 30)
        df['RSI_Sell'] = (rsi > 70) & (rsi.shift(1) <= 70)
        score += df['RSI_Buy'].astype(float) * 2
        score -= df['RSI_Sell'].astype(float) * 2
        score += ((rsi > 50).astype(float) - 0.5) * 0.5

    # 3. MACD crossover — bobot 1.5
    if 'MACD' in df and 'MACD_signal' in df:
        macd, sig = df['MACD'].squeeze(), df['MACD_signal'].squeeze()
        df['MACD_Buy']  = (macd > sig) & (macd.shift(1) <= sig.shift(1))
        df['MACD_Sell'] = (macd < sig) & (macd.shift(1) >= sig.shift(1))
        score += df['MACD_Buy'].astype(float) * 1.5
        score -= df['MACD_Sell'].astype(float) * 1.5
        score += ((macd > sig).astype(float) - 0.5) * 0.3

    # 4. Bollinger Bands — bobot 1
    if 'BB_lower' in df and 'BB_upper' in df:
        df['BB_Buy']  = close < df['BB_lower'].squeeze()
        df['BB_Sell'] = close > df['BB_upper'].squeeze()
        score += df['BB_Buy'].astype(float)
        score -= df['BB_Sell'].astype(float)

    # 5. Price vs MA50 — bobot 0.5
    if 'MA50' in df:
        above_ma50 = close > df['MA50'].squeeze()
        score += (above_ma50.astype(float) - 0.5) * 0.5

    # 6. Volume confirmation — amplifikasi jika volume tinggi
    if 'Volume_ratio' in df:
        high_vol = df['Volume_ratio'].squeeze() > 1.5
        score = score * (1 + high_vol.astype(float) * 0.25)

    df['Signal_Score'] = score
    df['Signal'] = 'HOLD'
    df.loc[score >= 2.0,  'Signal'] = 'BUY'
    df.loc[score <= -2.0, 'Signal'] = 'SELL'

    return df


def get_latest_signal(df: pd.DataFrame) -> dict:
    """Ringkasan sinyal terbaru."""
    if df.empty or 'Signal' not in df.columns:
        return {}

    row = df.iloc[-1]
    reasons = []

    for col, msg in [
        ('Golden_Cross', 'Golden Cross — MA20 melewati MA50 ke atas'),
        ('Death_Cross',  'Death Cross — MA20 melewati MA50 ke bawah'),
        ('RSI_Buy',      f"RSI Oversold ({row.get('RSI', 0):.1f})"),
        ('RSI_Sell',     f"RSI Overbought ({row.get('RSI', 0):.1f})"),
        ('MACD_Buy',     'MACD Bullish Crossover'),
        ('MACD_Sell',    'MACD Bearish Crossover'),
        ('BB_Buy',       'Harga di bawah Lower Bollinger Band'),
        ('BB_Sell',      'Harga di atas Upper Bollinger Band'),
    ]:
        if row.get(col, False):
            reasons.append(msg)

    return {
        'signal':      row.get('Signal', 'HOLD'),
        'score':       float(row.get('Signal_Score', 0)),
        'rsi':         float(row.get('RSI', 0)),
        'macd':        float(row.get('MACD', 0)),
        'macd_signal': float(row.get('MACD_signal', 0)),
        'close':       float(row.get('Close', 0)),
        'ma20':        float(row.get('MA20', 0)),
        'ma50':        float(row.get('MA50', 0)),
        'reasons':     reasons,
    }
