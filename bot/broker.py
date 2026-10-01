from dataclasses import dataclass

@dataclass
class Position:
    quantity: int
    entry_price: float

class PaperBroker:
    def __init__(self, starting_cash: float):
        self.cash = float(starting_cash)
        self.position = None
        self.realized_pnl = 0.0

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

        cost = price * quantity
        if cost > self.cash:
            return False

        self.cash -= cost
        self.position = Position(quantity=quantity, entry_price=price)
        return True

    def sell_all(self, price: float):
        if not self.position:
            return None

        proceeds = price * self.position.quantity
        cost_basis = self.position.entry_price * self.position.quantity
        pnl = proceeds - cost_basis
        qty = self.position.quantity

        self.cash += proceeds
        self.realized_pnl += pnl
        self.position = None

        return {"quantity": qty, "price": price, "pnl": pnl}
