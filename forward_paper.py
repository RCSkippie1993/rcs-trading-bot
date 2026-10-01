import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bot.config import Settings
from bot.data import YahooFinanceData
from bot.forward import ForwardPaperEngine, JsonStateStore


def interval_delta(interval: str) -> timedelta:
    value = interval.strip().lower()
    units = {
        "m": "minutes",
        "h": "hours",
        "d": "days",
    }
    suffix = value[-1:]
    if suffix not in units:
        raise ValueError(f"Unsupported forward interval: {interval}")
    amount = int(value[:-1])
    return timedelta(**{units[suffix]: amount})


def bar_is_complete(timestamp, interval: str, now: datetime | None = None) -> bool:
    if hasattr(timestamp, "to_pydatetime"):
        timestamp = timestamp.to_pydatetime()
    if not isinstance(timestamp, datetime):
        raise TypeError("Forward bar timestamp must be datetime-like")
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timestamp.tzinfo)
    return timestamp + interval_delta(interval) <= current


def main():
    enabled = os.getenv("RCS_FORWARD_ENABLED", "0") == "1"
    if not enabled:
        raise RuntimeError(
            "Forward paper trading is disabled. Set RCS_FORWARD_ENABLED=1 to process new market bars."
        )

    settings = Settings()
    state_path = os.getenv("RCS_FORWARD_STATE", "state/forward_state.json")
    lookback_period = os.getenv("RCS_FORWARD_PERIOD", "10d")
    interval = os.getenv("RCS_FORWARD_INTERVAL", "15m")

    data = YahooFinanceData(settings.symbol, lookback_period, interval)
    all_bars = list(data.bars())
    completed = [bar for bar in all_bars if bar_is_complete(bar.timestamp, interval)]
    if len(completed) < settings.slow_window + 2:
        raise RuntimeError("Not enough completed bars returned to warm the strategy")

    engine = ForwardPaperEngine(settings, JsonStateStore(state_path))

    if engine.state.last_bar_time is None:
        first_new_index = len(completed) - 1
    else:
        matching = [i for i, bar in enumerate(completed) if str(bar.timestamp) == engine.state.last_bar_time]
        if not matching:
            raise RuntimeError(
                "Last processed bar is no longer inside the forward lookback window; "
                "increase RCS_FORWARD_PERIOD before resuming."
            )
        first_new_index = matching[-1] + 1

    if first_new_index >= len(completed):
        latest = completed[-1]
        snapshot = {
            "symbol": settings.symbol,
            "bar_time": str(latest.timestamp),
            "close": latest.close,
            "bars_processed_this_run": 0,
            "result": {"action": "SKIP", "reason": "no_new_completed_bar"},
            "cash": engine.state.cash,
            "realized_pnl": engine.state.realized_pnl,
            "closed_trades": engine.state.closed_trades,
            "position": None if engine.state.position is None else {
                "quantity": engine.state.position.quantity,
                "entry_price": engine.state.position.entry_price,
                "entry_time": engine.state.position.entry_time,
            },
            "halted": engine.state.halted,
        }
    else:
        warm_start = max(0, first_new_index - (settings.slow_window + 2))
        engine.warm_strategy([bar.close for bar in completed[warm_start:first_new_index]])

        results = []
        for bar in completed[first_new_index:]:
            results.append(engine.process_bar(bar))

        latest = completed[-1]
        snapshot = {
            "symbol": settings.symbol,
            "bar_time": str(latest.timestamp),
            "close": latest.close,
            "bars_processed_this_run": len(results),
            "results": results,
            "result": results[-1],
            "cash": engine.state.cash,
            "realized_pnl": engine.state.realized_pnl,
            "closed_trades": engine.state.closed_trades,
            "position": None if engine.state.position is None else {
                "quantity": engine.state.position.quantity,
                "entry_price": engine.state.position.entry_price,
                "entry_time": engine.state.position.entry_time,
            },
            "halted": engine.state.halted,
        }

    Path("reports").mkdir(exist_ok=True)
    Path("reports/forward_latest.json").write_text(
        json.dumps(snapshot, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(snapshot, indent=2, default=str))


if __name__ == "__main__":
    main()
