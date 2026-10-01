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
    entry_fee: float = 0.0


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
    pending_signal: Optional[str] = None

    # Phase 3 performance ledger. Defaults make old state files compatible.
    starting_cash: float = 0.0
    bars_processed: int = 0
    closed_trades: int = 0
    wins: int = 0
    losses: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    total_fees: float = 0.0
    peak_equity: float = 0.0
    max_drawdown_pct: float = 0.0
    first_bar_time: Optional[str] = None

    @classmethod
    def fresh(cls, starting_cash: float):
        starting_cash = float(starting_cash)
        return cls(
            cash=starting_cash,
            session_start_equity=starting_cash,
            starting_cash=starting_cash,
            peak_equity=starting_cash,
        )


class JsonStateStore:
    def __init__(self, path: str):
        self.path = Path(path)

    def load(self, starting_cash: float) -> ForwardState:
        if not self.path.exists():
            return ForwardState.fresh(starting_cash)

        text = self.path.read_text(encoding="utf-8")
        if not text.strip():
            return ForwardState.fresh(starting_cash)

        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Paper state file is not valid JSON: {self.path}") from exc

        pos = raw.get("position")
        if pos:
            raw["position"] = ForwardPosition(**pos)
        state = ForwardState(**raw)
        if state.starting_cash <= 0:
            state.starting_cash = float(starting_cash)
        if state.peak_equity <= 0:
            state.peak_equity = max(state.starting_cash, state.cash)
        return state

    def save(self, state: ForwardState):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(asdict(state), indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)


class ForwardPaperEngine:
    """One-symbol forward paper-trading engine.

    Signals are generated only from completed bars. A close-of-bar signal is
    queued and executed at the next processed bar's open, avoiding same-close
    execution. The engine never sends orders to a broker.
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

    def _update_drawdown(self, mark_price: float):
        equity = self.equity(mark_price)
        self.state.peak_equity = max(self.state.peak_equity, equity)
        if self.state.peak_equity > 0:
            dd = (self.state.peak_equity - equity) / self.state.peak_equity * 100.0
            self.state.max_drawdown_pct = max(self.state.max_drawdown_pct, dd)

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
        self.state.total_fees += fee
        self.state.position = ForwardPosition(qty, fill, str(timestamp), fee)
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
        cost_basis = self.state.position.entry_price * qty + self.state.position.entry_fee
        pnl = proceeds - cost_basis
        self.state.cash += proceeds
        self.state.realized_pnl += pnl
        self.state.total_fees += fee
        self.state.closed_trades += 1
        if pnl > 0:
            self.state.wins += 1
            self.state.gross_profit += pnl
        elif pnl < 0:
            self.state.losses += 1
            self.state.gross_loss += abs(pnl)
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

        open_price = float(bar.open)
        close_price = float(bar.close)
        session = self._session_key(bar.timestamp)
        opening_equity = self.equity(open_price)

        if self.state.session_key != session:
            self.state.session_key = session
            self.state.session_start_equity = opening_equity
            self.state.trades_this_session = 0

        self.risk.session_start_equity = float(self.state.session_start_equity or opening_equity)
        self.risk.trades = self.state.trades_this_session

        if self.state.halted or os.getenv("RCS_KILL_SWITCH", "0") == "1":
            self.state.halted = True
            self.state.last_bar_time = bar_time
            self.store.save(self.state)
            return {"action": "HALT", "reason": "kill_switch", "bar_time": bar_time}

        if self.risk.daily_loss_limit_hit(opening_equity):
            self.state.halted = True
            self.state.last_bar_time = bar_time
            self.store.save(self.state)
            return {"action": "HALT", "reason": "daily_loss_limit", "bar_time": bar_time}

        event = {"action": "HOLD", "bar_time": bar_time, "price": close_price}

        # Execute the prior completed bar's signal at this bar's open.
        pending = self.state.pending_signal
        self.state.pending_signal = None
        if pending == "SELL" and self.state.position:
            event = self._apply_sell(open_price, bar.timestamp, "signal_next_open")
        elif pending == "BUY" and not self.state.position and self.risk.can_open_trade(opening_equity):
            qty = self.risk.position_size(opening_equity, open_price)
            event = self._apply_buy(open_price, qty, bar.timestamp)

        # Intrabar protection. If both stop and target are touched, stop wins.
        if self.state.position:
            entry = self.state.position.entry_price
            stop = entry * (1.0 - self.settings.stop_loss_pct)
            target = entry * (1.0 + self.settings.take_profit_pct)
            if float(bar.low) <= stop:
                # A gap below the stop is filled no better than the bar open.
                stop_fill = min(stop, open_price)
                event = self._apply_sell(stop_fill, bar.timestamp, "stop")
            elif float(bar.high) >= target:
                # Keep target fills conservative even if the bar gaps above target.
                event = self._apply_sell(target, bar.timestamp, "target")

        # Generate a new signal only from this completed bar's close.
        signal = self.strategy.on_price(close_price)
        if self.state.position and signal == "SELL":
            self.state.pending_signal = "SELL"
        elif not self.state.position and signal == "BUY":
            self.state.pending_signal = "BUY"

        event["signal"] = signal
        event["pending_signal"] = self.state.pending_signal
        self.state.last_bar_time = bar_time
        if self.state.first_bar_time is None:
            self.state.first_bar_time = bar_time
        self.state.bars_processed += 1
        self._update_drawdown(close_price)
        self.store.save(self.state)
        return event
