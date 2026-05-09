import yfinance as yf
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

IDX_STOCKS = {
    # Perbankan
    'BBCA': 'Bank Central Asia',
    'BBRI': 'Bank Rakyat Indonesia',
    'BMRI': 'Bank Mandiri',
    'BBNI': 'Bank Negara Indonesia',
    'BRIS': 'Bank Syariah Indonesia',
    # Telekomunikasi
    'TLKM': 'Telkom Indonesia',
    'EXCL': 'XL Axiata',
    'ISAT': 'Indosat Ooredoo',
    # Otomotif & Industri
    'ASII': 'Astra International',
    # Consumer
    'UNVR': 'Unilever Indonesia',
    'ICBP': 'Indofood CBP',
    'INDF': 'Indofood',
    'MYOR': 'Mayora Indah',
    'KLBF': 'Kalbe Farma',
    'SIDO': 'Industri Jamu Sido',
    'ACES': 'Ace Hardware Indonesia',
    # Energi & Tambang
    'BYAN': 'Bayan Resources',
    'ADRO': 'Adaro Energy',
    'PTBA': 'Bukit Asam',
    'ANTM': 'Aneka Tambang',
    'INCO': 'Vale Indonesia',
    'MDKA': 'Merdeka Copper Gold',
    # Infrastruktur
    'JSMR': 'Jasa Marga',
    'PGAS': 'PGN',
    'SMGR': 'Semen Indonesia',
    'TOWR': 'Sarana Menara Nusantara',
    'TBIG': 'Tower Bersama Infrastructure',
    # Properti
    'PWON': 'Pakuwon Jati',
    'BSDE': 'Bumi Serpong Damai',
    # Media & Teknologi
    'EMTK': 'Elang Mahkota Teknologi',
    # Lainnya
    'CPIN': 'Charoen Pokphand Indonesia',
    'JPFA': 'Japfa Comfeed Indonesia',
    'MAPI': 'Mitra Adiperkasa',
    'ULTJ': 'Ultra Jaya Milk',
    'HMSP': 'HM Sampoerna',
    'GGRM': 'Gudang Garam',
}


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten MultiIndex columns if present and drop NaN rows."""
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index)
    # Remove timezone info from index
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df.dropna()


def get_stock_data(ticker: str, period: str = '2y') -> pd.DataFrame:
    """
    Download OHLCV data saham IDX dari yfinance.
    ticker: kode saham tanpa .JK (contoh: 'BBCA')
    period: '1mo','3mo','6mo','1y','2y','5y'
    """
    try:
        df = yf.download(f"{ticker}.JK", period=period, auto_adjust=True, progress=False)
        return _clean_df(df)
    except Exception:
        return pd.DataFrame()


def get_ticker_info(ticker: str) -> dict:
    """Ambil info fundamental dari yfinance."""
    try:
        info = yf.Ticker(f"{ticker}.JK").info
        return {
            'name': info.get('longName', IDX_STOCKS.get(ticker, ticker)),
            'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
            'prev_close': info.get('previousClose', 0),
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE', None),
            'sector': info.get('sector', '-'),
        }
    except Exception:
        return {}
