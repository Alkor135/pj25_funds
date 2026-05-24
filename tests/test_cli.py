r"""Тесты CLI-обвязки для запуска Markov-бэктеста по SQLite-БД.

Пример запуска:
    .\.venv\Scripts\python.exe -m unittest tests.test_cli -v
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.run_markov_backtest import run_database


def create_cli_futures_db(directory: Path) -> Path:
    """Создает SQLite-БД с достаточной историей для smoke-прогона CLI."""
    path = directory / "TEST_futures_day_2025_21-00.db"
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
        rows = [
            ("2025-01-01", 100.0, 99.0, 101.0, 100.0, "TSTH5", "2025-03-20"),
            ("2025-01-02", 101.0, 100.0, 103.0, 102.0, "TSTH5", "2025-03-20"),
            ("2025-01-03", 101.0, 99.0, 102.0, 100.0, "TSTH5", "2025-03-20"),
            ("2025-01-04", 101.0, 100.0, 104.0, 103.0, "TSTH5", "2025-03-20"),
            ("2025-01-05", 104.0, 103.0, 107.0, 106.0, "TSTH5", "2025-03-20"),
        ]
        connection.executemany(
            """
            INSERT INTO Futures
            (TRADEDATE, OPEN, LOW, HIGH, CLOSE, SECID, LSTTRADE)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    connection.close()
    return path


def create_cli_settings(directory: Path, db_path: Path) -> Path:
    """Создает YAML-настройки для запуска CLI по тестовой БД."""
    path = directory / "settings.yaml"
    output_dir = directory / "artifacts"
    path.write_text(
        f"""
data:
  quote_databases:
    - symbol: TEST
      path: '{db_path}'
markov:
  lookback: 1
  bull_threshold: 0.01
  bear_threshold: -0.01
  min_train: 3
  signal_scale: 1.0
backtest:
  entry_threshold: 0.0
  commission: 0.0
  slippage: 0.0
output:
  directory: '{output_dir}'
  save_artifacts: true
""",
        encoding="utf-8",
    )
    return path


class CliRunnerTest(unittest.TestCase):
    """Проверяет запуск пайплайна по одной SQLite-БД."""

    def setUp(self) -> None:
        """Создает временную директорию для тестовой БД."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        """Удаляет временную директорию после закрытия соединений."""
        self.temp_dir.cleanup()

    def test_run_database_returns_summary_for_sqlite_quotes(self) -> None:
        """run_database возвращает сводку с метриками и последним сигналом."""
        db_path = create_cli_futures_db(self.temp_path)

        result = run_database(
            db_path,
            symbol="TEST",
            lookback=1,
            bull_threshold=0.01,
            bear_threshold=-0.01,
            min_train=3,
        )

        self.assertEqual("TEST", result["symbol"])
        self.assertEqual(5, result["rows"])
        self.assertIn("metrics", result)
        self.assertGreaterEqual(result["metrics"]["n_trades"], 1)
        self.assertIn("latest_signal", result)

    def test_script_runs_directly_from_project_root(self) -> None:
        """Скрипт запускается как файл `scripts/run_markov_backtest.py`."""
        db_path = create_cli_futures_db(self.temp_path)

        completed = subprocess.run(
            [
                sys.executable,
                "scripts/run_markov_backtest.py",
                "--db",
                str(db_path),
                "--lookback",
                "1",
                "--bull-threshold",
                "0.01",
                "--bear-threshold",
                "-0.01",
                "--min-train",
                "3",
            ],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual("", completed.stderr)
        self.assertEqual(0, completed.returncode)
        self.assertIn("=== TEST ===", completed.stdout)

    def test_script_reads_databases_from_settings_yaml(self) -> None:
        """CLI запускается без --db, читая список БД из settings.yaml."""
        db_path = create_cli_futures_db(self.temp_path)
        settings_path = create_cli_settings(self.temp_path, db_path)

        completed = subprocess.run(
            [
                sys.executable,
                "scripts/run_markov_backtest.py",
                "--settings",
                str(settings_path),
            ],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual("", completed.stderr)
        self.assertEqual(0, completed.returncode)
        self.assertIn("=== TEST ===", completed.stdout)
        self.assertIn("Report:", completed.stdout)
        self.assertTrue((self.temp_path / "artifacts" / "reports" / "TEST_report.html").exists())


if __name__ == "__main__":
    unittest.main()
