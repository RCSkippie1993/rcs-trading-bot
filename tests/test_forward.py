import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from bot.config import Settings
from bot.data import MarketBar
from bot.forward import ForwardPaperEngine, JsonStateStore


class ForwardPaperTests(unittest.TestCase):
    def make_engine(self, **overrides):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        settings = replace(Settings(), **overrides)
        store = JsonStateStore(str(Path(temp.name) / "state.json"))
        return ForwardPaperEngine(settings, store)

    def test_duplicate_bar_is_ignored(self):
        engine = self.make_engine()
        engine.warm_strategy([100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 90, 89])
        bar = MarketBar("2026-01-01T10:00:00", 90, 91, 89, 90, 1000)
        first = engine.process_bar(bar)
        second = engine.process_bar(bar)
        self.assertNotEqual(first["action"], "SKIP")
        self.assertEqual(second["action"], "SKIP")

    def test_kill_switch_state_halts_engine(self):
        engine = self.make_engine()
        engine.state.halted = True
        bar = MarketBar("2026-01-01T10:00:00", 100, 101, 99, 100, 1000)
        result = engine.process_bar(bar)
        self.assertEqual(result["action"], "HALT")

    def test_state_persists(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = str(Path(temp.name) / "state.json")
        store = JsonStateStore(path)
        state = store.load(10_000)
        state.cash = 9_500
        store.save(state)
        loaded = store.load(10_000)
        self.assertEqual(loaded.cash, 9_500)

    def test_pending_buy_executes_at_next_bar_open(self):
        engine = self.make_engine()
        engine.state.pending_signal = "BUY"
        bar = MarketBar("2026-01-01T10:15:00", 100, 101.5, 99.5, 101, 1000)
        result = engine.process_bar(bar)
        self.assertEqual(result["action"], "BUY")
        self.assertIsNotNone(engine.state.position)
        self.assertAlmostEqual(engine.state.position.entry_price, 100 * 1.0005, places=6)

    def test_realized_pnl_includes_both_entry_and_exit_fees(self):
        engine = self.make_engine()
        engine.state.pending_signal = "BUY"
        first = MarketBar("2026-01-01T10:15:00", 100, 101, 99.5, 100, 1000)
        engine.process_bar(first)
        position = engine.state.position
        self.assertIsNotNone(position)

        engine.state.pending_signal = "SELL"
        second = MarketBar("2026-01-01T10:30:00", 101, 101.5, 100.5, 101, 1000)
        result = engine.process_bar(second)
        self.assertEqual(result["action"], "SELL")

        sell_fill = 101 * 0.9995
        exit_fee = sell_fill * position.quantity * 0.001
        expected = (
            sell_fill * position.quantity
            - exit_fee
            - position.entry_price * position.quantity
            - position.entry_fee
        )
        self.assertAlmostEqual(engine.state.realized_pnl, expected, places=6)


if __name__ == "__main__":
    unittest.main()
