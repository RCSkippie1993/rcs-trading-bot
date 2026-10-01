import csv
import math
from pathlib import Path

from bot.backtest import run_backtest
from bot.config import Settings
from bot.data import YahooFinanceData


def fmt_pf(value: float) -> str:
    return "inf" if math.isinf(value) else f"{value:.2f}"


def main():
    settings = Settings()
    data = YahooFinanceData(
        symbol=settings.symbol,
        period=settings.period,
        interval=settings.interval,
    )
    result = run_backtest(data.bars(), settings)

    lines = [
        "RCS Trading Bot — PHASE 2 BACKTEST",
        f"Symbol: {settings.symbol}",
        f"Period / interval: {settings.period} / {settings.interval}",
        f"Fees / slippage: {settings.fee_bps:.1f} / {settings.slippage_bps:.1f} bps per side",
        f"Starting equity: R{result['starting_equity']:,.2f}",
        f"Ending equity: R{result['ending_equity']:,.2f}",
        f"Net P&L: R{result['net_pnl']:,.2f}",
        f"Total return: {result['total_return_pct']:.2f}%",
        f"Buy-and-hold benchmark: {result['benchmark_return_pct']:.2f}%",
        f"Excess return vs benchmark: {result['excess_return_pct']:.2f}%",
        f"Closed trades: {result['trades']}",
        f"Wins / losses: {result['wins']} / {result['losses']}",
        f"Win rate: {result['win_rate_pct']:.2f}%",
        f"Profit factor: {fmt_pf(result['profit_factor'])}",
        f"Max drawdown: {result['max_drawdown_pct']:.2f}%",
        f"Average trade P&L: R{result['avg_trade_pnl']:,.2f}",
        f"Expectancy per trade: R{result['expectancy_pnl']:,.2f}",
        f"Total modeled fees: R{result['total_fees']:,.2f}",
    ]

    text = "\n".join(lines) + "\n"
    print(text, end="")

    reports = Path("reports")
    reports.mkdir(exist_ok=True)
    (reports / "latest_summary.txt").write_text(text, encoding="utf-8")

    with (reports / "latest_trades.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "entry_time", "exit_time", "entry_price", "exit_price",
            "quantity", "pnl", "return_pct", "exit_reason"
        ])
        for trade in result["closed_trades"]:
            writer.writerow([
                trade.entry_time,
                trade.exit_time,
                f"{trade.entry_price:.4f}",
                f"{trade.exit_price:.4f}",
                trade.quantity,
                f"{trade.pnl:.2f}",
                f"{trade.return_pct * 100:.4f}",
                trade.exit_reason,
            ])

    with (reports / "latest_equity.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["step", "equity"])
        for i, equity in enumerate(result["equity_curve"]):
            writer.writerow([i, f"{equity:.2f}"])


if __name__ == "__main__":
    main()
