import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')


def run_prophet_forecast(df: pd.DataFrame, periods: int = 30) -> tuple:
    """
    Forecasting dengan Prophet.
    Returns: (forecast_df, accuracy_dict)
    forecast_df memiliki kolom: ds, yhat, yhat_lower, yhat_upper
    accuracy_dict: {'MAE': ..., 'MAPE': ...} atau {'error': ...}
    """
    try:
        from prophet import Prophet
    except ImportError:
        return None, {'error': 'Prophet belum terinstall. Jalankan: pip install prophet'}

    try:
        prophet_df = df[['Close']].copy().reset_index()
        prophet_df.columns = ['ds', 'y']
        prophet_df['ds'] = pd.to_datetime(prophet_df['ds'])
        if hasattr(prophet_df['ds'].dt, 'tz') and prophet_df['ds'].dt.tz is not None:
            prophet_df['ds'] = prophet_df['ds'].dt.tz_localize(None)
        prophet_df['y'] = prophet_df['y'].astype(float)
        prophet_df = prophet_df.dropna()

        if len(prophet_df) < 60:
            return None, {'error': 'Data terlalu sedikit (min 60 hari)'}

        # Validasi: latih di luar 30 hari terakhir
        val_size = 30
        train = prophet_df.iloc[:-val_size]
        val   = prophet_df.iloc[-val_size:]

        model = Prophet(
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10,
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
        )
        # Jangan tambah Indonesian holidays — bisa error jika paket holidays tidak ada
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            model.fit(train)

        # Validasi akurasi
        future_val = model.make_future_dataframe(periods=val_size, freq='B')
        fc_val = model.predict(future_val)
        merged = val.merge(fc_val[['ds', 'yhat']], on='ds', how='inner')
        if not merged.empty:
            mae  = float(np.mean(np.abs(merged['y'] - merged['yhat'])))
            mape = float(np.mean(np.abs((merged['y'] - merged['yhat']) / merged['y'].replace(0, np.nan))) * 100)
        else:
            mae, mape = 0.0, 0.0

        # Re-train dengan semua data untuk forecast ke depan
        model2 = Prophet(
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10,
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
        )
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            model2.fit(prophet_df)

        future = model2.make_future_dataframe(periods=periods, freq='B')
        forecast = model2.predict(future)

        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']], {'MAE': mae, 'MAPE': mape}

    except Exception as e:
        return None, {'error': str(e)}
