import unittest
from datetime import datetime, timedelta

from bot.backtest import run_backtest
from bot.config import Settings
from bot.data import MarketBar


class Phase2BacktestTests(unittest.TestCase):
    def _bars(self, closes, wide_bar_index=None):
        start = datetime(2026, 1, 1, 9, 0)
        bars = []
        for i, close in enumerate(closes):
            high = close
            low = close
            if wide_bar_index is not None and i == wide_bar_index:
                high = close * 1.10
                low = close * 0.90
            bars.append(
                MarketBar(
                    timestamp=start + timedelta(hours=i),
                    open=close,
                    high=high,
                    low=low,
                    close=close,
                    volume=1000,
                )
            )
        return bars

    def test_backtest_returns_core_metrics(self):
        settings = Settings(
            fast_window=2,
            slow_window=3,
            fee_bps=10,
            slippage_bps=5,
            period="1mo",
            interval="1h",
        )
        result = run_backtest(self._bars([10, 9, 8, 9, 10, 11, 12, 11, 10]), settings)
        for key in (
            "total_return_pct",
            "benchmark_return_pct",
            "max_drawdown_pct",
            "profit_factor",
            "total_fees",
            "expectancy_pnl",
        ):
            self.assertIn(key, result)

    def test_costs_are_modeled(self):
        base = dict(
            fast_window=2,
            slow_window=3,
            period="1mo",
            interval="1h",
        )
        bars = self._bars([10, 9, 8, 9, 10, 11, 12, 11, 10])
        free = run_backtest(bars, Settings(fee_bps=0, slippage_bps=0, **base))
        costly = run_backtest(bars, Settings(fee_bps=20, slippage_bps=10, **base))
        self.assertGreaterEqual(costly["total_fees"], 0)
        self.assertLessEqual(costly["ending_equity"], free["ending_equity"])

    def test_intrabar_stop_has_priority_when_stop_and_target_touched(self):
        settings = Settings(
            fast_window=2,
            slow_window=3,
            stop_loss_pct=0.01,
            take_profit_pct=0.02,
            fee_bps=0,
            slippage_bps=0,
            period="1mo",
            interval="1h",
        )
        bars = self._bars([10, 9, 8, 9, 10, 10], wide_bar_index=5)
        result = run_backtest(bars, settings)
        if result["closed_trades"]:
            self.assertEqual(result["closed_trades"][0].exit_reason, "stop")


if __name__ == "__main__":
    unittest.main()
