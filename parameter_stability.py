import csv
import os
from dataclasses import replace
from pathlib import Path
from statistics import median

from bot.backtest import run_backtest
from bot.config import Settings
from bot.data import YahooFinanceData
from portfolio_backtest import parse_symbols


FAST_WINDOWS = [3, 5, 8, 10, 12]
SLOW_WINDOWS = [10, 12, 15, 20, 25, 30, 40]


def parameter_grid() -> list[tuple[int, int]]:
    return [(fast, slow) for fast in FAST_WINDOWS for slow in SLOW_WINDOWS if fast < slow]


def main():
    base = Settings()
    symbols = parse_symbols()
    period = os.getenv("RCS_STAB_PERIOD", "2y")
    interval = os.getenv("RCS_STAB_INTERVAL", "1d")
    reports = Path("reports")
    reports.mkdir(exist_ok=True)

    grid = parameter_grid()
    symbol_bars = {}
    failures = []

    for symbol in symbols:
        try:
            data = YahooFinanceData(symbol=symbol, period=period, interval=interval)
            symbol_bars[symbol] = list(data.bars())
        except Exception as exc:
            failures.append((symbol, str(exc)))
            print(f"{symbol:8s} DATA FAILED: {exc}")

    rows = []
    detail_rows = []

    for fast, slow in grid:
        results = []
        for symbol, bars in symbol_bars.items():
            settings = replace(
                base,
                symbol=symbol,
                period=period,
                interval=interval,
                fast_window=fast,
                slow_window=slow,
            )
            result = run_backtest(bars, settings)
            results.append(result)
            detail_rows.append({
                "symbol": symbol,
                "fast": fast,
                "slow": slow,
                "return": result["total_return_pct"],
                "benchmark": result["benchmark_return_pct"],
                "excess": result["excess_return_pct"],
                "drawdown": result["max_drawdown_pct"],
                "trades": result["trades"],
                "win_rate": result["win_rate_pct"],
                "profit_factor": result["profit_factor"],
            })

        if not results:
            continue

        returns = [r["total_return_pct"] for r in results]
        excess = [r["excess_return_pct"] for r in results]
        drawdowns = [r["max_drawdown_pct"] for r in results]
        positive_pct = sum(r > 0 for r in returns) / len(returns) * 100.0
        beat_pct = sum(r > 0 for r in excess) / len(excess) * 100.0
        low_drawdown_pct = sum(d <= 10.0 for d in drawdowns) / len(drawdowns) * 100.0

        rows.append({
            "fast": fast,
            "slow": slow,
            "symbols": len(results),
            "positive_pct": positive_pct,
            "beat_pct": beat_pct,
            "low_drawdown_pct": low_drawdown_pct,
            "median_return": median(returns),
            "median_excess": median(excess),
            "median_drawdown": median(drawdowns),
        })

        print(
            f"SMA {fast:2d}/{slow:2d} positive={positive_pct:5.1f}% "
            f"beat={beat_pct:5.1f}% median={median(returns):7.2f}% "
            f"dd={median(drawdowns):6.2f}%"
        )

    with (reports / "parameter_stability.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "fast_window", "slow_window", "symbols", "positive_symbol_pct",
            "beat_benchmark_symbol_pct", "drawdown_le_10pct_symbol_pct",
            "median_return_pct", "median_excess_pct", "median_drawdown_pct",
        ])
        for row in rows:
            writer.writerow([
                row["fast"], row["slow"], row["symbols"],
                f"{row['positive_pct']:.2f}", f"{row['beat_pct']:.2f}",
                f"{row['low_drawdown_pct']:.2f}", f"{row['median_return']:.4f}",
                f"{row['median_excess']:.4f}", f"{row['median_drawdown']:.4f}",
            ])

    with (reports / "parameter_stability_detail.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "symbol", "fast_window", "slow_window", "return_pct",
            "benchmark_pct", "excess_pct", "max_drawdown_pct", "trades",
            "win_rate_pct", "profit_factor",
        ])
        for row in detail_rows:
            writer.writerow([
                row["symbol"], row["fast"], row["slow"],
                f"{row['return']:.4f}", f"{row['benchmark']:.4f}",
                f"{row['excess']:.4f}", f"{row['drawdown']:.4f}",
                row["trades"], f"{row['win_rate']:.4f}", row["profit_factor"],
            ])

    robust = [
        row for row in rows
        if row["positive_pct"] >= 60.0
        and row["beat_pct"] >= 50.0
        and row["median_drawdown"] <= 10.0
    ]

    lines = [
        "RCS Trading Bot — PHASE 2D PARAMETER STABILITY",
        f"History / interval: {period} / {interval}",
        f"Symbols requested: {len(symbols)}",
        f"Symbols with usable data: {len(symbol_bars)}",
        f"Parameter combinations tested: {len(rows)}",
        f"Broad-stability combinations: {len(robust)}",
        "Broad-stability rule: >=60% symbols positive, >=50% beat benchmark, median drawdown <=10%.",
    ]

    if rows:
        lines.extend([
            f"Median of parameter-grid median returns: {median(r['median_return'] for r in rows):.2f}%",
            f"Median of parameter-grid median excess returns: {median(r['median_excess'] for r in rows):.2f}%",
            f"Median of parameter-grid median drawdowns: {median(r['median_drawdown'] for r in rows):.2f}%",
        ])

    if robust:
        lines.append("Stable plateau combinations:")
        for row in sorted(robust, key=lambda r: (r["fast"], r["slow"])):
            lines.append(
                f"- SMA {row['fast']}/{row['slow']}: positive {row['positive_pct']:.1f}%, "
                f"beat benchmark {row['beat_pct']:.1f}%, median return {row['median_return']:.2f}%, "
                f"median drawdown {row['median_drawdown']:.2f}%"
            )
    else:
        lines.append("No parameter combination met the broad-stability rule.")

    if failures:
        lines.append("Data failures:")
        lines.extend(f"- {symbol}: {error}" for symbol, error in failures)

    text = "\n".join(lines) + "\n"
    print("\n" + text, end="")
    (reports / "parameter_stability_summary.txt").write_text(text, encoding="utf-8")

    if not rows:
        raise RuntimeError("No Phase 2D parameter stability results could be produced")


if __name__ == "__main__":
    main()
