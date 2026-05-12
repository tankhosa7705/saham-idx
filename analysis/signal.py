import pandas as pd
import numpy as np


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate sinyal BUY/SELL/HOLD berdasarkan posisi indikator (persistent scoring)."""
    df = df.copy()
    score = pd.Series(0.0, index=df.index)

    close = df['Close'].squeeze()

    # 1. MA Trend — MA20 vs MA50 (bobot 1.5)
    if 'MA20' in df and 'MA50' in df:
        ma20, ma50 = df['MA20'].squeeze(), df['MA50'].squeeze()
        score += (ma20 > ma50).astype(float) * 1.5
        score -= (ma20 < ma50).astype(float) * 1.5

    # 2. RSI level (bobot 2.0 di zona ekstrem, 0.5 di zona menengah)
    if 'RSI' in df:
        rsi = df['RSI'].squeeze()
        score += (rsi < 30).astype(float) * 2.0           # oversold kuat
        score += ((rsi >= 30) & (rsi < 45)).astype(float) * 0.5  # oversold ringan
        score -= ((rsi > 55) & (rsi <= 70)).astype(float) * 0.5  # overbought ringan
        score -= (rsi > 70).astype(float) * 2.0           # overbought kuat

    # 3. MACD posisi vs signal line (bobot 1.0)
    if 'MACD' in df and 'MACD_signal' in df:
        macd, sig = df['MACD'].squeeze(), df['MACD_signal'].squeeze()
        score += (macd > sig).astype(float) * 1.0
        score -= (macd < sig).astype(float) * 1.0

    # 4. Bollinger Bands (bobot 1.0)
    if 'BB_lower' in df and 'BB_upper' in df:
        score += (close < df['BB_lower'].squeeze()).astype(float) * 1.0
        score -= (close > df['BB_upper'].squeeze()).astype(float) * 1.0

    # 5. Price vs MA50 (bobot 0.5, hanya kalau selisih >2%)
    if 'MA50' in df:
        vs_ma50 = (close - df['MA50'].squeeze()) / df['MA50'].squeeze()
        score += (vs_ma50 > 0.02).astype(float) * 0.5
        score -= (vs_ma50 < -0.02).astype(float) * 0.5

    # 6. Volume confirmation — amplifikasi 20% jika volume tinggi
    if 'Volume_ratio' in df:
        high_vol = df['Volume_ratio'].squeeze() > 1.5
        score = score * (1 + high_vol.astype(float) * 0.2)

    df['Signal_Score'] = score
    df['Signal'] = 'HOLD'
    df.loc[score >= 2.5,  'Signal'] = 'BUY'
    df.loc[score <= -2.5, 'Signal'] = 'SELL'

    return df


def get_latest_signal(df: pd.DataFrame) -> dict:
    """Ringkasan sinyal terbaru."""
    if df.empty or 'Signal' not in df.columns:
        return {}

    row = df.iloc[-1]
    rsi      = float(row.get('RSI', 50) or 50)
    close    = float(row.get('Close', 0) or 0)
    ma20     = float(row.get('MA20', 0) or 0)
    ma50     = float(row.get('MA50', 0) or 0)
    macd     = float(row.get('MACD', 0) or 0)
    macd_sig = float(row.get('MACD_signal', 0) or 0)
    bb_lower = float(row.get('BB_lower', 0) or 0)
    bb_upper = float(row.get('BB_upper', 0) or 0)

    reasons = []
    if ma20 and ma50:
        if ma20 > ma50:
            reasons.append(f'MA20 di atas MA50 (uptrend)')
        else:
            reasons.append(f'MA20 di bawah MA50 (downtrend)')

    if rsi < 30:
        reasons.append(f'RSI Oversold ({rsi:.1f})')
    elif rsi > 70:
        reasons.append(f'RSI Overbought ({rsi:.1f})')
    elif rsi < 45:
        reasons.append(f'RSI recovering dari oversold ({rsi:.1f})')

    if macd > macd_sig:
        reasons.append('MACD di atas Signal (momentum bullish)')
    elif macd < macd_sig:
        reasons.append('MACD di bawah Signal (momentum bearish)')

    if bb_lower and close < bb_lower:
        reasons.append('Harga di bawah Lower Bollinger Band')
    elif bb_upper and close > bb_upper:
        reasons.append('Harga di atas Upper Bollinger Band')

    return {
        'signal':      row.get('Signal', 'HOLD'),
        'score':       float(row.get('Signal_Score', 0)),
        'rsi':         rsi,
        'macd':        macd,
        'macd_signal': macd_sig,
        'close':       close,
        'ma20':        ma20,
        'ma50':        ma50,
        'reasons':     reasons,
    }
