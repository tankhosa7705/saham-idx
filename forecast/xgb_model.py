import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')


def _build_features(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
    """Feature engineering dari OHLCV."""
    data = df[['Close', 'High', 'Low', 'Volume']].copy()
    close = data['Close']

    for lag in range(1, lookback + 1):
        data[f'lag_{lag}'] = close.shift(lag)

    for w in [5, 10, 20]:
        data[f'ma_{w}']     = close.rolling(w).mean()
        data[f'std_{w}']    = close.rolling(w).std()
        data[f'ret_{w}']    = close.pct_change(w)
        data[f'ma_ratio_{w}'] = close / data[f'ma_{w}'].replace(0, np.nan)

    data['hl_pct']       = (data['High'] - data['Low']) / close.replace(0, np.nan)
    data['trend_5']      = (close - close.shift(5)) / close.shift(5).replace(0, np.nan)
    data['vol_ma10']     = data['Volume'].rolling(10).mean()
    data['vol_ratio']    = data['Volume'] / data['vol_ma10'].replace(0, np.nan)

    return data


def run_xgb_forecast(df: pd.DataFrame, periods: int = 30) -> tuple:
    """
    Forecasting dengan XGBoost.
    Returns: (forecast_df, accuracy_dict, feature_importance_df)
    forecast_df kolom: ds, yhat
    """
    try:
        from xgboost import XGBRegressor
        from sklearn.metrics import mean_absolute_error
    except ImportError:
        return None, {'error': 'XGBoost belum terinstall. Jalankan: pip install xgboost'}, None

    try:
        data = _build_features(df)
        data['target'] = data['Close'].shift(-1)
        data = data.dropna()

        if len(data) < 80:
            return None, {'error': 'Data terlalu sedikit (min 80 hari)'}, None

        feature_cols = [c for c in data.columns if c not in ['target', 'Close', 'High', 'Low', 'Volume']]
        X = data[feature_cols].values
        y = data['target'].values

        split = len(X) - 30
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        model = XGBRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            random_state=42,
            verbosity=0,
        )
        model.fit(X_train, y_train,
                  eval_set=[(X_test, y_test)],
                  verbose=False)

        y_pred = model.predict(X_test)
        mae  = float(mean_absolute_error(y_test, y_pred))
        mape = float(np.mean(np.abs((y_test - y_pred) / np.where(y_test == 0, 1, y_test))) * 100)

        # Multi-step forecast: iteratif append prediksi ke data
        current_df = df[['Close', 'High', 'Low', 'Volume']].copy()
        forecast_prices = []

        for _ in range(periods):
            feat = _build_features(current_df)
            feat = feat.dropna()
            if feat.empty:
                break
            row = feat[feature_cols].iloc[-1:].values
            next_price = float(model.predict(row)[0])
            forecast_prices.append(next_price)

            new_idx = current_df.index[-1] + pd.Timedelta(days=1)
            new_row = pd.DataFrame({
                'Close':  [next_price],
                'High':   [next_price * 1.005],
                'Low':    [next_price * 0.995],
                'Volume': [float(current_df['Volume'].tail(10).mean())],
            }, index=[new_idx])
            current_df = pd.concat([current_df, new_row])

        last_date = df.index[-1]
        bdays = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=len(forecast_prices))
        forecast_df = pd.DataFrame({'ds': bdays, 'yhat': forecast_prices})

        fi_df = pd.DataFrame({
            'feature':    feature_cols,
            'importance': model.feature_importances_,
        }).sort_values('importance', ascending=False).head(15).reset_index(drop=True)

        return forecast_df, {'MAE': mae, 'MAPE': mape}, fi_df

    except Exception as e:
        return None, {'error': str(e)}, None
