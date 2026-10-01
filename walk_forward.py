import csv
import math
import os
from dataclasses import replace
from pathlib import Path
from statistics import median

from bot.config import Settings
from bot.data import YahooFinanceData
from bot.walk_forward import run_walk_forward
from portfolio_backtest import DEFAULT_SYMBOLS, parse_symbols


CANDIDATES = [(3, 10), (5, 12), (8, 20), (10, 30)]


def fmt_pf(value: float) -> str:
    return "inf" if math.isinf(value) else f"{value:.2f}"


def compound_returns(percentages: list[float]) -> float:
    equity = 1.0
    for pct in percentages:
        equity *= 1.0 + pct / 100.0
    return (equity - 1.0) * 100.0


def main():
    base = Settings()
    symbols = parse_symbols()
    period = os.getenv("RCS_WF_PERIOD", "2y")
    interval = os.getenv("RCS_WF_INTERVAL", "1d")
    train_bars = int(os.getenv("RCS_WF_TRAIN_BARS", "252"))
    test_bars = int(os.getenv("RCS_WF_TEST_BARS", "63"))
    step_bars = int(os.getenv("RCS_WF_STEP_BARS", str(test_bars)))

    reports = Path("reports")
    reports.mkdir(exist_ok=True)

    rows = []
    failures = []

    for symbol in symbols:
        try:
            settings = replace(base, symbol=symbol, period=period, interval=interval)
            data = YahooFinanceData(symbol=symbol, period=period, interval=interval)
            bars = list(data.bars())
            folds = run_walk_forward(
                bars,
                settings,
                candidates=CANDIDATES,
                train_bars=train_bars,
                test_bars=test_bars,
                step_bars=step_bars,
            )

            test_returns = [fold.test_return_pct for fold in folds]
            benchmark_returns = [fold.test_benchmark_pct for fold in folds]
            excess_returns = [fold.test_excess_pct for fold in folds]
            drawdowns = [fold.test_drawdown_pct for fold in folds]
            positive_folds = sum(1 for fold in folds if fold.test_return_pct > 0)
            beat_folds = sum(1 for fold in folds if fold.test_excess_pct > 0)

            strategy_compound = compound_returns(test_returns)
            benchmark_compound = compound_returns(benchmark_returns)
            summary = {
                "symbol": symbol,
                "folds": len(folds),
                "strategy_compound_pct": strategy_compound,
                "benchmark_compound_pct": benchmark_compound,
                "excess_compound_pct": strategy_compound - benchmark_compound,
                "positive_fold_pct": positive_folds / len(folds) * 100.0,
                "beat_benchmark_fold_pct": beat_folds / len(folds) * 100.0,
                "median_test_return_pct": median(test_returns),
                "median_excess_pct": median(excess_returns),
                "median_drawdown_pct": median(drawdowns),
            }
            rows.append(summary)

            with (reports / f"walk_forward_{symbol.replace('.', '_')}.csv").open(
                "w", newline="", encoding="utf-8"
            ) as f:
                writer = csv.writer(f)
                writer.writerow([
                    "fold", "train_start", "train_end", "test_start", "test_end",
                    "fast_window", "slow_window", "train_return_pct", "train_drawdown_pct",
                    "test_return_pct", "test_benchmark_pct", "test_excess_pct",
                    "test_drawdown_pct", "test_trades", "test_win_rate_pct",
                    "test_profit_factor", "test_expectancy_account_units",
                ])
                for fold in folds:
                    writer.writerow([
                        fold.fold, fold.train_start, fold.train_end, fold.test_start, fold.test_end,
                        fold.fast_window, fold.slow_window,
                        f"{fold.train_return_pct:.4f}", f"{fold.train_drawdown_pct:.4f}",
                        f"{fold.test_return_pct:.4f}", f"{fold.test_benchmark_pct:.4f}",
                        f"{fold.test_excess_pct:.4f}", f"{fold.test_drawdown_pct:.4f}",
                        fold.test_trades, f"{fold.test_win_rate_pct:.4f}",
                        fmt_pf(fold.test_profit_factor), f"{fold.test_expectancy:.4f}",
                    ])

            print(
                f"{symbol:8s} folds={len(folds):2d} "
                f"oos={strategy_compound:7.2f}% benchmark={benchmark_compound:7.2f}% "
                f"excess={strategy_compound - benchmark_compound:7.2f}%"
            )
        except Exception as exc:
            failures.append((symbol, str(exc)))
            print(f"{symbol:8s} FAILED: {exc}")

    with (reports / "walk_forward_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "symbol", "folds", "strategy_oos_compound_pct", "benchmark_compound_pct",
            "excess_compound_pct", "positive_fold_pct", "beat_benchmark_fold_pct",
            "median_test_return_pct", "median_excess_pct", "median_drawdown_pct",
        ])
        for row in rows:
            writer.writerow([
                row["symbol"], row["folds"], f"{row['strategy_compound_pct']:.4f}",
                f"{row['benchmark_compound_pct']:.4f}", f"{row['excess_compound_pct']:.4f}",
                f"{row['positive_fold_pct']:.2f}", f"{row['beat_benchmark_fold_pct']:.2f}",
                f"{row['median_test_return_pct']:.4f}", f"{row['median_excess_pct']:.4f}",
                f"{row['median_drawdown_pct']:.4f}",
            ])

    lines = [
        "RCS Trading Bot — PHASE 2C WALK-FORWARD VALIDATION",
        f"History / interval: {period} / {interval}",
        f"Train / test / step bars: {train_bars} / {test_bars} / {step_bars}",
        f"Parameter candidates: {CANDIDATES}",
        f"Symbols requested: {len(symbols)}",
        f"Successful symbols: {len(rows)}",
        f"Failed symbols: {len(failures)}",
    ]

    if rows:
        lines.extend([
            f"Symbols with positive compounded OOS return: {sum(r['strategy_compound_pct'] > 0 for r in rows)}/{len(rows)}",
            f"Symbols beating compounded benchmark OOS: {sum(r['excess_compound_pct'] > 0 for r in rows)}/{len(rows)}",
            f"Median compounded OOS return: {median(r['strategy_compound_pct'] for r in rows):.2f}%",
            f"Median compounded OOS excess return: {median(r['excess_compound_pct'] for r in rows):.2f}%",
            f"Median OOS drawdown across symbols: {median(r['median_drawdown_pct'] for r in rows):.2f}%",
        ])

    if failures:
        lines.append("Failures:")
        lines.extend(f"- {symbol}: {error}" for symbol, error in failures)

    text = "\n".join(lines) + "\n"
    print("\n" + text, end="")
    (reports / "walk_forward_summary.txt").write_text(text, encoding="utf-8")

    if not rows:
        raise RuntimeError("No symbol completed walk-forward validation successfully")


if __name__ == "__main__":
    main()
