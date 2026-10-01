import unittest
from dataclasses import replace
from datetime import datetime, timedelta

from bot.config import Settings
from bot.data import MarketBar
from bot.walk_forward import make_folds, run_walk_forward


def synthetic_bars(count: int):
    bars = []
    start = datetime(2024, 1, 1)
    for i in range(count):
        # Alternating trend blocks create several crossover opportunities without randomness.
        block = (i // 20) % 2
        offset = i % 20
        price = 100.0 + (offset * 0.8 if block == 0 else (20 - offset) * 0.8)
        bars.append(
            MarketBar(
                timestamp=start + timedelta(days=i),
                open=price,
                high=price * 1.005,
                low=price * 0.995,
                close=price,
                volume=1000.0,
            )
        )
    return bars


class WalkForwardTests(unittest.TestCase):
    def test_make_folds_non_overlapping_test_windows(self):
        bars = synthetic_bars(100)
        folds = make_folds(bars, train_bars=40, test_bars=20, step_bars=20)
        self.assertEqual(len(folds), 3)
        self.assertEqual(len(folds[0][0]), 40)
        self.assertEqual(len(folds[0][1]), 20)
        self.assertEqual(folds[0][1][0].timestamp, bars[40].timestamp)
        self.assertEqual(folds[1][1][0].timestamp, bars[60].timestamp)

    def test_insufficient_history_rejected(self):
        settings = Settings()
        with self.assertRaises(RuntimeError):
            run_walk_forward(
                synthetic_bars(30),
                settings,
                candidates=[(3, 8)],
                train_bars=25,
                test_bars=10,
            )

    def test_walk_forward_locks_valid_training_selected_parameters(self):
        settings = replace(
            Settings(),
            fee_bps=0.0,
            slippage_bps=0.0,
            max_trades_per_session=10,
        )
        candidates = [(3, 8), (5, 12)]
        folds = run_walk_forward(
            synthetic_bars(120),
            settings,
            candidates=candidates,
            train_bars=60,
            test_bars=20,
            step_bars=20,
        )
        self.assertEqual(len(folds), 3)
        for fold in folds:
            self.assertIn((fold.fast_window, fold.slow_window), candidates)
            self.assertGreaterEqual(fold.test_trades, 0)
            self.assertLessEqual(fold.test_drawdown_pct, 100.0)


if __name__ == "__main__":
    unittest.main()
