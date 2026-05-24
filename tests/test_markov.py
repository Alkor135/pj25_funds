r"""Тесты наблюдаемой марковской модели режимов.

Пример запуска:
    .\.venv\Scripts\python.exe -m unittest tests.test_markov -v
"""

from __future__ import annotations

import unittest

import pandas as pd

from pj25_funds.markov import add_markov_columns, build_transition_matrix


def sample_quotes() -> pd.DataFrame:
    """Возвращает котировки с заранее понятной последовательностью режимов."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2025-01-01",
                    "2025-01-02",
                    "2025-01-03",
                    "2025-01-04",
                    "2025-01-05",
                ]
            ),
            "open": [100.0, 101.0, 101.0, 101.0, 104.0],
            "low": [99.0, 100.0, 99.0, 100.0, 103.0],
            "high": [101.0, 103.0, 102.0, 104.0, 107.0],
            "close": [100.0, 102.0, 100.0, 103.0, 106.0],
        }
    )


class MarkovModelTest(unittest.TestCase):
    """Проверяет расчет режимов, матрицы переходов и next-day вероятностей."""

    def test_build_transition_matrix_normalizes_rows(self) -> None:
        """Матрица переходов нормирует счетчики по строкам."""
        matrix = build_transition_matrix([2, 0, 2])

        self.assertAlmostEqual(1.0, matrix[2, 0])
        self.assertAlmostEqual(0.0, matrix[2, 1])
        self.assertAlmostEqual(0.0, matrix[2, 2])
        self.assertAlmostEqual(1.0, matrix[0, 2])
        self.assertAlmostEqual(1.0, matrix[1].sum())

    def test_add_markov_columns_uses_only_known_transitions(self) -> None:
        """Вероятности на дате t не включают будущий переход t -> t+1."""
        result = add_markov_columns(
            sample_quotes(),
            lookback=1,
            bull_threshold=0.01,
            bear_threshold=-0.01,
            min_train=3,
        )

        self.assertEqual("Bull", result.loc[3, "mm_regime"])
        self.assertAlmostEqual(1.0, result.loc[3, "mm_p_bear_next"])
        self.assertAlmostEqual(0.0, result.loc[3, "mm_p_sideways_next"])
        self.assertAlmostEqual(0.0, result.loc[3, "mm_p_bull_next"])
        self.assertAlmostEqual(-1.0, result.loc[3, "mm_signal"])
        self.assertEqual(-1, result.loc[3, "mm_position_sign"])


if __name__ == "__main__":
    unittest.main()
