"""Генерация исследовательских артефактов и интерактивных HTML-отчетов."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def save_ticker_artifacts(
    output_dir: str | Path,
    symbol: str,
    features: pd.DataFrame,
    trades: pd.DataFrame,
    metrics: dict[str, Any],
) -> dict[str, Path]:
    """Сохраняет pkl/json/html артефакты для одного тикера."""
    root = Path(output_dir)
    data_dir = root / "data"
    trades_dir = root / "trades"
    metrics_dir = root / "metrics"
    reports_dir = root / "reports"
    for directory in [data_dir, trades_dir, metrics_dir, reports_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    safe_symbol = _safe_name(symbol)
    paths = {
        "features_pkl": data_dir / f"{safe_symbol}_markov_features.pkl",
        "trades_pkl": trades_dir / f"{safe_symbol}_trades.pkl",
        "metrics_json": metrics_dir / f"{safe_symbol}_metrics.json",
        "html_report": reports_dir / f"{safe_symbol}_report.html",
    }

    features.to_pickle(paths["features_pkl"])
    trades.to_pickle(paths["trades_pkl"])
    paths["metrics_json"].write_text(
        json.dumps(_json_safe(metrics), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths["html_report"].write_text(
        build_ticker_report_html(symbol, features, trades, metrics, paths),
        encoding="utf-8",
    )
    return paths


def build_ticker_report_html(
    symbol: str,
    features: pd.DataFrame,
    trades: pd.DataFrame,
    metrics: dict[str, Any],
    artifact_paths: dict[str, Path] | None = None,
) -> str:
    """Создает HTML-отчет с интерактивными Plotly-графиками."""
    price_figure = _build_price_signal_figure(features)
    equity_figure = _build_equity_figure(trades)
    probability_figure = _build_probability_figure(features)

    price_html = price_figure.to_html(full_html=False, include_plotlyjs=True)
    equity_html = equity_figure.to_html(full_html=False, include_plotlyjs=False)
    probability_html = probability_figure.to_html(full_html=False, include_plotlyjs=False)
    metrics_html = _build_metrics_html(metrics)
    artifacts_html = _build_artifacts_html(artifact_paths or {})

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{symbol} Markov Report</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      color: #172026;
      background: #f5f7f8;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1, h2 {{
      margin: 0 0 12px;
      font-weight: 700;
    }}
    h1 {{
      font-size: 30px;
    }}
    h2 {{
      margin-top: 28px;
      font-size: 20px;
    }}
    .meta {{
      margin-bottom: 20px;
      color: #51606a;
      font-size: 14px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin: 18px 0 8px;
    }}
    .metric {{
      background: #ffffff;
      border: 1px solid #d9e0e4;
      border-radius: 6px;
      padding: 12px;
    }}
    .metric-label {{
      color: #60707a;
      font-size: 12px;
      text-transform: uppercase;
    }}
    .metric-value {{
      margin-top: 6px;
      font-size: 22px;
      font-weight: 700;
    }}
    .chart {{
      background: #ffffff;
      border: 1px solid #d9e0e4;
      border-radius: 6px;
      padding: 8px;
      margin-bottom: 16px;
    }}
    .artifacts {{
      background: #ffffff;
      border: 1px solid #d9e0e4;
      border-radius: 6px;
      padding: 12px 16px;
      color: #33434c;
      font-size: 14px;
    }}
    code {{
      background: #eef2f4;
      padding: 2px 5px;
      border-radius: 4px;
    }}
  </style>
</head>
<body>
<main>
  <h1>{symbol} Markov Report</h1>
  <div class="meta">Интерактивный отчет по MM-сигналам, вероятностям следующего режима и open-to-close walk-forward результату.</div>
  {metrics_html}
  {artifacts_html}
  <h2>Цена, режим и сигнал</h2>
  <div class="chart">{price_html}</div>
  <h2>Equity и просадка</h2>
  <div class="chart">{equity_html}</div>
  <h2>Вероятности режима на следующий день</h2>
  <div class="chart">{probability_html}</div>
</main>
</body>
</html>
"""


