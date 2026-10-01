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


def run_backtest(bars: Iterable, settings: Settings) -> Dict[str, Any]:
    broker = PaperBroker(settings.starting_cash)
    risk = RiskManager(settings)
    strategy = MovingAverageCrossStrategy(settings.fast_window, settings.slow_window)

    trades: List[ClosedTrade] = []
    equity_curve: List[float] = [settings.starting_cash]
    entry_time = None
    last_bar = None

    for bar in bars:
        last_bar = bar
        price = float(bar.close)
        signal = strategy.on_price(price)
        equity = broker.equity(price)
        equity_curve.append(equity)

        if broker.position:
            entry = broker.position.entry_price
            stop_price = entry * (1 - settings.stop_loss_pct)
            target_price = entry * (1 + settings.take_profit_pct)

            exit_reason = None
            if price <= stop_price:
                exit_reason = "stop"
            elif price >= target_price:
                exit_reason = "target"
            elif signal == "SELL":
                exit_reason = "signal"

            if exit_reason:
                pos = broker.position
                result = broker.sell_all(price)
                trades.append(
                    ClosedTrade(
                        entry_price=entry,
                        exit_price=price,
                        quantity=pos.quantity,
                        pnl=float(result["pnl"]),
                        return_pct=(price / entry - 1.0) if entry else 0.0,
                        exit_reason=exit_reason,
                        entry_time=entry_time,
                        exit_time=bar.timestamp,
                    )
                )
                entry_time = None
                equity_curve.append(broker.cash)
                continue

        if signal == "BUY" and broker.position is None:
            equity = broker.equity(price)
            if risk.can_open_trade(equity):
                qty = risk.position_size(equity, price)
                if broker.buy(price, qty):
                    risk.record_trade()
                    entry_time = bar.timestamp

    if broker.position and last_bar is not None:
        price = float(last_bar.close)
        pos = broker.position
        entry = pos.entry_price
        result = broker.sell_all(price)
        trades.append(
            ClosedTrade(
                entry_price=entry,
                exit_price=price,
                quantity=pos.quantity,
                pnl=float(result["pnl"]),
                return_pct=(price / entry - 1.0) if entry else 0.0,
                exit_reason="end_of_test",
                entry_time=entry_time,
                exit_time=last_bar.timestamp,
            )
        )
        equity_curve.append(broker.cash)

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)
    total_return = (broker.cash / settings.starting_cash - 1.0) if settings.starting_cash else 0.0

    return {
        "starting_equity": settings.starting_cash,
        "ending_equity": broker.cash,
        "net_pnl": broker.cash - settings.starting_cash,
        "total_return_pct": total_return * 100,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": (len(wins) / len(trades) * 100) if trades else 0.0,
        "profit_factor": profit_factor,
        "max_drawdown_pct": _max_drawdown(equity_curve) * 100,
        "closed_trades": trades,
    }
