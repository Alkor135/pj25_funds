"""Open-to-close бэктест торговых сигналов."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


TRADE_COLUMNS = [
    "signal_date",
    "entry_date",
    "exit_date",
    "entry_price",
    "exit_price",
    "signal",
    "position",
    "gross_return",
    "cost_return",
    "net_return",
    "equity",
    "drawdown",
]


def run_open_close_backtest(
    quotes: pd.DataFrame,
    signal_column: str = "mm_signal",
    threshold: float = 0.0,
    commission: float = 0.0,
    slippage: float = 0.0,
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Тестирует сигнал `t` на доходности `open_{t+1} -> close_{t+1}`.

    Положительный сигнал выше `threshold` открывает long, отрицательный ниже
    `-threshold` открывает short. Нулевые и пропущенные сигналы пропускаются.
    """
    _validate_backtest_input(quotes, signal_column)
    if threshold < 0:
        raise ValueError("threshold не может быть отрицательным")
    if commission < 0 or slippage < 0:
        raise ValueError("commission и slippage не могут быть отрицательными")

    rows = []
    for position_index in range(len(quotes) - 1):
        signal = quotes.iloc[position_index][signal_column]
        if pd.isna(signal):
            continue

        position = _position_from_signal(float(signal), threshold)
        if position == 0:
            continue

        signal_row = quotes.iloc[position_index]
        execution_row = quotes.iloc[position_index + 1]
        open_price = float(execution_row["open"])
        close_price = float(execution_row["close"])
        open_close_return = close_price / open_price - 1.0
        gross_return = position * open_close_return
        cost_return = abs(position) * (commission + slippage)
        net_return = gross_return - cost_return

        rows.append(
            {
                "signal_date": signal_row["date"],
                "entry_date": execution_row["date"],
                "exit_date": execution_row["date"],
                "entry_price": open_price,
                "exit_price": close_price,
                "signal": float(signal),
                "position": position,
                "gross_return": gross_return,
                "cost_return": cost_return,
                "net_return": net_return,
            }
        )

    trades = pd.DataFrame(rows, columns=TRADE_COLUMNS[:-2])
    if trades.empty:
        trades = pd.DataFrame(columns=TRADE_COLUMNS)
        return trades, _empty_metrics()

    trades["equity"] = (1.0 + trades["net_return"]).cumprod()
    running_max = trades["equity"].cummax()
    trades["drawdown"] = trades["equity"] / running_max - 1.0
    metrics = _calculate_metrics(trades["net_return"], trades["equity"], trades["drawdown"])
    return trades[TRADE_COLUMNS], metrics


def _validate_backtest_input(quotes: pd.DataFrame, signal_column: str) -> None:
    """Проверяет наличие колонок, необходимых для open-to-close бэктеста."""
    required = {"date", "open", "close", signal_column}
    missing = required.difference(quotes.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"В quotes отсутствуют колонки: {missing_text}")


def _position_from_signal(signal: float, threshold: float) -> int:
    """Преобразует сигнал в позицию с учетом порога входа."""
    if signal > threshold:
        return 1
    if signal < -threshold:
        return -1
    return 0


def _calculate_metrics(
    returns: pd.Series,
    equity: pd.Series,
    drawdown: pd.Series,
) -> dict[str, float | int]:
    """Считает основные метрики по сделкам стратегии."""
    positive = returns[returns > 0]
    negative = returns[returns < 0]
    loss_sum = abs(float(negative.sum()))
    profit_factor = math.inf if loss_sum == 0 and positive.sum() > 0 else (
        float(positive.sum()) / loss_sum if loss_sum > 0 else math.nan
    )
    std = float(returns.std(ddof=1)) if len(returns) > 1 else 0.0
    sharpe = float(returns.mean() / std * np.sqrt(252)) if std > 0 else math.nan

    return {
        "n_trades": int(len(returns)),
        "total_return": float(equity.iloc[-1] - 1.0),
        "average_trade": float(returns.mean()),
        "win_rate": float((returns > 0).mean()),
        "profit_factor": profit_factor,
        "max_drawdown": float(drawdown.min()),
        "sharpe": sharpe,
    }


def _empty_metrics() -> dict[str, float | int]:
    """Возвращает метрики для случая без сделок."""
    return {
        "n_trades": 0,
        "total_return": 0.0,
        "average_trade": math.nan,
        "win_rate": math.nan,
        "profit_factor": math.nan,
        "max_drawdown": 0.0,
        "sharpe": math.nan,
    }
