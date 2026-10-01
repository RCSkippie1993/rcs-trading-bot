from dataclasses import dataclass
from typing import Iterable, List, Dict, Any

from bot.broker import PaperBroker
from bot.config import Settings
from bot.risk import RiskManager
from bot.strategy import MovingAverageCrossStrategy


@dataclass
class ClosedTrade:
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    return_pct: float
    exit_reason: str
    entry_time: object
    exit_time: object


def _max_drawdown(equity_curve: List[float]) -> float:
    peak = None
    worst = 0.0
    for equity in equity_curve:
        if peak is None or equity > peak:
            peak = equity
        if peak and peak > 0:
            drawdown = (peak - equity) / peak
            worst = max(worst, drawdown)
    return worst


def _session_key(timestamp: object):
    if hasattr(timestamp, "date"):
        return timestamp.date()
    return str(timestamp)[:10]


def run_backtest(bars: Iterable, settings: Settings) -> Dict[str, Any]:
    bars = list(bars)
    if not bars:
        raise RuntimeError("Backtest requires at least one market bar.")

    broker = PaperBroker(
        settings.starting_cash,
        fee_bps=settings.fee_bps,
        slippage_bps=settings.slippage_bps,
    )
    risk = RiskManager(settings)
    strategy = MovingAverageCrossStrategy(settings.fast_window, settings.slow_window)

    trades: List[ClosedTrade] = []
    equity_curve: List[float] = [settings.starting_cash]
    entry_time = None
    current_session = None

    first_close = float(bars[0].close)
    last_close = first_close

    for bar in bars:
        last_close = float(bar.close)
        signal = strategy.on_price(last_close)
        equity = broker.equity(last_close)

        session = _session_key(bar.timestamp)
        if current_session is None or session != current_session:
            current_session = session
            risk.reset_session(equity)

        if broker.position:
            entry = broker.position.entry_price
            stop_price = entry * (1 - settings.stop_loss_pct)
            target_price = entry * (1 + settings.take_profit_pct)

            exit_reason = None
            exit_price = None

            # Conservative intrabar assumption: if both stop and target are touched
            # in the same candle, assume the stop was hit first.
            if float(bar.low) <= stop_price:
                exit_reason = "stop"
                exit_price = stop_price
            elif float(bar.high) >= target_price:
                exit_reason = "target"
                exit_price = target_price
            elif signal == "SELL":
                exit_reason = "signal"
                exit_price = last_close

            if exit_reason:
                pos = broker.position
                result = broker.sell_all(exit_price)
                trades.append(
                    ClosedTrade(
                        entry_price=entry,
                        exit_price=float(result["price"]),
                        quantity=pos.quantity,
                        pnl=float(result["pnl"]),
                        return_pct=(float(result["price"]) / entry - 1.0) if entry else 0.0,
                        exit_reason=exit_reason,
                        entry_time=entry_time,
                        exit_time=bar.timestamp,
                    )
                )
                entry_time = None
                equity_curve.append(broker.cash)
                continue

        if signal == "BUY" and broker.position is None:
            equity = broker.equity(last_close)
            if risk.can_open_trade(equity):
                qty = risk.position_size(equity, last_close)
                fill = broker.buy(last_close, qty)
                if fill:
                    risk.record_trade()
                    entry_time = bar.timestamp

        equity_curve.append(broker.equity(last_close))

    if broker.position:
        pos = broker.position
        entry = pos.entry_price
        result = broker.sell_all(last_close)
        trades.append(
            ClosedTrade(
                entry_price=entry,
                exit_price=float(result["price"]),
                quantity=pos.quantity,
                pnl=float(result["pnl"]),
                return_pct=(float(result["price"]) / entry - 1.0) if entry else 0.0,
                exit_reason="end_of_test",
                entry_time=entry_time,
                exit_time=bars[-1].timestamp,
            )
        )
        equity_curve.append(broker.cash)

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)
    total_return = (broker.cash / settings.starting_cash - 1.0) if settings.starting_cash else 0.0
    benchmark_return = (last_close / first_close - 1.0) if first_close else 0.0
    avg_trade = (sum(t.pnl for t in trades) / len(trades)) if trades else 0.0
    avg_win = (gross_profit / len(wins)) if wins else 0.0
    avg_loss = (gross_loss / len(losses)) if losses else 0.0
    expectancy = (
        (len(wins) / len(trades)) * avg_win - (len(losses) / len(trades)) * avg_loss
        if trades else 0.0
    )

    return {
        "starting_equity": settings.starting_cash,
        "ending_equity": broker.cash,
        "net_pnl": broker.cash - settings.starting_cash,
        "total_return_pct": total_return * 100,
        "benchmark_return_pct": benchmark_return * 100,
        "excess_return_pct": (total_return - benchmark_return) * 100,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": (len(wins) / len(trades) * 100) if trades else 0.0,
        "profit_factor": profit_factor,
        "max_drawdown_pct": _max_drawdown(equity_curve) * 100,
        "avg_trade_pnl": avg_trade,
        "expectancy_pnl": expectancy,
        "total_fees": broker.total_fees,
        "closed_trades": trades,
        "equity_curve": equity_curve,
    }
