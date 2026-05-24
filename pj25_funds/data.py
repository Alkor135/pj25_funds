"""Загрузка дневных котировок из локальных SQLite-БД."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

REQUIRED_FUTURES_COLUMNS = {
    "TRADEDATE",
    "OPEN",
    "LOW",
    "HIGH",
    "CLOSE",
    "SECID",
    "LSTTRADE",
}


def load_futures_quotes(db_path: str | Path, symbol: str | None = None) -> pd.DataFrame:
    """Загружает дневные фьючерсные свечи из таблицы Futures.

    Возвращает DataFrame с нормализованными именами колонок:
    `date`, `open`, `low`, `high`, `close`, `secid`, `lsttrade`, `symbol`.
    Строки сортируются по возрастанию даты.
    """
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"База данных не найдена: {path}")

    connection = sqlite3.connect(path)
    try:
        columns = _get_table_columns(connection, "Futures")
        missing = REQUIRED_FUTURES_COLUMNS.difference(columns)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"В таблице Futures отсутствуют колонки: {missing_text}")

        df = pd.read_sql_query(
            """
            SELECT TRADEDATE, OPEN, LOW, HIGH, CLOSE, SECID, LSTTRADE
            FROM Futures
            ORDER BY TRADEDATE ASC
            """,
            connection,
            parse_dates=["TRADEDATE"],
        )
    finally:
        connection.close()

    df = df.rename(
        columns={
            "TRADEDATE": "date",
            "OPEN": "open",
            "LOW": "low",
            "HIGH": "high",
            "CLOSE": "close",
            "SECID": "secid",
            "LSTTRADE": "lsttrade",
        }
    )
    df["symbol"] = symbol if symbol is not None else _infer_symbol_from_path(path)
    return df[["date", "open", "low", "high", "close", "secid", "lsttrade", "symbol"]]


def _get_table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    """Возвращает множество имен колонок SQLite-таблицы."""
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    if not rows:
        raise ValueError(f"Таблица {table_name} не найдена")
    return {str(row[1]) for row in rows}


def _infer_symbol_from_path(path: Path) -> str:
    """Определяет символ инструмента по имени файла БД."""
    return path.stem.split("_", maxsplit=1)[0]
