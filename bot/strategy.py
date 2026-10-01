from collections import deque

class MovingAverageCrossStrategy:
    def __init__(self, fast_window: int, slow_window: int):
        if fast_window >= slow_window:
            raise ValueError("fast_window must be smaller than slow_window")
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.prices = deque(maxlen=slow_window)
        self.previous_state = None

    def on_price(self, price: float) -> str:
        self.prices.append(float(price))
        if len(self.prices) < self.slow_window:
            return "HOLD"

        values = list(self.prices)
        fast = sum(values[-self.fast_window:]) / self.fast_window
        slow = sum(values) / self.slow_window

        state = "ABOVE" if fast > slow else "BELOW"
        signal = "HOLD"
        if self.previous_state == "BELOW" and state == "ABOVE":
            signal = "BUY"
        elif self.previous_state == "ABOVE" and state == "BELOW":
            signal = "SELL"

        self.previous_state = state
        return signal
