"""Local Flask API for the Atlas Quant paper-only dashboard.

This API serves generated reports and can backtest caller-supplied candles. It
never accepts exchange credentials and never places orders.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request

from atlas_quant.backtest import BacktestError, run_backtest

ROOT = Path(__file__).resolve().parent.parent
ENGINE_ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "atlas.json"
CONFIG_PATH = ENGINE_ROOT / "config.json"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def create_app() -> Flask:
    app = Flask(__name__)

    @app.after_request
    def add_local_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "paper_only": True, "service": "atlas-quant"})

    @app.get("/api/atlas/report")
    def report():
        return jsonify(_read_json(REPORT_PATH))

    @app.get("/api/atlas/config")
    def config():
        data = _read_json(CONFIG_PATH)
        atlas = data.get("atlas", {})
        # Never return unrelated config or credentials if they are added later.
        safe_keys = {
            "enabled", "timeframe", "limit", "initial_capital", "risk_pct", "fee_pct",
            "ema_fast", "ema_slow", "adx_period", "adx_min", "rsi_period", "long_rsi_min",
            "long_rsi_max", "short_rsi_min", "short_rsi_max", "chop_period", "chop_max",
            "atr_period", "atr_multiplier", "reward_r", "breakeven_trigger", "allow_short", "symbols",
        }
        return jsonify({key: value for key, value in atlas.items() if key in safe_keys})

    @app.post("/api/atlas/backtest")
    def backtest():
        body = request.get_json(silent=True) or {}
        candles = body.get("candles")
        if not isinstance(candles, list) or not 100 <= len(candles) <= 5000:
            return jsonify({"ok": False, "error": "candles باید یک آرایهٔ ۱۰۰ تا ۵۰۰۰تایی باشد."}), 400
        params = body.get("params") if isinstance(body.get("params"), dict) else {}
        try:
            result = run_backtest(candles, **params)
        except (BacktestError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, "paper_only": True, "real_orders_enabled": False, "result": result})

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atlas Quant paper-only local API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5000, type=int)
    args = parser.parse_args()
    create_app().run(host=args.host, port=args.port, debug=False)
