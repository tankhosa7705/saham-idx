import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from forecast.xgb_model import run_xgb_forecast
from forecast.prophet_model import run_prophet_forecast


def run_ensemble_forecast(df: pd.DataFrame, periods: int = 30) -> tuple:
    """
    Ensemble XGBoost + Prophet dengan bobot berdasarkan akurasi (inverse MAPE).
    Returns: (xgb_fc, prophet_fc, ensemble_df, ensemble_acc, xgb_fi)
    """
    xgb_fc, xgb_acc, xgb_fi = run_xgb_forecast(df, periods)
    prophet_fc, prophet_acc = run_prophet_forecast(df, periods)

    xgb_ok = xgb_fc is not None and 'error' not in xgb_acc
    prophet_ok = prophet_fc is not None and 'error' not in prophet_acc

    if not xgb_ok and not prophet_ok:
        return None, None, None, {'error': 'Kedua model gagal'}, None

    if not xgb_ok:
        return None, prophet_fc, None, prophet_acc, None

    if not prophet_ok:
        return xgb_fc, None, None, xgb_acc, xgb_fi

    last_date = df.index[-1]
    prophet_future = prophet_fc[prophet_fc['ds'] > last_date][
        ['ds', 'yhat', 'yhat_lower', 'yhat_upper']
    ].copy().reset_index(drop=True)

    merged = xgb_fc.merge(
        prophet_future,
        on='ds', how='inner',
        suffixes=('_xgb', '_prophet'),
    )

    if merged.empty:
        return xgb_fc, prophet_fc, None, xgb_acc, xgb_fi

    # Bobot: semakin kecil MAPE, semakin besar bobot
    xgb_mape = max(xgb_acc.get('MAPE', 50), 0.01)
    prp_mape = max(prophet_acc.get('MAPE', 50), 0.01)
    inv_xgb = 1 / xgb_mape
    inv_prp = 1 / prp_mape
    total   = inv_xgb + inv_prp
    w_xgb   = inv_xgb / total
    w_prp   = inv_prp / total

    yhat_ens = w_xgb * merged['yhat_xgb'] + w_prp * merged['yhat_prophet']

    ensemble_df = pd.DataFrame({
        'ds':           merged['ds'],
        'yhat':         yhat_ens,
        'yhat_lower':   merged['yhat_lower'],
        'yhat_upper':   merged['yhat_upper'],
        'yhat_xgb':     merged['yhat_xgb'],
        'yhat_prophet': merged['yhat_prophet'],
    })

    ensemble_acc = {
        'MAE':            w_xgb * xgb_acc.get('MAE', 0) + w_prp * prophet_acc.get('MAE', 0),
        'MAPE':           w_xgb * xgb_mape + w_prp * prp_mape,
        'XGB_weight':     round(w_xgb * 100, 1),
        'Prophet_weight': round(w_prp * 100, 1),
    }

    return xgb_fc, prophet_fc, ensemble_df, ensemble_acc, xgb_fi
