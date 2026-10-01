class RiskManager:
    def __init__(self, settings):
        self.settings = settings
        self.session_start_equity = settings.starting_cash
        self.trades = 0

    def reset_session(self, equity: float):
        self.session_start_equity = float(equity)
        self.trades = 0

    def daily_loss_limit_hit(self, equity: float) -> bool:
        floor = self.session_start_equity * (1 - self.settings.max_daily_loss_pct)
        return equity <= floor

    def can_open_trade(self, equity: float) -> bool:
        return (
            not self.daily_loss_limit_hit(equity)
            and self.trades < self.settings.max_trades_per_session
        )

    def position_size(self, equity: float, price: float) -> int:
        if price <= 0:
            return 0

        risk_budget = equity * self.settings.risk_per_trade_pct
        loss_per_share = price * self.settings.stop_loss_pct
        by_risk = int(risk_budget // loss_per_share) if loss_per_share else 0

        allocation_cap = equity * self.settings.max_position_pct
        by_allocation = int(allocation_cap // price)

        return max(0, min(by_risk, by_allocation))

    def record_trade(self):
        self.trades += 1
