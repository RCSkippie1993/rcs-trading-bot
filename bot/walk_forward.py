from dataclasses import dataclass, replace
from typing import Iterable, Sequence

from bot.backtest import run_backtest


@dataclass(frozen=True)
class WalkForwardFold:
    fold: int
    train_start: object
    train_end: object
    test_start: object
    test_end: object
    fast_window: int
    slow_window: int
    train_return_pct: float
    train_drawdown_pct: float
    test_return_pct: float
    test_benchmark_pct: float
    test_excess_pct: float
    test_drawdown_pct: float
    test_trades: int
    test_win_rate_pct: float
    test_profit_factor: float
    test_expectancy: float


def make_folds(bars: Sequence, train_bars: int, test_bars: int, step_bars: int | None = None):
    if train_bars <= 0 or test_bars <= 0:
        raise ValueError("train_bars and test_bars must be positive")
    if step_bars is None:
        step_bars = test_bars
    if step_bars <= 0:
        raise ValueError("step_bars must be positive")

    folds = []
    start = 0
    while start + train_bars + test_bars <= len(bars):
        train = bars[start : start + train_bars]
        test = bars[start + train_bars : start + train_bars + test_bars]
        folds.append((train, test))
        start += step_bars
    return folds


def candidate_score(result: dict) -> float:
    """Training-only selection score that rewards excess return and penalizes drawdown.

    The penalty reduces the chance that a single high-return/high-drawdown fit wins merely
    because it was the most aggressive parameter pair in the training sample.
    """
    return float(result["excess_return_pct"]) - 0.50 * float(result["max_drawdown_pct"])


def select_parameters(train_bars: Sequence, settings, candidates: Iterable[tuple[int, int]]):
    best = None
    for fast, slow in candidates:
        if fast >= slow or slow > len(train_bars):
            continue
        candidate_settings = replace(settings, fast_window=fast, slow_window=slow)
        result = run_backtest(train_bars, candidate_settings)
        score = candidate_score(result)
        item = (score, -result["max_drawdown_pct"], result["total_return_pct"], fast, slow, result)
        if best is None or item[:3] > best[:3]:
            best = item

    if best is None:
        raise RuntimeError("No valid walk-forward parameter candidate for this training window")

    _, _, _, fast, slow, result = best
    return fast, slow, result


def run_walk_forward(
    bars: Sequence,
    settings,
    candidates: Iterable[tuple[int, int]],
    train_bars: int,
    test_bars: int,
    step_bars: int | None = None,
):
    materialized = list(bars)
    fold_pairs = make_folds(materialized, train_bars, test_bars, step_bars)
    if not fold_pairs:
        raise RuntimeError(
            f"Insufficient history: need at least {train_bars + test_bars} bars, got {len(materialized)}"
        )

    output = []
    for index, (train, test) in enumerate(fold_pairs, start=1):
        fast, slow, train_result = select_parameters(train, settings, candidates)
        locked = replace(settings, fast_window=fast, slow_window=slow)
        test_result = run_backtest(test, locked)

        output.append(
            WalkForwardFold(
                fold=index,
                train_start=train[0].timestamp,
                train_end=train[-1].timestamp,
                test_start=test[0].timestamp,
                test_end=test[-1].timestamp,
                fast_window=fast,
                slow_window=slow,
                train_return_pct=float(train_result["total_return_pct"]),
                train_drawdown_pct=float(train_result["max_drawdown_pct"]),
                test_return_pct=float(test_result["total_return_pct"]),
                test_benchmark_pct=float(test_result["benchmark_return_pct"]),
                test_excess_pct=float(test_result["excess_return_pct"]),
                test_drawdown_pct=float(test_result["max_drawdown_pct"]),
                test_trades=int(test_result["trades"]),
                test_win_rate_pct=float(test_result["win_rate_pct"]),
                test_profit_factor=float(test_result["profit_factor"]),
                test_expectancy=float(test_result["expectancy_pnl"]),
            )
        )

    return output
