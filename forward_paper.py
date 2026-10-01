import json
import os
from pathlib import Path

from bot.config import Settings
from bot.data import YahooFinanceData
from bot.forward import ForwardPaperEngine, JsonStateStore


def main():
    enabled = os.getenv("RCS_FORWARD_ENABLED", "0") == "1"
    if not enabled:
        raise RuntimeError(
            "Forward paper trading is disabled. Set RCS_FORWARD_ENABLED=1 to process new market bars."
        )

    settings = Settings()
    state_path = os.getenv("RCS_FORWARD_STATE", "state/forward_state.json")
    lookback_period = os.getenv("RCS_FORWARD_PERIOD", "5d")
    interval = os.getenv("RCS_FORWARD_INTERVAL", "15m")

    data = YahooFinanceData(settings.symbol, lookback_period, interval)
    bars = list(data.bars())
    if len(bars) < settings.slow_window + 1:
        raise RuntimeError("Not enough bars returned to warm the strategy")

    engine = ForwardPaperEngine(settings, JsonStateStore(state_path))

    # Rebuild indicator state from historical bars before the newest completed bar.
    warm = bars[-(settings.slow_window + 2):-1]
    engine.warm_strategy([bar.close for bar in warm])

    latest = bars[-1]
    result = engine.process_bar(latest)
    snapshot = {
        "symbol": settings.symbol,
        "bar_time": str(latest.timestamp),
        "close": latest.close,
        "result": result,
        "cash": engine.state.cash,
        "realized_pnl": engine.state.realized_pnl,
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
