import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    starting_cash: float = 10_000.0
    risk_per_trade_pct: float = 0.005
    max_daily_loss_pct: float = 0.02
    max_position_pct: float = 0.10
    max_trades_per_session: int = 3
    stop_loss_pct: float = 0.01
    take_profit_pct: float = 0.02
    fast_window: int = 5
    slow_window: int = 12

    # Real market-data defaults. Yahoo quotes JSE (.JO) equities in ZAc;
    # the data adapter normalizes those prices to ZAR for this paper account.
    symbol: str = os.getenv("RCS_SYMBOL", "SOL.JO")
    period: str = os.getenv("RCS_PERIOD", "1mo")
    interval: str = os.getenv("RCS_INTERVAL", "1h")
