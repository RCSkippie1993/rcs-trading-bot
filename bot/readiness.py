import math
from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class ReadinessThresholds:
    min_closed_trades: int = 30
    min_total_return_pct: float = 0.0
    min_profit_factor: float = 1.20
    max_drawdown_pct: float = 10.0
    min_positive_symbol_pct: float = 60.0


def profit_factor(gross_profit: float, gross_loss: float) -> float:
    if gross_loss > 0:
        return gross_profit / gross_loss
    return math.inf if gross_profit > 0 else 0.0


def evaluate_symbol(state: Mapping, thresholds: ReadinessThresholds = ReadinessThresholds()) -> dict:
    starting_cash = float(state.get("starting_cash") or 0.0)
    cash = float(state.get("cash") or 0.0)
    closed_trades = int(state.get("closed_trades") or 0)
    wins = int(state.get("wins") or 0)
    gross_profit = float(state.get("gross_profit") or 0.0)
    gross_loss = float(state.get("gross_loss") or 0.0)
    max_dd = float(state.get("max_drawdown_pct") or 0.0)
    halted = bool(state.get("halted", False))

    total_return_pct = ((cash / starting_cash) - 1.0) * 100.0 if starting_cash > 0 else 0.0
    pf = profit_factor(gross_profit, gross_loss)
    win_rate_pct = (wins / closed_trades * 100.0) if closed_trades else 0.0

    enough_data = closed_trades >= thresholds.min_closed_trades
    gates = {
        "enough_closed_trades": enough_data,
        "positive_return_after_costs": total_return_pct > thresholds.min_total_return_pct,
        "profit_factor": pf >= thresholds.min_profit_factor,
        "drawdown": max_dd <= thresholds.max_drawdown_pct,
        "not_halted": not halted,
    }

    if not enough_data:
        status = "INSUFFICIENT DATA"
    elif all(gates.values()):
        status = "READY FOR MANUAL REVIEW"
    else:
        status = "NOT READY"

    return {
        "status": status,
        "closed_trades": closed_trades,
        "win_rate_pct": win_rate_pct,
        "total_return_pct": total_return_pct,
        "profit_factor": pf,
        "max_drawdown_pct": max_dd,
        "realized_pnl": float(state.get("realized_pnl") or 0.0),
        "total_fees": float(state.get("total_fees") or 0.0),
        "bars_processed": int(state.get("bars_processed") or 0),
        "halted": halted,
        "gates": gates,
    }


def evaluate_portfolio(symbol_results: Iterable[Mapping], thresholds: ReadinessThresholds = ReadinessThresholds()) -> dict:
    rows = list(symbol_results)
    if not rows:
        return {
            "status": "INSUFFICIENT DATA",
            "symbols": 0,
            "positive_symbol_pct": 0.0,
            "review_ready_symbols": 0,
        }

    adequate = [r for r in rows if r.get("status") != "INSUFFICIENT DATA"]
    if not adequate:
        return {
            "status": "INSUFFICIENT DATA",
            "symbols": len(rows),
            "positive_symbol_pct": 0.0,
            "review_ready_symbols": 0,
        }

    positive = sum(1 for r in adequate if float(r.get("total_return_pct", 0.0)) > 0)
    ready = sum(1 for r in adequate if r.get("status") == "READY FOR MANUAL REVIEW")
    positive_pct = positive / len(adequate) * 100.0

    status = (
        "READY FOR MANUAL REVIEW"
        if positive_pct >= thresholds.min_positive_symbol_pct and ready >= max(1, math.ceil(len(adequate) / 2))
        else "NOT READY"
    )

    return {
        "status": status,
        "symbols": len(rows),
        "symbols_with_enough_data": len(adequate),
        "positive_symbol_pct": positive_pct,
        "review_ready_symbols": ready,
    }
