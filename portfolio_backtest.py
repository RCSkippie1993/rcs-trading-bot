import csv
import math
import os
from dataclasses import replace
from pathlib import Path
from statistics import median

from bot.backtest import run_backtest
from bot.config import Settings
from bot.data import YahooFinanceData


DEFAULT_SYMBOLS = [
    "SOL.JO",
    "NPN.JO",
    "MTN.JO",
    "FSR.JO",
    "SBK.JO",
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
]


def parse_symbols() -> list[str]:
    raw = os.getenv("RCS_SYMBOLS", "").strip()
    if not raw:
        return DEFAULT_SYMBOLS
    return [item.strip().upper() for item in raw.split(",") if item.strip()]


def fmt_pf(value: float) -> str:
    return "inf" if math.isinf(value) else f"{value:.2f}"


def main():
    base = Settings()
    symbols = parse_symbols()
    reports = Path("reports")
    reports.mkdir(exist_ok=True)

    rows = []
    failures = []

    for symbol in symbols:
        settings = replace(base, symbol=symbol)
        try:
            data = YahooFinanceData(
                symbol=symbol,
                period=settings.period,
                interval=settings.interval,
            )
            result = run_backtest(data.bars(), settings)
            rows.append({
                "symbol": symbol,
                "total_return_pct": result["total_return_pct"],
                "benchmark_return_pct": result["benchmark_return_pct"],
                "excess_return_pct": result["excess_return_pct"],
                "trades": result["trades"],
                "wins": result["wins"],
                "losses": result["losses"],
                "win_rate_pct": result["win_rate_pct"],
                "profit_factor": result["profit_factor"],
                "max_drawdown_pct": result["max_drawdown_pct"],
                "expectancy_pnl": result["expectancy_pnl"],
                "total_fees": result["total_fees"],
            })
            print(
                f"{symbol:8s} return={result['total_return_pct']:7.2f}% "
                f"benchmark={result['benchmark_return_pct']:7.2f}% "
                f"excess={result['excess_return_pct']:7.2f}% "
                f"trades={result['trades']:3d} "
                f"dd={result['max_drawdown_pct']:6.2f}%"
            )
        except Exception as exc:
            failures.append((symbol, str(exc)))
            print(f"{symbol:8s} FAILED: {exc}")

    with (reports / "portfolio_comparison.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "symbol",
            "total_return_pct",
            "benchmark_return_pct",
            "excess_return_pct",
            "trades",
            "wins",
            "losses",
            "win_rate_pct",
            "profit_factor",
            "max_drawdown_pct",
            "expectancy_account_units",
            "modeled_fees_account_units",
        ])
        for row in rows:
            writer.writerow([
                row["symbol"],
                f"{row['total_return_pct']:.4f}",
                f"{row['benchmark_return_pct']:.4f}",
                f"{row['excess_return_pct']:.4f}",
                row["trades"],
                row["wins"],
                row["losses"],
                f"{row['win_rate_pct']:.4f}",
                fmt_pf(row["profit_factor"]),
                f"{row['max_drawdown_pct']:.4f}",
                f"{row['expectancy_pnl']:.4f}",
                f"{row['total_fees']:.4f}",
            ])

    successful = len(rows)
    positive = sum(1 for row in rows if row["total_return_pct"] > 0)
    beat_benchmark = sum(1 for row in rows if row["excess_return_pct"] > 0)
    profitable_expectancy = sum(1 for row in rows if row["expectancy_pnl"] > 0)

    returns = [row["total_return_pct"] for row in rows]
    excess = [row["excess_return_pct"] for row in rows]
    drawdowns = [row["max_drawdown_pct"] for row in rows]

    lines = [
        "RCS Trading Bot — PHASE 2B MULTI-SYMBOL ROBUSTNESS REPORT",
        f"Period / interval: {base.period} / {base.interval}",
        f"Fees / slippage: {base.fee_bps:.1f} / {base.slippage_bps:.1f} bps per side",
        f"Symbols requested: {len(symbols)}",
        f"Successful backtests: {successful}",
        f"Failed data runs: {len(failures)}",
    ]

    if rows:
        lines.extend([
            f"Positive-return instruments: {positive}/{successful} ({positive / successful * 100:.1f}%)",
            f"Beat buy-and-hold benchmark: {beat_benchmark}/{successful} ({beat_benchmark / successful * 100:.1f}%)",
            f"Positive expectancy: {profitable_expectancy}/{successful} ({profitable_expectancy / successful * 100:.1f}%)",
            f"Median strategy return: {median(returns):.2f}%",
            f"Median excess return: {median(excess):.2f}%",
            f"Median max drawdown: {median(drawdowns):.2f}%",
        ])

    if failures:
        lines.append("Failures:")
        lines.extend(f"- {symbol}: {error}" for symbol, error in failures)

    text = "\n".join(lines) + "\n"
    print("\n" + text, end="")
    (reports / "portfolio_summary.txt").write_text(text, encoding="utf-8")

    if not rows:
        raise RuntimeError("No symbol completed successfully; no Phase 2B comparison could be produced.")


if __name__ == "__main__":
    main()
