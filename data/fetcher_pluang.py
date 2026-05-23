import yfinance as yf
import pandas as pd
import requests
import warnings
warnings.filterwarnings('ignore')

TROY_OZ_TO_GRAM = 31.1035

CRYPTO_LIST = {
    'BTC':  'bitcoin',
    'ETH':  'ethereum',
    'SOL':  'solana',
    'BNB':  'binancecoin',
    'ADA':  'cardano',
    'AVAX': 'avalanche-2',
    'DOGE': 'dogecoin',
}

CRYPTO_NAMES = {
    'BTC':  'Bitcoin',
    'ETH':  'Ethereum',
    'SOL':  'Solana',
    'BNB':  'BNB',
    'ADA':  'Cardano',
    'AVAX': 'Avalanche',
    'DOGE': 'Dogecoin',
}

US_STOCKS = {
    'AAPL':  'Apple',
    'MSFT':  'Microsoft',
    'NVDA':  'NVIDIA',
    'AMZN':  'Amazon',
    'GOOGL': 'Alphabet',
    'META':  'Meta',
    'TSLA':  'Tesla',
    'SPY':   'S&P 500 ETF',
    'QQQ':   'Nasdaq 100 ETF',
}

COINGECKO_BASE = 'https://api.coingecko.com/api/v3'
_HEADERS = {'Accept': 'application/json', 'User-Agent': 'saham-idx-bot/1.0'}


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index)
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df.dropna()


def get_usd_idr() -> float:
    try:
        df = yf.download('IDR=X', period='5d', auto_adjust=True, progress=False)
        df = _clean_df(df)
        if not df.empty:
            return float(df['Close'].iloc[-1])
    except Exception:
        pass
    return 16200.0


def get_gold_data(period: str = '3mo') -> pd.DataFrame:
    """OHLCV emas (XAU/USD per troy oz) dari yfinance."""
    try:
        df = yf.download('GC=F', period=period, auto_adjust=True, progress=False)
        return _clean_df(df)
    except Exception:
        return pd.DataFrame()


def get_gold_price_idr(usd_idr: float) -> float:
    """Harga emas per gram dalam IDR."""
    df = get_gold_data('5d')
    if df.empty:
        return 0.0
    price_usd_per_oz = float(df['Close'].iloc[-1])
    return price_usd_per_oz * usd_idr / TROY_OZ_TO_GRAM


def get_crypto_ohlcv(coin_id: str, days: int = 90) -> pd.DataFrame:
    """OHLCV crypto dari CoinGecko (gratis, tanpa API key)."""
    try:
        r = requests.get(
            f"{COINGECKO_BASE}/coins/{coin_id}/ohlc",
            params={'vs_currency': 'usd', 'days': days},
            headers=_HEADERS, timeout=15
        )
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data, columns=['timestamp', 'Open', 'High', 'Low', 'Close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        df['Volume'] = 0.0
        return df.dropna()
    except Exception:
        return pd.DataFrame()


def get_crypto_price_usd(coin_id: str) -> float:
    """Harga crypto terkini dalam USD dari CoinGecko."""
    try:
        r = requests.get(
            f"{COINGECKO_BASE}/simple/price",
            params={'ids': coin_id, 'vs_currencies': 'usd'},
            headers=_HEADERS, timeout=10
        )
        r.raise_for_status()
        return float(r.json().get(coin_id, {}).get('usd', 0))
    except Exception:
        return 0.0


def get_us_stock_data(ticker: str, period: str = '3mo') -> pd.DataFrame:
    """OHLCV US stock/ETF dari yfinance (tanpa .JK)."""
    try:
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        return _clean_df(df)
    except Exception:
        return pd.DataFrame()
