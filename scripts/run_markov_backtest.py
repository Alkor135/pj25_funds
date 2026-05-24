r"""Запускает Markov Hedge Fund Method бэктест по настройкам `settings.yaml`.

Скрипт загружает таблицу `Futures`, добавляет MM-режимы, вероятности следующего
дня и сигнал `P(Bull next) - P(Bear next)`, затем тестирует сигнал по схеме:
сигнал на закрытии дня `t`, вход на `open_{t+1}`, выход на `close_{t+1}`.

Примеры запуска:
    .\.venv\Scripts\python.exe scripts\run_markov_backtest.py
    .\.venv\Scripts\python.exe scripts\run_markov_backtest.py --settings settings.yaml
    .\.venv\Scripts\python.exe scripts\run_markov_backtest.py --db C:\path\to\MIX_futures_day_2025_21-00.db
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pj25_funds.backtest import run_open_close_backtest
from pj25_funds.data import load_futures_quotes
from pj25_funds.markov import add_markov_columns
from pj25_funds.report import save_ticker_artifacts
from pj25_funds.settings import AppSettings, load_settings


def build_parser() -> argparse.ArgumentParser:
    """Создает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Walk-forward бэктест Markov-сигналов по дневным SQLite-БД."
    )
    parser.add_argument(
        "--settings",
        default="settings.yaml",
        help="Путь к YAML-файлу настроек. По умолчанию settings.yaml.",
    )
    parser.add_argument(
        "--db",
        action="append",
        help="Override: путь к SQLite-БД. Если задан, список БД берется из CLI.",
    )
    parser.add_argument("--lookback", type=int, default=20, help="Окно режима в днях.")
    parser.add_argument(
        "--bull-threshold",
        type=float,
        default=0.05,
        help="Порог Bull-режима по доходности окна.",
    )
    parser.add_argument(
        "--bear-threshold",
        type=float,
        default=-0.05,
        help="Порог Bear-режима по доходности окна.",
    )
    parser.add_argument(
        "--min-train",
        type=int,
        default=252,
        help="Минимум размеченных режимов до начала сигналов.",
    )
    parser.add_argument(
        "--entry-threshold",
        type=float,
        default=0.0,
        help="Минимальная абсолютная сила сигнала для входа.",
    )
    parser.add_argument(
        "--commission",
        type=float,
        default=0.0,
        help="Комиссия на сделку в долях капитала.",
    )
    parser.add_argument(
        "--slippage",
        type=float,
        default=0.0,
        help="Проскальзывание на сделку в долях капитала.",
    )
    return parser


def run_database(
    db_path: str | Path,
    symbol: str | None = None,
    lookback: int = 20,
    bull_threshold: float = 0.05,
    bear_threshold: float = -0.05,
    min_train: int = 252,
    signal_scale: float = 1.0,
    entry_threshold: float = 0.0,
    commission: float = 0.0,
    slippage: float = 0.0,
) -> dict[str, Any]:
    """Запускает полный пайплайн загрузки, MM-расчета и бэктеста для одной БД."""
    quotes = load_futures_quotes(db_path, symbol=symbol)
    enriched = add_markov_columns(
        quotes,
        lookback=lookback,
        bull_threshold=bull_threshold,
        bear_threshold=bear_threshold,
        min_train=min_train,
        signal_scale=signal_scale,
    )
    trades, metrics = run_open_close_backtest(
        enriched,
        signal_column="mm_signal",
        threshold=entry_threshold,
        commission=commission,
        slippage=slippage,
    )
    latest = _latest_signal_row(enriched)
    return {
        "db_path": str(db_path),
        "symbol": str(quotes["symbol"].iloc[0]) if symbol is None else symbol,
        "rows": int(len(quotes)),
        "date_start": _date_to_text(quotes["date"].iloc[0]),
        "date_end": _date_to_text(quotes["date"].iloc[-1]),
        "latest_date": _date_to_text(latest["date"]) if latest is not None else None,
        "latest_regime": latest["mm_regime"] if latest is not None else None,
        "latest_signal": float(latest["mm_signal"]) if latest is not None else math.nan,
        "latest_p_bear_next": float(latest["mm_p_bear_next"]) if latest is not None else math.nan,
        "latest_p_sideways_next": (
            float(latest["mm_p_sideways_next"]) if latest is not None else math.nan
        ),
        "latest_p_bull_next": float(latest["mm_p_bull_next"]) if latest is not None else math.nan,
        "metrics": metrics,
        "features": enriched,
        "trades": trades,
    }


