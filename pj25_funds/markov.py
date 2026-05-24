"""Расчет наблюдаемой марковской модели рыночных режимов."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

BEAR = 0
SIDEWAYS = 1
BULL = 2

REGIME_NAMES = {
    BEAR: "Bear",
    SIDEWAYS: "Sideways",
    BULL: "Bull",
}


def label_regimes(
    close: pd.Series,
    lookback: int = 20,
    bull_threshold: float = 0.05,
    bear_threshold: float = -0.05,
) -> tuple[pd.Series, pd.Series]:
    """Размечает режимы по доходности закрытия за lookback-окно.

    Возвращает пару `(rolling_return, regime_code)`, где режимы кодируются как
    `0=Bear`, `1=Sideways`, `2=Bull`; первые строки без полного окна получают
    пустой код.
    """
    if lookback < 1:
        raise ValueError("lookback должен быть положительным")
    if bear_threshold >= bull_threshold:
        raise ValueError("bear_threshold должен быть меньше bull_threshold")

    rolling_return = close.astype(float).pct_change(periods=lookback)
    regime_code = pd.Series(pd.NA, index=close.index, dtype="Int64")
    known = rolling_return.notna()
    regime_code.loc[known] = SIDEWAYS
    regime_code.loc[rolling_return >= bull_threshold] = BULL
    regime_code.loc[rolling_return <= bear_threshold] = BEAR
    return rolling_return, regime_code


def build_transition_matrix(regime_codes: Sequence[int]) -> np.ndarray:
    """Строит 3x3 матрицу переходов `from_state -> to_state`.

    Строки без наблюдаемых переходов заполняются равномерным распределением,
    чтобы каждая строка оставалась вероятностной и суммировалась в `1.0`.
    """
    codes = [int(code) for code in regime_codes]
    counts = np.zeros((3, 3), dtype=float)
    for current_code, next_code in zip(codes[:-1], codes[1:]):
        _validate_regime_code(current_code)
        _validate_regime_code(next_code)
        counts[current_code, next_code] += 1.0

    matrix = np.zeros((3, 3), dtype=float)
    for row_index in range(3):
        row_sum = counts[row_index].sum()
        if row_sum == 0:
            matrix[row_index] = np.array([1.0 / 3.0] * 3)
        else:
            matrix[row_index] = counts[row_index] / row_sum
    return matrix


def stationary_distribution(matrix: np.ndarray) -> np.ndarray:
    """Вычисляет стационарное распределение марковской цепи."""
    values, vectors = np.linalg.eig(matrix.T)
    index = int(np.argmin(np.abs(values - 1.0)))
    vector = np.real(vectors[:, index])
    vector = np.abs(vector)
    total = vector.sum()
    if total == 0:
        return np.array([1.0 / 3.0] * 3)
    return vector / total


def add_markov_columns(
    quotes: pd.DataFrame,
    lookback: int = 20,
    bull_threshold: float = 0.05,
    bear_threshold: float = -0.05,
    min_train: int = 252,
    signal_scale: float = 1.0,
) -> pd.DataFrame:
    """Добавляет в DataFrame режимы, вероятности MM и торговые сигналы.

    Для строки `t` матрица переходов строится только по режимам, известным на
    закрытии `t`, то есть будущий переход `t -> t+1` не используется.
    """
    if "close" not in quotes.columns:
        raise ValueError("В quotes должна быть колонка close")
    if signal_scale <= 0:
        raise ValueError("signal_scale должен быть положительным")

    out = quotes.copy()
    out["cc_return"] = out["close"].astype(float).pct_change()
    if {"open", "close"}.issubset(out.columns):
        out["oc_return"] = out["close"].astype(float) / out["open"].astype(float) - 1.0

    rolling_return, regime_code = label_regimes(
        out["close"],
        lookback=lookback,
        bull_threshold=bull_threshold,
        bear_threshold=bear_threshold,
    )
    rolling_column = f"mm_rolling_return_{lookback}"
    out[rolling_column] = rolling_return
    out["mm_regime_code"] = regime_code
    out["mm_regime"] = regime_code.map(REGIME_NAMES)

    _initialize_markov_output_columns(out)

    for position, row_index in enumerate(out.index):
        current_code = regime_code.iloc[position]
        if pd.isna(current_code):
            continue

        history = regime_code.iloc[: position + 1].dropna().astype(int)
        if len(history) < min_train:
            continue

        matrix = build_transition_matrix(history.tolist())
        current_state = int(current_code)
        probabilities = matrix[current_state]
        signal = float(probabilities[BULL] - probabilities[BEAR])
        stationary = stationary_distribution(matrix)

        out.loc[row_index, "mm_p_bear_next"] = probabilities[BEAR]
        out.loc[row_index, "mm_p_sideways_next"] = probabilities[SIDEWAYS]
        out.loc[row_index, "mm_p_bull_next"] = probabilities[BULL]
        out.loc[row_index, "mm_signal"] = signal
        out.loc[row_index, "mm_position_sign"] = _sign(signal)
        out.loc[row_index, "mm_position_proportional"] = float(
            np.clip(signal / signal_scale, -1.0, 1.0)
        )
        out.loc[row_index, "mm_persistence_bear"] = matrix[BEAR, BEAR]
        out.loc[row_index, "mm_persistence_sideways"] = matrix[SIDEWAYS, SIDEWAYS]
        out.loc[row_index, "mm_persistence_bull"] = matrix[BULL, BULL]
        out.loc[row_index, "mm_stationary_bear"] = stationary[BEAR]
        out.loc[row_index, "mm_stationary_sideways"] = stationary[SIDEWAYS]
        out.loc[row_index, "mm_stationary_bull"] = stationary[BULL]

    return out


def _initialize_markov_output_columns(df: pd.DataFrame) -> None:
    """Создает числовые колонки результата MM со значениями NaN."""
    for column in [
        "mm_p_bear_next",
        "mm_p_sideways_next",
        "mm_p_bull_next",
        "mm_signal",
        "mm_position_sign",
        "mm_position_proportional",
        "mm_persistence_bear",
        "mm_persistence_sideways",
        "mm_persistence_bull",
        "mm_stationary_bear",
        "mm_stationary_sideways",
        "mm_stationary_bull",
    ]:
        df[column] = np.nan


def _sign(value: float) -> int:
    """Возвращает знак числа как торговую позицию `-1`, `0` или `1`."""
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _validate_regime_code(code: int) -> None:
    """Проверяет, что код режима входит в допустимый набор."""
    if code not in REGIME_NAMES:
        raise ValueError(f"Недопустимый код режима: {code}")
