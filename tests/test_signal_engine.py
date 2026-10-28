import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "signal-hub"))

import scan  # noqa: E402
import whale_pro  # noqa: E402


class SignalEngineTests(unittest.TestCase):
    def test_normalize_candles_sorts_deduplicates_and_drops_forming_bar(self):
        rows = [
            [1_800_000, 11, 12, 10, 11.5, 100],
            [0, 10, 11, 9, 10.5, 90],
            [1_800_000, 11, 12.2, 10, 11.7, 110],
            [900_000, 10.5, 11.5, 10, 11, 95],
        ]
        with patch.object(scan, "NOW", return_value=2_000):
            out = scan.normalize_candles(rows, "15m")
        self.assertEqual([row[0] for row in out], [0, 900_000])
        self.assertEqual(out[-1][4], 11.0)

    def test_normalize_candles_rejects_impossible_ohlc(self):
        rows = [[0, 10, 9, 8, 10, 100], [900_000, 10, 11, 9, 10, 100]]
        with patch.object(scan, "NOW", return_value=10_000):
            out = scan.normalize_candles(rows, "15m")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0][0], 900_000)

    def test_whale_strategy_handles_warmup_without_crashing(self):
        candles = []
        price = 100.0
        for i in range(320):
            price += 0.03 if i % 3 else -0.02
            candles.append([i * 900_000, price - 0.1, price + 0.2, price - 0.2, price, 1_000.0])
        result = whale_pro.run(candles, {"enable": True})
        self.assertIn("trades", result)
        self.assertIn("stats", result)
        self.assertIsInstance(result["trades"], list)


if __name__ == "__main__":
    unittest.main()
