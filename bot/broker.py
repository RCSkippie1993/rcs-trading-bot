from dataclasses import dataclass


@dataclass
class Position:
    quantity: int
    entry_price: float
    entry_fee: float


class PaperBroker:
    def __init__(self, starting_cash: float, fee_bps: float = 0.0, slippage_bps: float = 0.0):
        self.cash = float(starting_cash)
        self.position = None
        self.realized_pnl = 0.0
        self.fee_rate = float(fee_bps) / 10_000.0
        self.slippage_rate = float(slippage_bps) / 10_000.0
        self.total_fees = 0.0

    def equity(self, current_price: float) -> float:
        position_value = 0.0
        if self.position:
            position_value = self.position.quantity * current_price
        return self.cash + position_value

    def buy(self, price: float, quantity: int):
        if self.position is not None:
            raise RuntimeError("Only one open position is supported in v1")
        if quantity <= 0:
            return False

        fill_price = float(price) * (1.0 + self.slippage_rate)
        gross = fill_price * quantity
        fee = gross * self.fee_rate
        total_cost = gross + fee
        if total_cost > self.cash:
            return False

        self.cash -= total_cost
        self.total_fees += fee
        self.position = Position(quantity=quantity, entry_price=fill_price, entry_fee=fee)
        return {"quantity": quantity, "price": fill_price, "fee": fee}

    def sell_all(self, price: float):
        if not self.position:
            return None

        fill_price = float(price) * (1.0 - self.slippage_rate)
        gross_proceeds = fill_price * self.position.quantity
        exit_fee = gross_proceeds * self.fee_rate
        net_proceeds = gross_proceeds - exit_fee
        cost_basis = self.position.entry_price * self.position.quantity + self.position.entry_fee
        pnl = net_proceeds - cost_basis
        qty = self.position.quantity

        self.cash += net_proceeds
        self.total_fees += exit_fee
        self.realized_pnl += pnl
        self.position = None

        return {
            "quantity": qty,
            "price": fill_price,
            "pnl": pnl,
            "fee": exit_fee,
        }
