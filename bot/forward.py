import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from bot.config import Settings
from bot.risk import RiskManager
from bot.strategy import MovingAverageCrossStrategy


@dataclass
class ForwardPosition:
    quantity: int
    entry_price: float
    entry_time: str


@dataclass
class ForwardState:
    cash: float
    realized_pnl: float = 0.0
    position: Optional[ForwardPosition] = None
    last_bar_time: Optional[str] = None
    session_key: Optional[str] = None
    session_start_equity: Optional[float] = None
    trades_this_session: int = 0
    halted: bool = False

    @classmethod
    def fresh(cls, starting_cash: float):
        return cls(cash=float(starting_cash), session_start_equity=float(starting_cash))


class JsonStateStore:
    def __init__(self, path: str):
        self.path = Path(path)

    def load(self, starting_cash: float) -> ForwardState:
        if not self.path.exists():
            return ForwardState.fresh(starting_cash)
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        pos = raw.get("position")
        if pos:
            raw["position"] = ForwardPosition(**pos)
        return ForwardState(**raw)

    def save(self, state: ForwardState):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(asdict(state), indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)


class ForwardPaperEngine:
    """One-symbol forward paper-trading engine.

    The engine processes only completed bars supplied by a data adapter. It never
    sends orders to a broker. State is persisted after every processed bar.
    """

    def __init__(self, settings: Settings, state_store: JsonStateStore):
        self.settings = settings
        self.store = state_store
        self.state = state_store.load(settings.starting_cash)
        self.strategy = MovingAverageCrossStrategy(settings.fast_window, settings.slow_window)
        self.risk = RiskManager(settings)

    @staticmethod
    def _session_key(timestamp) -> str:
        if hasattr(timestamp, "date"):
            return str(timestamp.date())
        return str(timestamp)[:10]

    def equity(self, mark_price: float) -> float:
        position_value = 0.0
        if self.state.position:
            position_value = self.state.position.quantity * mark_price
        return self.state.cash + position_value

    def warm_strategy(self, closes):
        self.strategy = MovingAverageCrossStrategy(self.settings.fast_window, self.settings.slow_window)
        for close in closes:
            self.strategy.on_price(float(close))

    def _apply_buy(self, price: float, qty: int, timestamp) -> dict:
        slip = self.settings.slippage_bps / 10_000.0
        fee_rate = self.settings.fee_bps / 10_000.0
        fill = price * (1.0 + slip)
        gross = fill * qty
        fee = gross * fee_rate
        total = gross + fee
        if qty <= 0 or total > self.state.cash:
            return {"action": "HOLD", "reason": "insufficient_cash_or_zero_qty"}
        self.state.cash -= total
        self.state.position = ForwardPosition(qty, fill, str(timestamp))
        self.state.trades_this_session += 1
        return {"action": "BUY", "quantity": qty, "fill_price": fill, "fee": fee}

    def _apply_sell(self, price: float, timestamp, reason: str) -> dict:
        if not self.state.position:
            return {"action": "HOLD", "reason": "no_position"}
        slip = self.settings.slippage_bps / 10_000.0
        fee_rate = self.settings.fee_bps / 10_000.0
        fill = price * (1.0 - slip)
        qty = self.state.position.quantity
        gross = fill * qty
        fee = gross * fee_rate
        proceeds = gross - fee
        cost_basis = self.state.position.entry_price * qty
        pnl = proceeds - cost_basis
        self.state.cash += proceeds
        self.state.realized_pnl += pnl
        self.state.position = None
        return {
            "action": "SELL",
            "quantity": qty,
            "fill_price": fill,
            "fee": fee,
            "pnl": pnl,
            "reason": reason,
            "time": str(timestamp),
        }

    def process_bar(self, bar) -> dict:
        bar_time = str(bar.timestamp)
        if self.state.last_bar_time == bar_time:
            return {"action": "SKIP", "reason": "duplicate_bar", "bar_time": bar_time}

        price = float(bar.close)
        session = self._session_key(bar.timestamp)
        current_equity = self.equity(price)

        if self.state.session_key != session:
            self.state.session_key = session
            self.state.session_start_equity = current_equity
            self.state.trades_this_session = 0

        self.risk.session_start_equity = float(self.state.session_start_equity or current_equity)
        self.risk.trades = self.state.trades_this_session

        if self.state.halted or os.getenv("RCS_KILL_SWITCH", "0") == "1":
            self.state.halted = True
            self.state.last_bar_time = bar_time
            self.store.save(self.state)
            return {"action": "HALT", "reason": "kill_switch", "bar_time": bar_time}

        if self.risk.daily_loss_limit_hit(current_equity):
            self.state.halted = True
            self.state.last_bar_time = bar_time
            self.store.save(self.state)
            return {"action": "HALT", "reason": "daily_loss_limit", "bar_time": bar_time}

        signal = self.strategy.on_price(price)
        result = {"action": "HOLD", "signal": signal, "bar_time": bar_time, "price": price}

        if self.state.position:
            entry = self.state.position.entry_price
            stop = entry * (1.0 - self.settings.stop_loss_pct)
            target = entry * (1.0 + self.settings.take_profit_pct)
            if float(bar.low) <= stop:
                result = self._apply_sell(stop, bar.timestamp, "stop")
            elif float(bar.high) >= target:
                result = self._apply_sell(target, bar.timestamp, "target")
            elif signal == "SELL":
                result = self._apply_sell(price, bar.timestamp, "signal")
        elif signal == "BUY" and self.risk.can_open_trade(current_equity):
            qty = self.risk.position_size(current_equity, price)
            result = self._apply_buy(price, qty, bar.timestamp)

        self.state.last_bar_time = bar_time
        self.store.save(self.state)
        return result
