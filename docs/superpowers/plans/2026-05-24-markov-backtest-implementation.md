# Markov Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working implementation that loads daily futures quotes from SQLite, creates MM regime/probability/signal columns, and runs an open-to-close walk-forward backtest.

**Architecture:** Keep the code as small Python modules with clear boundaries: data loading, Markov calculations, and backtest execution. Use `unittest` so the project works without adding a test framework dependency. Use `pandas` and `numpy` for tabular calculations and matrix math.

**Tech Stack:** Python 3, SQLite, pandas, numpy, unittest.

---

## File Structure

- Create `pj25_funds/__init__.py`: package marker and version.
- Create `pj25_funds/data.py`: SQLite quote loader for the `Futures` table.
- Create `pj25_funds/markov.py`: MM regime labeling, transition matrix, probabilities, stationary distribution, and signal columns.
- Create `pj25_funds/backtest.py`: open-to-close walk-forward backtest using precomputed signal columns.
- Create `scripts/run_markov_backtest.py`: CLI runner for MIX/RTS/Si databases.
- Create `tests/test_data.py`: tests SQLite loading with a temporary DB.
- Create `tests/test_markov.py`: tests regime labels, transition probabilities, and no-lookahead behavior.
- Create `tests/test_backtest.py`: tests open-to-close return alignment.
- Create `requirements.txt`: pinned installed dependencies after package installation.

## Task 1: Dependencies

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Install runtime dependencies**

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install pandas numpy
```

Expected: command exits with code `0`.

- [ ] **Step 2: Capture installed dependencies**

Run:

```powershell
.\.venv\Scripts\python.exe -m pip freeze
```

Expected: output includes `numpy==...` and `pandas==...`.

- [ ] **Step 3: Write `requirements.txt`**

Write the exact `pip freeze` output to `requirements.txt`.

## Task 2: SQLite Loader

**Files:**
- Create: `tests/test_data.py`
- Create: `pj25_funds/data.py`

- [ ] **Step 1: Write failing tests**

Test behavior:

```python
def test_load_futures_quotes_orders_rows_and_normalizes_columns():
    path = create_temp_futures_db_with_reverse_dates()
    df = load_futures_quotes(path, symbol="MIX")
    assert list(df.columns) == ["date", "open", "low", "high", "close", "secid", "lsttrade", "symbol"]
    assert df["date"].tolist() == [Timestamp("2025-01-02"), Timestamp("2025-01-03")]
    assert df["symbol"].tolist() == ["MIX", "MIX"]
```

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_data -v
```

Expected: fail because `pj25_funds.data` does not exist.

- [ ] **Step 2: Implement loader**

Create `load_futures_quotes(db_path, symbol=None)` that reads `Futures`, renames columns to lowercase, sorts by `date`, validates required columns, and returns a DataFrame.

- [ ] **Step 3: Verify tests pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_data -v
```

Expected: pass.

## Task 3: Markov Model Columns

**Files:**
- Create: `tests/test_markov.py`
- Create: `pj25_funds/markov.py`

- [ ] **Step 1: Write failing tests**

Test behavior:

```python
def test_add_markov_columns_uses_only_past_transitions_for_next_probabilities():
    df = sample_quotes_with_known_closes()
    result = add_markov_columns(df, lookback=1, bull_threshold=0.01, bear_threshold=-0.01, min_train=3)
    assert result.loc[3, "mm_p_bull_next"] == 0.5
    assert result.loc[3, "mm_p_bear_next"] == 0.5
    assert result.loc[3, "mm_signal"] == 0.0
```

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_markov -v
```

Expected: fail because `pj25_funds.markov` does not exist.

- [ ] **Step 2: Implement MM functions**

Create `label_regimes`, `build_transition_matrix`, `stationary_distribution`, and `add_markov_columns`.

- [ ] **Step 3: Verify tests pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_markov -v
```

Expected: pass.

## Task 4: Walk-forward Backtest

**Files:**
- Create: `tests/test_backtest.py`
- Create: `pj25_funds/backtest.py`

- [ ] **Step 1: Write failing tests**

Test behavior:

```python
def test_backtest_uses_signal_from_t_and_open_close_return_from_next_day():
    df = sample_signal_df()
    trades, metrics = run_open_close_backtest(df, signal_column="mm_signal", threshold=0.0)
    assert trades.loc[0, "entry_date"] == Timestamp("2025-01-03")
    assert trades.loc[0, "gross_return"] == 0.10
```

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_backtest -v
```

Expected: fail because `pj25_funds.backtest` does not exist.

- [ ] **Step 2: Implement backtest**

Create `run_open_close_backtest` that converts signal to position, shifts execution to the next row, computes gross/net returns, equity, drawdown, and summary metrics.

- [ ] **Step 3: Verify tests pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_backtest -v
```

Expected: pass.

## Task 5: CLI Smoke Runner

**Files:**
- Create: `scripts/run_markov_backtest.py`

- [ ] **Step 1: Write CLI script**

Script accepts one or more `--db` paths, computes MM columns and backtest, and prints per-symbol metrics.

- [ ] **Step 2: Run all tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

Expected: all tests pass.

- [ ] **Step 3: Run smoke test on provided databases**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_markov_backtest.py --db C:\Users\Alkor\gd\data_quote_db\MIX_futures_day_2025_21-00.db --db C:\Users\Alkor\gd\data_quote_db\RTS_futures_day_2025_21-00.db --db C:\Users\Alkor\gd\data_quote_db\Si_futures_day_2025_21-00.db
```

Expected: prints one result block for each database.
