r"""Тесты open-to-close бэктеста по сигналам предыдущего дня.

Пример запуска:
    .\.venv\Scripts\python.exe -m unittest tests.test_backtest -v
"""

from __future__ import annotations

import unittest

import pandas as pd

from old.scripts.pj25_funds.backtest import run_open_close_backtest


def sample_signal_df() -> pd.DataFrame:
    """Возвращает тестовый DataFrame с сигналами и свечами исполнения."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-04"]),
            "open": [100.0, 100.0, 200.0],
            "close": [100.0, 110.0, 180.0],
            "mm_signal": [1.0, -1.0, 0.0],
        }
    )


class OpenCloseBacktestTest(unittest.TestCase):
    """Проверяет выравнивание сигналов и open-to-close доходности."""

    def test_backtest_uses_signal_from_t_and_open_close_return_from_next_day(self) -> None:
        """Сделка открывается на open следующего дня и закрывается на close."""
        trades, metrics = run_open_close_backtest(
            sample_signal_df(),
            signal_column="mm_signal",
            threshold=0.0,
        )

        self.assertEqual(pd.Timestamp("2025-01-02"), trades.loc[0, "signal_date"])
        self.assertEqual(pd.Timestamp("2025-01-03"), trades.loc[0, "entry_date"])
        self.assertEqual(pd.Timestamp("2025-01-03"), trades.loc[0, "exit_date"])
        self.assertEqual(1, trades.loc[0, "position"])
        self.assertAlmostEqual(0.10, trades.loc[0, "gross_return"])

        self.assertEqual(pd.Timestamp("2025-01-03"), trades.loc[1, "signal_date"])
        self.assertEqual(pd.Timestamp("2025-01-04"), trades.loc[1, "entry_date"])
        self.assertEqual(-1, trades.loc[1, "position"])
        self.assertAlmostEqual(0.10, trades.loc[1, "gross_return"])

        self.assertEqual(2, metrics["n_trades"])
        self.assertAlmostEqual(1.21 - 1.0, metrics["total_return"])


if __name__ == "__main__":
    unittest.main()
