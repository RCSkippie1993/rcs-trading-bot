import math
import unittest

from bot.readiness import ReadinessThresholds, evaluate_portfolio, evaluate_symbol, profit_factor


class ReadinessTests(unittest.TestCase):
    def test_profit_factor(self):
        self.assertAlmostEqual(profit_factor(120.0, 100.0), 1.2)
        self.assertTrue(math.isinf(profit_factor(10.0, 0.0)))
        self.assertEqual(profit_factor(0.0, 0.0), 0.0)

    def test_insufficient_data(self):
        result = evaluate_symbol({
            "starting_cash": 10000,
            "cash": 10100,
            "closed_trades": 10,
            "wins": 6,
            "gross_profit": 160,
            "gross_loss": 60,
            "max_drawdown_pct": 2,
        })
        self.assertEqual(result["status"], "INSUFFICIENT DATA")

    def test_ready_for_manual_review(self):
        result = evaluate_symbol({
            "starting_cash": 10000,
            "cash": 10400,
            "closed_trades": 40,
            "wins": 24,
            "gross_profit": 900,
            "gross_loss": 500,
            "max_drawdown_pct": 6,
            "halted": False,
        })
        self.assertEqual(result["status"], "READY FOR MANUAL REVIEW")
        self.assertTrue(all(result["gates"].values()))

    def test_not_ready_when_drawdown_fails(self):
        result = evaluate_symbol({
            "starting_cash": 10000,
            "cash": 10500,
            "closed_trades": 40,
            "wins": 25,
            "gross_profit": 900,
            "gross_loss": 500,
            "max_drawdown_pct": 12,
            "halted": False,
        })
        self.assertEqual(result["status"], "NOT READY")
        self.assertFalse(result["gates"]["drawdown"])

    def test_portfolio_requires_breadth(self):
        rows = [
            {"status": "READY FOR MANUAL REVIEW", "total_return_pct": 3.0},
            {"status": "READY FOR MANUAL REVIEW", "total_return_pct": 2.0},
            {"status": "NOT READY", "total_return_pct": -1.0},
        ]
        result = evaluate_portfolio(rows, ReadinessThresholds(min_positive_symbol_pct=60.0))
        self.assertEqual(result["status"], "READY FOR MANUAL REVIEW")


if __name__ == "__main__":
    unittest.main()
