import warnings
warnings.filterwarnings('ignore')

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from data.fetcher import IDX_STOCKS, get_stock_data
from analysis.technical import compute_indicators
from analysis.signal import generate_signals, get_latest_signal
from screener.screener import screen_stocks
from forecast.prophet_model import run_prophet_forecast
from forecast.xgb_model import run_xgb_forecast

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Saham IDX Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.4rem; }
.buy-badge  { background:#1b5e20; color:#fff; padding:4px 12px; border-radius:6px; font-weight:700; }
.sell-badge { background:#b71c1c; color:#fff; padding:4px 12px; border-radius:6px; font-weight:700; }
.hold-badge { background:#e65100; color:#fff; padding:4px 12px; border-radius:6px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ── Cached data loader ────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def cached_stock_data(ticker: str, period: str) -> pd.DataFrame:
    return get_stock_data(ticker, period)


# ── Title ─────────────────────────────────────────────────────
st.title("📈 Saham IDX Analyzer")
st.caption("Screener · Analisis Teknikal · Forecasting — data via Yahoo Finance")

tab_screen, tab_chart, tab_fc = st.tabs(["🔍 Screener", "📊 Analisis Teknikal", "🔮 Forecasting"])

# ════════════════════════════════════════════════════════════════
# TAB 1 — SCREENER
# ════════════════════════════════════════════════════════════════
with tab_screen:
    st.subheader("Screener Saham IDX")

    c1, c2, c3 = st.columns([4, 1, 1])
    with c1:
        sel_tickers = st.multiselect(
            "Pilih saham:",
            options=list(IDX_STOCKS.keys()),
            default=list(IDX_STOCKS.keys())[:20],
            format_func=lambda x: f"{x} — {IDX_STOCKS[x]}",
        )
    with c2:
        sc_period = st.selectbox("Periode", ['3mo', '6mo', '1y'], key='sc_period')
    with c3:
        sc_filter = st.selectbox("Filter sinyal", ['Semua', 'BUY', 'SELL', 'HOLD'])

    if st.button("🔍 Jalankan Screener", type="primary", use_container_width=True):
        if not sel_tickers:
            st.warning("Pilih minimal 1 saham.")
        else:
            progress_bar = st.progress(0.0)
            status_txt   = st.empty()

            def _cb(cur, tot, tkr):
                progress_bar.progress(cur / tot)
                status_txt.caption(f"Menganalisis {tkr} ({cur}/{tot})…")

            with st.spinner(""):
                df_sc = screen_stocks(sel_tickers, sc_period, _cb)

            progress_bar.empty()
            status_txt.empty()

            if df_sc.empty:
                st.error("Tidak ada data berhasil diambil.")
            else:
                if sc_filter != 'Semua':
                    df_sc = df_sc[df_sc['Signal'] == sc_filter]

                # Summary metrics
                col_b, col_s, col_h, col_t = st.columns(4)
                col_b.metric("BUY",  int((df_sc['Signal'] == 'BUY').sum()))
                col_s.metric("SELL", int((df_sc['Signal'] == 'SELL').sum()))
                col_h.metric("HOLD", int((df_sc['Signal'] == 'HOLD').sum()))
                col_t.metric("Total", len(df_sc))

                def _color_signal(val):
                    m = {'BUY': 'background:#1b5e20;color:#fff',
                         'SELL': 'background:#b71c1c;color:#fff',
                         'HOLD': 'background:#e65100;color:#fff'}
                    return m.get(val, '')

                def _color_chg(val):
                    return 'color:#00c853' if val > 0 else 'color:#f44336' if val < 0 else ''

                def _color_rsi(val):
                    if val < 30: return 'color:#00c853;font-weight:700'
                    if val > 70: return 'color:#f44336;font-weight:700'
                    return ''

                st.dataframe(
                    df_sc.style
                         .map(_color_signal, subset=['Signal'])
                         .map(_color_chg,    subset=['Perubahan%'])
                         .map(_color_rsi,    subset=['RSI'])
                         .format({
                             'Harga':      'Rp {:,.0f}',
                             'Perubahan%': '{:+.2f}%',
                             'RSI':        '{:.1f}',
                             'Vs MA50%':   '{:+.1f}%',
                             'MACD Hist':  '{:.3f}',
                             'Vol Ratio':  '{:.2f}x',
                             'Score':      '{:.2f}',
                         }),
                    use_container_width=True,
                    height=520,
                )

# ════════════════════════════════════════════════════════════════
# TAB 2 — ANALISIS TEKNIKAL
# ════════════════════════════════════════════════════════════════
with tab_chart:
    st.subheader("Analisis Teknikal")

    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        ch_ticker = st.selectbox(
            "Saham",
            list(IDX_STOCKS.keys()),
            format_func=lambda x: f"{x} — {IDX_STOCKS[x]}",
            key='ch_ticker',
        )
    with c2:
        ch_period = st.selectbox("Periode", ['3mo', '6mo', '1y', '2y'], index=2, key='ch_period')
    with c3:
        ch_inds = st.multiselect(
            "Overlay indikator",
            ['MA20', 'MA50', 'MA200', 'Bollinger Bands'],
            default=['MA20', 'MA50'],
        )

    if ch_ticker:
        with st.spinner(f"Mengambil data {ch_ticker}…"):
            df_ch = cached_stock_data(ch_ticker, ch_period)

        if df_ch.empty:
            st.error(f"Tidak bisa mengambil data {ch_ticker}.")
        else:
            df_ch = compute_indicators(df_ch)
            df_ch = generate_signals(df_ch)
            sig   = get_latest_signal(df_ch)
            last  = df_ch.iloc[-1]

            # Metric row
            signal_val = sig.get('signal', 'HOLD')
            rsi_val    = sig.get('rsi', 0)
            close_val  = sig.get('close', 0)
            macd_val   = sig.get('macd', 0)
            macd_s_val = sig.get('macd_signal', 0)
            delta_1d   = float(last.get('Change_pct', 0) or 0)

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Sinyal",   signal_val)
            m2.metric("Harga",    f"Rp {close_val:,.0f}", f"{delta_1d:+.2f}%")
            m3.metric("RSI (14)", f"{rsi_val:.1f}")
            m4.metric("MACD",     f"{macd_val:.3f}", f"{macd_val - macd_s_val:+.3f}")
            m5.metric("Score",    f"{sig.get('score', 0):.2f}")

            if sig.get('reasons'):
                st.info("**Alasan:** " + " · ".join(sig['reasons']))

            # ── Chart ──────────────────────────────────────────
            fig = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.02,
                row_heights=[0.55, 0.18, 0.27],
            )

            # Candlestick
            fig.add_trace(go.Candlestick(
                x=df_ch.index,
                open=df_ch['Open'], high=df_ch['High'],
                low=df_ch['Low'],   close=df_ch['Close'],
                name='OHLC',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350',
            ), row=1, col=1)

            # MA overlays
            ma_cfg = {'MA20': ('#42a5f5', 1.5), 'MA50': ('#ffa726', 1.5), 'MA200': ('#ab47bc', 1.5)}
            for ma, (clr, w) in ma_cfg.items():
                if ma in ch_inds and ma in df_ch:
                    fig.add_trace(go.Scatter(
                        x=df_ch.index, y=df_ch[ma].squeeze(),
                        name=ma, line=dict(color=clr, width=w),
                    ), row=1, col=1)

            # Bollinger Bands
            if 'Bollinger Bands' in ch_inds and 'BB_upper' in df_ch:
                fig.add_trace(go.Scatter(
                    x=df_ch.index, y=df_ch['BB_upper'].squeeze(),
                    name='BB Upper', line=dict(color='rgba(200,200,200,0.4)', dash='dot'),
                ), row=1, col=1)
                fig.add_trace(go.Scatter(
                    x=df_ch.index, y=df_ch['BB_lower'].squeeze(),
                    name='BB Lower', line=dict(color='rgba(200,200,200,0.4)', dash='dot'),
                    fill='tonexty', fillcolor='rgba(200,200,200,0.05)',
                ), row=1, col=1)

            # BUY/SELL markers
            buys  = df_ch[df_ch['Signal'] == 'BUY']
            sells = df_ch[df_ch['Signal'] == 'SELL']
            if not buys.empty:
                fig.add_trace(go.Scatter(
                    x=buys.index, y=buys['Low'].squeeze() * 0.99,
                    mode='markers', name='BUY Signal',
                    marker=dict(symbol='triangle-up', size=9, color='#00e676'),
                ), row=1, col=1)
            if not sells.empty:
                fig.add_trace(go.Scatter(
                    x=sells.index, y=sells['High'].squeeze() * 1.01,
                    mode='markers', name='SELL Signal',
                    marker=dict(symbol='triangle-down', size=9, color='#ff1744'),
                ), row=1, col=1)

            # Volume bars
            vol_colors = [
                '#26a69a' if float(df_ch['Close'].iloc[i]) >= float(df_ch['Open'].iloc[i])
                else '#ef5350'
                for i in range(len(df_ch))
            ]
            fig.add_trace(go.Bar(
                x=df_ch.index, y=df_ch['Volume'].squeeze(),
                name='Volume', marker_color=vol_colors, opacity=0.6,
            ), row=2, col=1)
            if 'Volume_MA20' in df_ch:
                fig.add_trace(go.Scatter(
                    x=df_ch.index, y=df_ch['Volume_MA20'].squeeze(),
                    name='Vol MA20', line=dict(color='#ffa726', width=1),
                ), row=2, col=1)

            # RSI
            if 'RSI' in df_ch:
                rsi_s = df_ch['RSI'].squeeze()
                fig.add_trace(go.Scatter(
                    x=df_ch.index, y=rsi_s,
                    name='RSI', line=dict(color='#ce93d8', width=1.5),
                ), row=3, col=1)
                for lvl, clr in [(70, 'rgba(255,80,80,0.4)'), (30, 'rgba(80,200,120,0.4)'), (50, 'rgba(180,180,180,0.2)')]:
                    fig.add_hline(y=lvl, line_dash='dash', line_color=clr, row=3, col=1)

            # MACD
            if 'MACD' in df_ch:
                fig.add_trace(go.Scatter(
                    x=df_ch.index, y=df_ch['MACD'].squeeze(),
                    name='MACD', line=dict(color='#42a5f5', width=1.2),
                ), row=3, col=1)
                fig.add_trace(go.Scatter(
                    x=df_ch.index, y=df_ch['MACD_signal'].squeeze(),
                    name='Signal', line=dict(color='#ff7043', width=1),
                ), row=3, col=1)
                hist_vals = df_ch['MACD_hist'].squeeze().fillna(0)
                hist_clrs = ['#26a69a' if v >= 0 else '#ef5350' for v in hist_vals]
                fig.add_trace(go.Bar(
                    x=df_ch.index, y=hist_vals,
                    name='Hist', marker_color=hist_clrs, opacity=0.5,
                ), row=3, col=1)

            fig.update_layout(
                height=720,
                template='plotly_dark',
                xaxis_rangeslider_visible=False,
                legend=dict(orientation='h', x=0, y=1.02),
                margin=dict(l=10, r=10, t=30, b=10),
            )
            fig.update_yaxes(title_text="Harga (Rp)", row=1, col=1)
            fig.update_yaxes(title_text="Volume",     row=2, col=1)
            fig.update_yaxes(title_text="RSI / MACD", row=3, col=1)

            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Data 30 hari terakhir"):
                cols_show = [c for c in ['Open','High','Low','Close','Volume','RSI','MACD','Signal'] if c in df_ch]
                st.dataframe(
                    df_ch[cols_show].tail(30).iloc[::-1].style.format({
                        'Open': 'Rp {:,.0f}', 'High': 'Rp {:,.0f}',
                        'Low':  'Rp {:,.0f}', 'Close': 'Rp {:,.0f}',
                        'Volume': '{:,.0f}',  'RSI': '{:.1f}', 'MACD': '{:.4f}',
                    }),
                    use_container_width=True,
                )

# ════════════════════════════════════════════════════════════════
# TAB 3 — FORECASTING
# ════════════════════════════════════════════════════════════════
with tab_fc:
    st.subheader("Forecasting Harga Saham")
    st.warning(
        "⚠️ **Disclaimer**: Forecasting bukan jaminan profit. "
        "Pasar saham dipengaruhi banyak faktor yang tidak bisa diprediksi model. "
        "Gunakan sebagai salah satu referensi analisis, bukan satu-satunya acuan."
    )

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        fc_ticker = st.selectbox(
            "Saham",
            list(IDX_STOCKS.keys()),
            format_func=lambda x: f"{x} — {IDX_STOCKS[x]}",
            key='fc_ticker',
        )
    with c2:
        fc_period = st.selectbox("Data historis", ['1y', '2y', '3y'], index=1, key='fc_period')
    with c3:
        fc_days = st.selectbox("Forecast (hari ke depan)", [7, 14, 30, 60], index=1)
    with c4:
        fc_model = st.selectbox("Model", ['XGBoost', 'Prophet', 'Keduanya'])

    if st.button("🔮 Jalankan Forecast", type="primary", use_container_width=True):
        with st.spinner(f"Mengambil data {fc_ticker}…"):
            df_fc = cached_stock_data(fc_ticker, fc_period)

        if df_fc.empty:
            st.error(f"Tidak bisa mengambil data {fc_ticker}.")
        else:
            df_fc = compute_indicators(df_fc)

            fig_fc = go.Figure()

            # Harga historis (120 hari terakhir)
            hist = df_fc.tail(120)
            fig_fc.add_trace(go.Scatter(
                x=hist.index, y=hist['Close'].squeeze(),
                name='Harga Aktual',
                line=dict(color='#90caf9', width=2),
            ))

            xgb_fc = prophet_fc = None

            # ── XGBoost ──────────────────────────────────────
            if fc_model in ('XGBoost', 'Keduanya'):
                with st.spinner("Melatih XGBoost…"):
                    xgb_fc, xgb_acc, xgb_fi = run_xgb_forecast(df_fc, fc_days)

                if xgb_fc is not None:
                    fig_fc.add_trace(go.Scatter(
                        x=xgb_fc['ds'], y=xgb_fc['yhat'],
                        name='XGBoost Forecast',
                        line=dict(color='#69f0ae', width=2, dash='dash'),
                    ))
                    m1, m2 = st.columns(2)
                    m1.metric("XGBoost MAE",  f"Rp {xgb_acc.get('MAE', 0):,.0f}")
                    m2.metric("XGBoost MAPE", f"{xgb_acc.get('MAPE', 0):.2f}%")
                    if xgb_fi is not None:
                        with st.expander("Feature Importance XGBoost"):
                            st.dataframe(xgb_fi, use_container_width=True)
                else:
                    st.error(f"XGBoost gagal: {xgb_acc.get('error', '')}")

            # ── Prophet ──────────────────────────────────────
            if fc_model in ('Prophet', 'Keduanya'):
                with st.spinner("Melatih Prophet…"):
                    prophet_fc, prophet_acc = run_prophet_forecast(df_fc, fc_days)

                if prophet_fc is not None:
                    last_date  = df_fc.index[-1]
                    fc_only    = prophet_fc[prophet_fc['ds'] > last_date]

                    fig_fc.add_trace(go.Scatter(
                        x=fc_only['ds'], y=fc_only['yhat'],
                        name='Prophet Forecast',
                        line=dict(color='#ffb74d', width=2, dash='dot'),
                    ))
                    # Confidence band
                    x_band = pd.concat([fc_only['ds'], fc_only['ds'].iloc[::-1]])
                    y_band = pd.concat([fc_only['yhat_upper'], fc_only['yhat_lower'].iloc[::-1]])
                    fig_fc.add_trace(go.Scatter(
                        x=x_band, y=y_band,
                        fill='toself',
                        fillcolor='rgba(255,183,77,0.12)',
                        line=dict(color='rgba(0,0,0,0)'),
                        name='Prophet CI',
                    ))
                    m3, m4 = st.columns(2)
                    m3.metric("Prophet MAE",  f"Rp {prophet_acc.get('MAE', 0):,.0f}")
                    m4.metric("Prophet MAPE", f"{prophet_acc.get('MAPE', 0):.2f}%")
                else:
                    st.error(f"Prophet gagal: {prophet_acc.get('error', '')}")

            fig_fc.update_layout(
                title=f"Forecast {fc_ticker}.JK — {fc_days} Hari ke Depan",
                template='plotly_dark',
                height=480,
                xaxis_title="Tanggal",
                yaxis_title="Harga (Rp)",
                legend=dict(orientation='h', x=0, y=1.02),
                margin=dict(l=10, r=10, t=50, b=10),
            )
            fig_fc.update_yaxes(tickformat=',.0f', tickprefix='Rp ')
            st.plotly_chart(fig_fc, use_container_width=True)

            # Tabel hasil forecast
            tabs_result = []
            if xgb_fc is not None:
                tabs_result.append(('XGBoost', xgb_fc))
            if prophet_fc is not None:
                last_date = df_fc.index[-1]
                tabs_result.append(('Prophet', prophet_fc[prophet_fc['ds'] > last_date][['ds', 'yhat']].reset_index(drop=True)))

            if tabs_result:
                st.subheader("Tabel Prediksi")
                sub_tabs = st.tabs([name for name, _ in tabs_result])
                for (name, fdf), sub in zip(tabs_result, sub_tabs):
                    with sub:
                        out = fdf.copy()
                        out['ds'] = pd.to_datetime(out['ds']).dt.strftime('%Y-%m-%d')
                        out.columns = ['Tanggal', 'Prediksi Harga']
                        st.dataframe(
                            out.style.format({'Prediksi Harga': 'Rp {:,.0f}'}),
                            use_container_width=True,
                        )