def _build_price_signal_figure(features: pd.DataFrame) -> go.Figure:
    """Строит график цены закрытия, режима и MM-сигнала."""
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.68, 0.32],
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]],
    )
    fig.add_trace(
        go.Scatter(
            x=features["date"],
            y=features["close"],
            mode="lines",
            name="Close",
            line={"color": "#1f77b4", "width": 2},
            customdata=features.get("mm_regime"),
            hovertemplate="Дата=%{x}<br>Close=%{y:.2f}<br>Режим=%{customdata}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    if "mm_signal" in features:
        fig.add_trace(
            go.Bar(
                x=features["date"],
                y=features["mm_signal"],
                name="MM signal",
                marker_color="#637381",
                hovertemplate="Дата=%{x}<br>Signal=%{y:.4f}<extra></extra>",
            ),
            row=2,
            col=1,
        )
    fig.update_layout(
        height=620,
        margin={"l": 50, "r": 30, "t": 35, "b": 40},
        legend={"orientation": "h"},
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="Цена", row=1, col=1)
    fig.update_yaxes(title_text="Signal", row=2, col=1)
    return fig


def _build_equity_figure(trades: pd.DataFrame) -> go.Figure:
    """Строит график equity и drawdown по сделкам."""
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.68, 0.32],
    )
    if trades.empty:
        fig.add_annotation(text="Нет сделок", x=0.5, y=0.5, showarrow=False)
    else:
        fig.add_trace(
            go.Scatter(
                x=trades["exit_date"],
                y=trades["equity"],
                mode="lines",
                name="Equity",
                line={"color": "#1b8a5a", "width": 2},
                hovertemplate="Дата=%{x}<br>Equity=%{y:.4f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=trades["exit_date"],
                y=trades["drawdown"],
                mode="lines",
                name="Drawdown",
                fill="tozeroy",
                line={"color": "#b84747", "width": 1},
                hovertemplate="Дата=%{x}<br>Drawdown=%{y:.2%}<extra></extra>",
            ),
            row=2,
            col=1,
        )
    fig.update_layout(
        height=620,
        margin={"l": 50, "r": 30, "t": 35, "b": 40},
        legend={"orientation": "h"},
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="Equity", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown", tickformat=".0%", row=2, col=1)
    return fig


def _build_probability_figure(features: pd.DataFrame) -> go.Figure:
    """Строит график вероятностей Bear/Sideways/Bull на следующий день."""
    fig = go.Figure()
    probability_columns = [
        ("mm_p_bear_next", "Bear", "#b84747"),
        ("mm_p_sideways_next", "Sideways", "#7b8790"),
        ("mm_p_bull_next", "Bull", "#1b8a5a"),
    ]
    for column, label, color in probability_columns:
        if column in features:
            fig.add_trace(
                go.Scatter(
                    x=features["date"],
                    y=features[column],
                    mode="lines",
                    name=label,
                    line={"color": color, "width": 2},
                    hovertemplate=f"Дата=%{{x}}<br>{label}=%{{y:.2%}}<extra></extra>",
                )
            )
    fig.update_layout(
        height=420,
        margin={"l": 50, "r": 30, "t": 35, "b": 40},
        legend={"orientation": "h"},
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="Probability", tickformat=".0%")
    return fig


def _build_metrics_html(metrics: dict[str, Any]) -> str:
    """Создает HTML-блок основных показателей."""
    items = [
        ("Trades", _format_number(metrics.get("n_trades"), decimals=0)),
        ("Total return", _format_percent(metrics.get("total_return"))),
        ("Max drawdown", _format_percent(metrics.get("max_drawdown"))),
        ("Sharpe", _format_number(metrics.get("sharpe"), decimals=3)),
        ("Win rate", _format_percent(metrics.get("win_rate"))),
        ("Profit factor", _format_number(metrics.get("profit_factor"), decimals=3)),
        ("Average trade", _format_percent(metrics.get("average_trade"))),
    ]
    cards = "\n".join(
        f"""<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>"""
        for label, value in items
    )
    return f'<section class="metrics">{cards}</section>'


def _build_artifacts_html(paths: dict[str, Path]) -> str:
    """Создает HTML-блок путей к сохраненным артефактам."""
    if not paths:
        return ""
    items = "\n".join(
        f"<li><code>{key}</code>: {path}</li>" for key, path in sorted(paths.items())
    )
    return f'<section class="artifacts"><strong>Артефакты:</strong><ul>{items}</ul></section>'


def _format_percent(value: Any) -> str:
    """Форматирует долю как процент."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if pd.isna(number):
        return "n/a"
    return f"{number * 100:.2f}%"


def _format_number(value: Any, decimals: int = 4) -> str:
    """Форматирует число для карточки метрик."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if pd.isna(number):
        return "n/a"
    return f"{number:.{decimals}f}"


def _json_safe(value: Any) -> Any:
    """Преобразует pandas/numpy значения в JSON-совместимые типы."""
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    if pd.isna(value):
        return None
    return value


def _safe_name(value: str) -> str:
    """Преобразует тикер в безопасное имя файла."""
    return "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in value)
