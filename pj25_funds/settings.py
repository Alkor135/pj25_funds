"""Чтение настроек проекта из YAML-файла."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class QuoteDatabaseSettings:
    """Настройки одной SQLite-БД с котировками."""

    symbol: str
    path: Path


@dataclass(frozen=True)
class MarkovSettings:
    """Параметры наблюдаемой марковской модели режимов."""

    lookback: int = 20
    bull_threshold: float = 0.05
    bear_threshold: float = -0.05
    min_train: int = 252
    signal_scale: float = 1.0


@dataclass(frozen=True)
class BacktestSettings:
    """Параметры open-to-close бэктеста."""

    entry_threshold: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0


@dataclass(frozen=True)
class OutputSettings:
    """Настройки сохранения исследовательских артефактов."""

    directory: Path = Path("artifacts")
    save_artifacts: bool = True


@dataclass(frozen=True)
class AppSettings:
    """Полная конфигурация запуска проекта."""

    quote_databases: list[QuoteDatabaseSettings]
    markov: MarkovSettings
    backtest: BacktestSettings
    output: OutputSettings


def load_settings(path: str | Path = "settings.yaml") -> AppSettings:
    """Загружает и валидирует настройки из YAML-файла."""
    settings_path = Path(path)
    if not settings_path.exists():
        raise FileNotFoundError(f"Файл настроек не найден: {settings_path}")

    with settings_path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    if not isinstance(raw, dict):
        raise ValueError("settings.yaml должен содержать YAML-словарь верхнего уровня")

    return AppSettings(
        quote_databases=_parse_quote_databases(raw.get("data", {})),
        markov=_parse_markov(raw.get("markov", {})),
        backtest=_parse_backtest(raw.get("backtest", {})),
        output=_parse_output(raw.get("output", {})),
    )


def _parse_quote_databases(raw_data: Any) -> list[QuoteDatabaseSettings]:
    """Разбирает секцию `data.quote_databases`."""
    if not isinstance(raw_data, dict):
        raise ValueError("Секция data должна быть YAML-словарем")

    raw_databases = raw_data.get("quote_databases")
    if not isinstance(raw_databases, list) or not raw_databases:
        raise ValueError("Секция data.quote_databases должна быть непустым списком")

    databases = []
    for index, item in enumerate(raw_databases, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Элемент quote_databases #{index} должен быть словарем")
        symbol = item.get("symbol")
        path = item.get("path")
        if not symbol:
            raise ValueError(f"В quote_databases #{index} не задан symbol")
        if not path:
            raise ValueError(f"В quote_databases #{index} не задан path")
        databases.append(QuoteDatabaseSettings(symbol=str(symbol), path=Path(str(path))))
    return databases


def _parse_markov(raw_markov: Any) -> MarkovSettings:
    """Разбирает секцию `markov` с параметрами модели."""
    if raw_markov is None:
        raw_markov = {}
    if not isinstance(raw_markov, dict):
        raise ValueError("Секция markov должна быть YAML-словарем")

    settings = MarkovSettings(
        lookback=int(raw_markov.get("lookback", 20)),
        bull_threshold=float(raw_markov.get("bull_threshold", 0.05)),
        bear_threshold=float(raw_markov.get("bear_threshold", -0.05)),
        min_train=int(raw_markov.get("min_train", 252)),
        signal_scale=float(raw_markov.get("signal_scale", 1.0)),
    )
    if settings.lookback < 1:
        raise ValueError("markov.lookback должен быть положительным")
    if settings.bear_threshold >= settings.bull_threshold:
        raise ValueError("markov.bear_threshold должен быть меньше bull_threshold")
    if settings.min_train < 2:
        raise ValueError("markov.min_train должен быть не меньше 2")
    if settings.signal_scale <= 0:
        raise ValueError("markov.signal_scale должен быть положительным")
    return settings


def _parse_backtest(raw_backtest: Any) -> BacktestSettings:
    """Разбирает секцию `backtest` с параметрами проверки."""
    if raw_backtest is None:
        raw_backtest = {}
    if not isinstance(raw_backtest, dict):
        raise ValueError("Секция backtest должна быть YAML-словарем")

    settings = BacktestSettings(
        entry_threshold=float(raw_backtest.get("entry_threshold", 0.0)),
        commission=float(raw_backtest.get("commission", 0.0)),
        slippage=float(raw_backtest.get("slippage", 0.0)),
    )
    if settings.entry_threshold < 0:
        raise ValueError("backtest.entry_threshold не может быть отрицательным")
    if settings.commission < 0:
        raise ValueError("backtest.commission не может быть отрицательной")
    if settings.slippage < 0:
        raise ValueError("backtest.slippage не может быть отрицательным")
    return settings


def _parse_output(raw_output: Any) -> OutputSettings:
    """Разбирает секцию `output` с настройками сохранения артефактов."""
    if raw_output is None:
        raw_output = {}
    if not isinstance(raw_output, dict):
        raise ValueError("Секция output должна быть YAML-словарем")

    return OutputSettings(
        directory=Path(str(raw_output.get("directory", "artifacts"))),
        save_artifacts=bool(raw_output.get("save_artifacts", True)),
    )
