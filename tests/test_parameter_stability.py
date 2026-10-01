import unittest

from parameter_stability import FAST_WINDOWS, SLOW_WINDOWS, parameter_grid


class ParameterStabilityTests(unittest.TestCase):
    def test_grid_contains_only_valid_pairs(self):
        grid = parameter_grid()
        self.assertTrue(grid)
        self.assertTrue(all(fast < slow for fast, slow in grid))

    def test_grid_is_unique(self):
        grid = parameter_grid()
        self.assertEqual(len(grid), len(set(grid)))

    def test_grid_covers_each_configured_fast_window(self):
        grid = parameter_grid()
        covered = {fast for fast, _ in grid}
        self.assertEqual(covered, set(FAST_WINDOWS))

    def test_grid_uses_configured_slow_windows(self):
        grid = parameter_grid()
        self.assertTrue(all(slow in SLOW_WINDOWS for _, slow in grid))


if __name__ == "__main__":
    unittest.main()
