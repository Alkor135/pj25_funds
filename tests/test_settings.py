r"""Тесты чтения настроек проекта из YAML.

Пример запуска:
    .\.venv\Scripts\python.exe -m unittest tests.test_settings -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pj25_funds.settings import load_settings


class SettingsTest(unittest.TestCase):
    """Проверяет разбор YAML-настроек в типизированную конфигурацию."""

    def test_load_settings_reads_databases_markov_and_backtest_sections(self) -> None:
        """Загрузчик читает все секции, нужные для запуска бэктеста."""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.yaml"
            path.write_text(
                """
data:
  quote_databases:
    - symbol: TEST
      path: C:\\quotes\\TEST.db
markov:
  lookback: 10
  bull_threshold: 0.03
  bear_threshold: -0.04
  min_train: 30
  signal_scale: 0.5
backtest:
  entry_threshold: 0.1
  commission: 0.0002
  slippage: 0.0003
output:
  directory: custom_artifacts
  save_artifacts: true
""",
                encoding="utf-8",
            )

            settings = load_settings(path)

        self.assertEqual("TEST", settings.quote_databases[0].symbol)
        self.assertEqual(Path("C:\\quotes\\TEST.db"), settings.quote_databases[0].path)
        self.assertEqual(10, settings.markov.lookback)
        self.assertEqual(0.03, settings.markov.bull_threshold)
        self.assertEqual(-0.04, settings.markov.bear_threshold)
        self.assertEqual(30, settings.markov.min_train)
        self.assertEqual(0.5, settings.markov.signal_scale)
        self.assertEqual(0.1, settings.backtest.entry_threshold)
        self.assertEqual(0.0002, settings.backtest.commission)
        self.assertEqual(0.0003, settings.backtest.slippage)
        self.assertEqual(Path("custom_artifacts"), settings.output.directory)
        self.assertTrue(settings.output.save_artifacts)


if __name__ == "__main__":
    unittest.main()
