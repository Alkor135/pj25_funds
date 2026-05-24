r"""Тесты генерации HTML-отчетов и исследовательских артефактов.

Пример запуска:
    .\.venv\Scripts\python.exe -m unittest tests.test_report -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from pj25_funds.report import save_ticker_artifacts


def sample_features() -> pd.DataFrame:
    """Возвращает DataFrame с MM-колонками для тестового отчета."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-04"]),
            "open": [100.0, 101.0, 102.0],
            "high": [102.0, 104.0, 105.0],
            "low": [99.0, 100.0, 101.0],
            "close": [101.0, 103.0, 102.0],
            "mm_regime": ["Sideways", "Bull", "Bear"],
            "mm_signal": [0.0, 0.5, -0.25],
            "mm_p_bear_next": [0.2, 0.1, 0.6],
            "mm_p_sideways_next": [0.6, 0.2, 0.3],
            "mm_p_bull_next": [0.2, 0.7, 0.1],
        }
    )


def sample_trades() -> pd.DataFrame:
    """Возвращает тестовые сделки с equity и drawdown."""
    return pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2025-01-02", "2025-01-03"]),
            "entry_date": pd.to_datetime(["2025-01-03", "2025-01-04"]),
            "exit_date": pd.to_datetime(["2025-01-03", "2025-01-04"]),
            "position": [1, -1],
            "gross_return": [0.02, 0.01],
            "cost_return": [0.0, 0.0],
            "net_return": [0.02, 0.01],
            "equity": [1.02, 1.0302],
            "drawdown": [0.0, 0.0],
        }
    )


class ReportTest(unittest.TestCase):
    """Проверяет сохранение pkl/json/html по одному тикеру."""

    def test_save_ticker_artifacts_writes_pickles_metrics_and_interactive_html(self) -> None:
        """Генератор пишет все артефакты и HTML содержит Plotly-графики."""
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = save_ticker_artifacts(
                output_dir=Path(temp_dir),
                symbol="TEST",
                features=sample_features(),
                trades=sample_trades(),
                metrics={
                    "n_trades": 2,
                    "total_return": 0.0302,
                    "max_drawdown": 0.0,
                    "sharpe": 1.2,
                    "win_rate": 1.0,
                },
            )

            features = pd.read_pickle(paths["features_pkl"])
            trades = pd.read_pickle(paths["trades_pkl"])
            metrics = json.loads(paths["metrics_json"].read_text(encoding="utf-8"))
            html = paths["html_report"].read_text(encoding="utf-8")

        self.assertEqual(3, len(features))
        self.assertEqual(2, len(trades))
        self.assertEqual(2, metrics["n_trades"])
        self.assertIn("TEST Markov Report", html)
        self.assertIn("Plotly.newPlot", html)
        self.assertIn("Equity", html)


if __name__ == "__main__":
    unittest.main()
