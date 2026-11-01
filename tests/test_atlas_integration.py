import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "signal-hub"))

from atlas_adapter import run_from_cache  # noqa: E402
from atlas_quant.backtest import run_backtest  # noqa: E402
from atlas_quant.day_trader_skill import build_indicators  # noqa: E402


class AtlasIntegrationTests(unittest.TestCase):
    @staticmethod
    def candles(count=260):
        rows = []
        price = 100.0
        for i in range(count):
            price += 0.35 if i % 8 < 5 else -0.15
            rows.append([i * 900_000, price - 0.2, price + 0.5, price - 0.5, price, 1000.0])
        return rows

    def test_backtest_never_enables_real_orders(self):
        rows = self.candles()
        result = run_backtest([
            {"time": row[0] / 1000, "open": row[1], "high": row[2], "low": row[3], "close": row[4], "volume": row[5]}
            for row in rows
        ])
        self.assertFalse(result["real_orders_enabled"])
        self.assertIn("equity_curve", result)

    def test_day_trader_skill_builds_all_required_indicators(self):
        candles = [
            {"time": row[0] / 1000, "open": row[1], "high": row[2], "low": row[3], "close": row[4], "volume": row[5]}
            for row in self.candles()
        ]
        indicators = build_indicators(candles)
        self.assertEqual(set(indicators), {"ema_fast", "ema_slow", "adx", "rsi", "chop", "atr"})
        self.assertIsNotNone(indicators["ema_slow"][-1])
        self.assertIsNotNone(indicators["adx"][-1])
        self.assertIsNotNone(indicators["chop"][-1])

    def test_adapter_reads_cache_and_writes_compact_report(self):
        rows = self.candles()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "atlas.json"
            result = run_from_cache(
                {("BTCUSDT", "15m"): rows},
                {"atlas": {"symbols": ["BTCUSDT"], "timeframe": "15m"}},
                path,
            )
            self.assertEqual(result["summary"]["tested"], 1)
            self.assertTrue(result["paper_only"])
            self.assertFalse(result["real_orders_enabled"])
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["symbols"]["BTCUSDT"]["status"], "ok")

    def test_adapter_marks_short_cache_as_insufficient(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_from_cache(
                {("BTCUSDT", "15m"): self.candles(40)},
                {"atlas": {"symbols": ["BTCUSDT"]}},
                Path(tmp) / "atlas.json",
            )
            self.assertEqual(result["symbols"]["BTCUSDT"]["status"], "insufficient_data")
            self.assertEqual(result["summary"]["tested"], 0)


if __name__ == "__main__":
    unittest.main()
