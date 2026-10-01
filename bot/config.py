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

    # Phase 2 backtest realism. Values are basis points per side.
    fee_bps: float = float(os.getenv("RCS_FEE_BPS", "10"))
    slippage_bps: float = float(os.getenv("RCS_SLIPPAGE_BPS", "5"))

    # Real market-data defaults. Yahoo quotes JSE (.JO) equities in ZAc;
    # the data adapter normalizes those prices to ZAR for this paper account.
    symbol: str = os.getenv("RCS_SYMBOL", "SOL.JO")
    period: str = os.getenv("RCS_PERIOD", "6mo")
    interval: str = os.getenv("RCS_INTERVAL", "1h")
