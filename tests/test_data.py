r"""Тесты загрузки дневных фьючерсных котировок из SQLite.

Пример запуска:
    .\.venv\Scripts\python.exe -m unittest tests.test_data -v
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from pj25_funds.data import load_futures_quotes


def create_futures_db(directory: Path) -> Path:
    """Создает временную SQLite-БД с таблицей Futures в формате источника."""
    path = directory / "quotes.db"
    connection = sqlite3.connect(path)
    with connection:
        connection.execute(
            """
            CREATE TABLE Futures (
                TRADEDATE DATE PRIMARY KEY UNIQUE NOT NULL,
                OPEN REAL NOT NULL,
                LOW REAL NOT NULL,
                HIGH REAL NOT NULL,
                CLOSE REAL NOT NULL,
                SECID TEXT NOT NULL,
                LSTTRADE TEXT NOT NULL
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO Futures
            (TRADEDATE, OPEN, LOW, HIGH, CLOSE, SECID, LSTTRADE)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("2025-01-03", 102.0, 101.0, 106.0, 105.0, "MXH5", "2025-03-20"),
                ("2025-01-02", 100.0, 99.0, 103.0, 102.0, "MXH5", "2025-03-20"),
            ],
        )
    connection.close()
    return path


class LoadFuturesQuotesTest(unittest.TestCase):
    """Проверяет нормализацию и сортировку котировок из таблицы Futures."""

    def setUp(self) -> None:
        """Создает временную директорию для SQLite-файла теста."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        """Удаляет временную директорию после закрытия SQLite-соединений."""
        self.temp_dir.cleanup()

    def test_load_futures_quotes_orders_rows_and_normalizes_columns(self) -> None:
        """Загрузчик возвращает ожидаемые колонки и сортирует строки по дате."""
        db_path = create_futures_db(self.temp_path)

        df = load_futures_quotes(db_path, symbol="MIX")

        self.assertEqual(
            [
                "date",
                "open",
                "low",
                "high",
                "close",
                "secid",
                "lsttrade",
                "symbol",
            ],
            list(df.columns),
        )
        self.assertEqual(
            [pd.Timestamp("2025-01-02"), pd.Timestamp("2025-01-03")],
            df["date"].tolist(),
        )
        self.assertEqual(["MIX", "MIX"], df["symbol"].tolist())
        self.assertEqual([100.0, 102.0], df["open"].tolist())


if __name__ == "__main__":
    unittest.main()
