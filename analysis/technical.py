import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

try:
    import ta
    HAS_TA = True
except ImportError:
    HAS_TA = False


def _rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _bollinger(series: pd.Series, window=20, std=2):
    mid = series.rolling(window).mean()
    deviation = series.rolling(window).std()
    upper = mid + std * deviation
    lower = mid - std * deviation
    pct = (series - lower) / (upper - lower).replace(0, np.nan)
    return upper, mid, lower, pct


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window=14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Tambahkan indikator teknikal ke DataFrame OHLCV."""
    df = df.copy()
    close = df['Close'].squeeze()
    high  = df['High'].squeeze()
    low   = df['Low'].squeeze()
    vol   = df['Volume'].squeeze()

    # Moving Averages
    for n in [5, 20, 50, 200]:
        df[f'MA{n}'] = close.rolling(n).mean()
    df['EMA12'] = close.ewm(span=12, adjust=False).mean()
    df['EMA26'] = close.ewm(span=26, adjust=False).mean()

    # RSI
    if HAS_TA:
        df['RSI'] = ta.momentum.RSIIndicator(close, window=14).rsi()
        macd_ind = ta.trend.MACD(close)
        df['MACD']        = macd_ind.macd()
        df['MACD_signal'] = macd_ind.macd_signal()
        df['MACD_hist']   = macd_ind.macd_diff()
        bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        df['BB_upper']  = bb.bollinger_hband()
        df['BB_middle'] = bb.bollinger_mavg()
        df['BB_lower']  = bb.bollinger_lband()
        df['BB_pct']    = bb.bollinger_pband()
        df['ATR'] = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()
    else:
        df['RSI'] = _rsi(close)
        df['MACD'], df['MACD_signal'], df['MACD_hist'] = _macd(close)
        df['BB_upper'], df['BB_middle'], df['BB_lower'], df['BB_pct'] = _bollinger(close)
        df['ATR'] = _atr(high, low, close)

    # Volume
    df['Volume_MA20']  = vol.rolling(20).mean()
    df['Volume_ratio'] = vol / df['Volume_MA20'].replace(0, np.nan)

    # Return
    df['Change_pct'] = close.pct_change() * 100

    return df
