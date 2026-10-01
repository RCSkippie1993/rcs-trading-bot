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


if __name__ == "__main__":
    unittest.main()
