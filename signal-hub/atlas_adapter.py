"""Signal Hub adapter for the user-supplied ATLAS QUANT v0.3 backtester.

This bridge intentionally uses only the existing incremental candle cache. It
never fetches market data, places exchange orders, opens a server, or mutates
the paper-account SQLite database. The output is a compact JSON report suitable
for the Persian dashboard and scheduled CI runs.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from atlas_quant.backtest import BacktestEngine, BacktestError

NOW = lambda: int(time.time())
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT")


def _to_candles(rows: Sequence[Sequence[float]]) -> list[dict[str, float]]:
    candles: list[dict[str, float]] = []
    for row in rows:
        if len(row) < 5:
            continue
        try:
            timestamp = float(row[0])
            if timestamp > 10_000_000_000:
                timestamp /= 1000
            o, h, low, close = map(float, row[1:5])
            volume = float(row[5]) if len(row) > 5 else 0.0
        except (TypeError, ValueError):
            continue
        candles.append({"time": timestamp, "open": o, "high": h, "low": low, "close": close, "volume": volume})
    return candles


def _compact_report(report: dict[str, Any], max_curve_points: int = 80, max_trades: int = 30) -> dict[str, Any]:
    curve = report.pop("equity_curve", [])
    trades = report.pop("trades", [])
    if curve:
        step = max(1, len(curve) // max_curve_points)
        sampled = curve[::step]
        if sampled[-1] != curve[-1]:
            sampled.append(curve[-1])
        report["equity_curve"] = sampled
    else:
        report["equity_curve"] = []
    report["trades_total"] = len(trades)
    report["trades"] = trades[-max_trades:]
    return report


def run_from_cache(
    cache: Mapping[tuple[str, str], Sequence[Sequence[float]]],
    config: Mapping[str, Any] | None = None,
    output_path: str | os.PathLike[str] = "atlas.json",
) -> dict[str, Any]:
    settings = dict((config or {}).get("atlas", {}))
    timeframe = str(settings.get("timeframe", "15m"))
    limit = int(settings.get("limit", 1000))
    symbols = tuple(settings.get("symbols") or DEFAULT_SYMBOLS)
    params = {
        "initial_capital": float(settings.get("initial_capital", 10_000)),
        "risk_pct": float(settings.get("risk_pct", 1)),
        "fee_pct": float(settings.get("fee_pct", 0.1)),
        "stop_atr": float(settings.get("atr_multiplier", settings.get("stop_atr", 2))),
        "reward_r": float(settings.get("reward_r", 2)),
        "allow_short": bool(settings.get("allow_short", False)),
        "ema_fast": int(settings.get("ema_fast", 55)),
        "ema_slow": int(settings.get("ema_slow", 200)),
        "adx_period": int(settings.get("adx_period", 14)),
        "adx_min": float(settings.get("adx_min", 20)),
        "rsi_period": int(settings.get("rsi_period", 14)),
        "long_rsi_min": float(settings.get("long_rsi_min", 50)),
        "long_rsi_max": float(settings.get("long_rsi_max", 70)),
        "short_rsi_min": float(settings.get("short_rsi_min", 30)),
        "short_rsi_max": float(settings.get("short_rsi_max", 50)),
        "chop_period": int(settings.get("chop_period", 14)),
        "chop_max": float(settings.get("chop_max", 61.8)),
        "atr_period": int(settings.get("atr_period", 14)),
        "atr_multiplier": float(settings.get("atr_multiplier", settings.get("stop_atr", 2))),
        "breakeven_trigger": float(settings.get("breakeven_trigger", 0.5)),
    }
    output: dict[str, Any] = {
        "updated": NOW(),
        "engine": "ATLAS QUANT v0.3",
        "mode": "HISTORICAL_BACKTEST",
        "paper_only": True,
        "real_orders_enabled": False,
        "data_source": "Signal Hub incremental candle cache",
        "timeframe": timeframe,
        "parameters": params,
        "symbols": {},
    }
    engine = BacktestEngine(**params)
    ok_reports: list[tuple[str, dict[str, Any]]] = []
    for symbol in symbols:
        rows = list(cache.get((symbol, timeframe), []))[-limit:]
        candles = _to_candles(rows)
        required = max(100, int(params["ema_slow"]) + 2)
        if len(candles) < required:
            output["symbols"][symbol] = {
                "status": "insufficient_data",
                "candles": len(candles),
                "required": required,
            }
            continue
        try:
            report = engine.run(candles)
            report.update({"status": "ok", "symbol": symbol, "timeframe": timeframe, "candles": len(candles)})
            report = _compact_report(report)
            output["symbols"][symbol] = report
            ok_reports.append((symbol, report))
        except (BacktestError, ValueError) as exc:
            output["symbols"][symbol] = {"status": "error", "candles": len(candles), "error": str(exc)}

    ranked = sorted(ok_reports, key=lambda item: float(item[1].get("return_pct", 0)), reverse=True)
    output["summary"] = {
        "tested": len(ok_reports),
        "available": len(symbols),
        "profitable": sum(float(r.get("return_pct", 0)) > 0 for _, r in ok_reports),
        "best_symbol": ranked[0][0] if ranked else None,
        "best_return_pct": ranked[0][1].get("return_pct") if ranked else None,
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="atlas-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(output, handle, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return output


if __name__ == "__main__":
    from scan import CFG, KLINE_CACHE

    result = run_from_cache(KLINE_CACHE, CFG)
    print(json.dumps({"event": "atlas_backtest", "status": "ok", "summary": result["summary"]}, ensure_ascii=False))