def format_result(result: dict[str, Any]) -> str:
    """Форматирует результат одной БД для вывода в консоль."""
    metrics = result["metrics"]
    lines = [
        f"=== {result['symbol']} ===",
        f"DB: {result['db_path']}",
        f"Rows: {result['rows']} | {result['date_start']} -> {result['date_end']}",
        (
            "Latest signal: "
            f"{_format_number(result['latest_signal'])} "
            f"on {result['latest_date']} ({result['latest_regime']})"
        ),
        (
            "Next regime probabilities: "
            f"Bear={_format_percent(result['latest_p_bear_next'])}, "
            f"Sideways={_format_percent(result['latest_p_sideways_next'])}, "
            f"Bull={_format_percent(result['latest_p_bull_next'])}"
        ),
        (
            "Backtest: "
            f"trades={metrics['n_trades']}, "
            f"total_return={_format_percent(metrics['total_return'])}, "
            f"max_dd={_format_percent(metrics['max_drawdown'])}, "
            f"sharpe={_format_number(metrics['sharpe'])}, "
            f"win_rate={_format_percent(metrics['win_rate'])}"
        ),
    ]
    artifact_paths = result.get("artifact_paths")
    if artifact_paths:
        lines.append(f"Report: {artifact_paths['html_report']}")
        lines.append(f"Features pkl: {artifact_paths['features_pkl']}")
    return "\n".join(lines)


def run_settings(settings: AppSettings) -> list[dict[str, Any]]:
    """Запускает пайплайн для всех БД из объекта настроек."""
    results = []
    for database in settings.quote_databases:
        result = run_database(
            database.path,
            symbol=database.symbol,
            lookback=settings.markov.lookback,
            bull_threshold=settings.markov.bull_threshold,
            bear_threshold=settings.markov.bear_threshold,
            min_train=settings.markov.min_train,
            signal_scale=settings.markov.signal_scale,
            entry_threshold=settings.backtest.entry_threshold,
            commission=settings.backtest.commission,
            slippage=settings.backtest.slippage,
        )
        if settings.output.save_artifacts:
            result["artifact_paths"] = save_ticker_artifacts(
                output_dir=settings.output.directory,
                symbol=database.symbol,
                features=result["features"],
                trades=result["trades"],
                metrics=result["metrics"],
            )
        results.append(result)
    return results


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI."""
    args = build_parser().parse_args(argv)
    if args.db:
        results = [
            run_database(
                db_path,
                lookback=args.lookback,
                bull_threshold=args.bull_threshold,
                bear_threshold=args.bear_threshold,
                min_train=args.min_train,
                entry_threshold=args.entry_threshold,
                commission=args.commission,
                slippage=args.slippage,
            )
            for db_path in args.db
        ]
    else:
        results = run_settings(load_settings(args.settings))

    for result in results:
        print(format_result(result))
        print()
    return 0


def _latest_signal_row(df: pd.DataFrame) -> pd.Series | None:
    """Возвращает последнюю строку с рассчитанным MM-сигналом."""
    valid = df[df["mm_signal"].notna()]
    if valid.empty:
        return None
    return valid.iloc[-1]


def _date_to_text(value: Any) -> str:
    """Преобразует дату pandas/Python в строку `YYYY-MM-DD`."""
    timestamp = pd.Timestamp(value)
    return timestamp.strftime("%Y-%m-%d")


def _format_percent(value: Any) -> str:
    """Форматирует число-долю как процент или `n/a`."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not math.isfinite(number):
        return "n/a"
    return f"{number * 100:.2f}%"


def _format_number(value: Any) -> str:
    """Форматирует число с четырьмя знаками или `n/a`."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not math.isfinite(number):
        return "n/a"
    return f"{number:.4f}"


if __name__ == "__main__":
    raise SystemExit(main())
