from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.config import APP_CONFIG


def build_history_chart(history_df: pd.DataFrame) -> go.Figure:
    rolling_mean = history_df[APP_CONFIG.target_col].rolling(window=3, min_periods=1).mean()
    max_row = history_df.loc[history_df[APP_CONFIG.target_col].idxmax()]
    min_row = history_df.loc[history_df[APP_CONFIG.target_col].idxmin()]
    latest_row = history_df.iloc[-1]

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=history_df[APP_CONFIG.date_col],
            y=history_df[APP_CONFIG.target_col],
            mode="lines+markers",
            name="历史用电量",
            line=dict(color="#0f4c5c", width=3.5),
            marker=dict(size=7, color="#0f4c5c"),
            fill="tozeroy",
            fillcolor="rgba(15, 76, 92, 0.10)",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=history_df[APP_CONFIG.date_col],
            y=rolling_mean,
            mode="lines",
            name="3个月移动均值",
            line=dict(color="#d97706", width=2.5, dash="dot"),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=[max_row[APP_CONFIG.date_col], min_row[APP_CONFIG.date_col], latest_row[APP_CONFIG.date_col]],
            y=[max_row[APP_CONFIG.target_col], min_row[APP_CONFIG.target_col], latest_row[APP_CONFIG.target_col]],
            mode="markers+text",
            name="关键节点",
            text=[
                f"峰值 {max_row[APP_CONFIG.target_col]:.0f}",
                f"低谷 {min_row[APP_CONFIG.target_col]:.0f}",
                f"最新 {latest_row[APP_CONFIG.target_col]:.0f}",
            ],
            textposition="top center",
            marker=dict(
                size=[12, 12, 11],
                color=["#bb3e03", "#94a3b8", "#0ea5a4"],
                line=dict(color="white", width=1.5),
            ),
        )
    )
    figure.update_layout(**_base_layout("历史月度用电量趋势"))
    return figure


def build_forecast_chart(history_df: pd.DataFrame, forecast_df: pd.DataFrame) -> go.Figure:
    forecast_start = forecast_df[APP_CONFIG.date_col].min()
    peak_row = forecast_df.loc[forecast_df["forecast"].idxmax()]

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=history_df[APP_CONFIG.date_col],
            y=history_df[APP_CONFIG.target_col],
            mode="lines",
            name="历史",
            line=dict(color="#1d3557", width=3),
            fill="tozeroy",
            fillcolor="rgba(29, 53, 87, 0.06)",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=forecast_df[APP_CONFIG.date_col],
            y=forecast_df["forecast"],
            mode="lines+markers",
            name="预测",
            line=dict(color="#c2410c", width=3.5, dash="dash"),
            marker=dict(size=8, color="#c2410c"),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=forecast_df[APP_CONFIG.date_col],
            y=forecast_df["upper_bound"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=forecast_df[APP_CONFIG.date_col],
            y=forecast_df["lower_bound"],
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(194, 65, 12, 0.16)",
            line=dict(width=0),
            name="预测区间",
            hoverinfo="skip",
        )
    )
    # Use a manual shape instead of add_vline because Plotly's annotated vline
    # path can trigger Timestamp arithmetic errors on newer pandas versions.
    figure.add_shape(
        type="line",
        x0=forecast_start,
        x1=forecast_start,
        y0=0,
        y1=1,
        xref="x",
        yref="paper",
        line=dict(color="#475569", width=2, dash="dot"),
    )
    figure.add_annotation(
        x=forecast_start,
        y=1,
        xref="x",
        yref="paper",
        text="预测起点",
        showarrow=False,
        xanchor="left",
        yanchor="bottom",
        font=dict(color="#475569"),
        bgcolor="rgba(255,255,255,0.86)",
    )
    figure.add_annotation(
        x=peak_row[APP_CONFIG.date_col],
        y=peak_row["forecast"],
        text=f"预测峰值 {peak_row['forecast']:.0f}",
        showarrow=True,
        arrowhead=2,
        arrowcolor="#c2410c",
        bgcolor="rgba(255,255,255,0.85)",
    )
    figure.update_layout(**_base_layout("未来用电量预测"))
    return figure


def build_seasonality_chart(history_df: pd.DataFrame) -> go.Figure:
    monthly_avg = (
        history_df.assign(month=history_df[APP_CONFIG.date_col].dt.month)
        .groupby("month")[APP_CONFIG.target_col]
        .mean()
        .reset_index()
    )
    monthly_avg["label"] = monthly_avg["month"].astype(str) + "月"
    top_mask = monthly_avg[APP_CONFIG.target_col].rank(method="dense", ascending=False) <= 3
    colors = np.where(top_mask, "#c2410c", "#8ecae6")

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=monthly_avg["label"],
            y=monthly_avg[APP_CONFIG.target_col],
            name="月均用电量",
            marker_color=colors,
            text=monthly_avg[APP_CONFIG.target_col].round(0),
            textposition="outside",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=monthly_avg["label"],
            y=monthly_avg[APP_CONFIG.target_col],
            mode="lines+markers",
            name="季节性轮廓",
            line=dict(color="#0f4c5c", width=2),
            marker=dict(size=6, color="#0f4c5c"),
        )
    )
    figure.update_layout(**_base_layout("历史月度季节性分布"))
    return figure


def _base_layout(title: str) -> dict:
    return {
        "title": {"text": title, "x": 0.02, "font": {"size": 20}},
        "xaxis_title": "月份",
        "yaxis_title": "用电量（亿千瓦时）",
        "template": "plotly_white",
        "hovermode": "x unified",
        "paper_bgcolor": "#fcfbf7",
        "plot_bgcolor": "#ffffff",
        "font": {"family": "Avenir Next, PingFang SC, Microsoft YaHei, sans-serif"},
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1.0,
        },
        "margin": dict(l=20, r=20, t=70, b=20),
        "xaxis": {"showgrid": False, "zeroline": False},
        "yaxis": {"gridcolor": "rgba(15, 23, 42, 0.08)", "zeroline": False},
    }
