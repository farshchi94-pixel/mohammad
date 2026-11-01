"""Paper-only historical backtest engine for the Atlas Quant DayTraderSkill."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .day_trader_skill import DEFAULTS, build_indicators, latest_snapshot, signal_at

BASE = "https://api.lbkex.com/v2/kline.do"
INTERVALS = {"1m": "minute1", "3m": "minute3", "5m": "minute5", "15m": "minute15", "30m": "minute30", "1h": "hour1", "4h": "hour4", "1d": "day1"}


class BacktestError(ValueError):
    pass


def fetch_candles(symbol: str, timeframe: str, limit: int = 500) -> list[dict[str, float]]:
    """Optional standalone data helper; the Signal Hub adapter uses its local cache."""
    if timeframe not in INTERVALS:
        raise BacktestError("تایم‌فریم پشتیبانی نمی‌شود.")
    if not 100 <= limit <= 2000:
        raise BacktestError("تعداد کندل باید بین ۱۰۰ تا ۲۰۰۰ باشد.")
    params = urllib.parse.urlencode({"symbol": symbol.lower().replace("/", "_"), "type": INTERVALS[timeframe], "size": limit})
    request = urllib.request.Request(BASE + "?" + params, headers={"User-Agent": "ATLAS-QUANT-PAPER-BACKTEST/2.0"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise BacktestError(f"دریافت داده تاریخی ناموفق بود: {type(exc).__name__}") from exc
    if not isinstance(payload, list):
        payload = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(payload, list):
        raise BacktestError("پاسخ API کندل معتبر نیست.")
    candles: list[dict[str, float]] = []
    for row in payload:
        try:
            if isinstance(row, dict):
                timestamp = row.get("timestamp", row.get("time", row.get("t")))
                values = [row[k] for k in ("open", "high", "low", "close", "volume")]
            else:
                timestamp, *values = row[:6]
            timestamp = float(timestamp)
            timestamp = timestamp / 1000 if timestamp > 10_000_000_000 else timestamp
            open_, high, low, close, volume = map(float, values)
            if min(open_, high, low, close) <= 0 or high < max(open_, close, low) or low > min(open_, close, high):
                continue
            candles.append({"time": timestamp, "open": open_, "high": high, "low": low, "close": close, "volume": volume})
        except (TypeError, ValueError, KeyError, IndexError):
            continue
    unique = {c["time"]: c for c in candles}
    candles = [unique[key] for key in sorted(unique)]
    if len(candles) < 100:
        raise BacktestError(f"داده معتبر کافی نیست: فقط {len(candles)} کندل دریافت شد.")
    return candles


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def _validate(candles: Sequence[Mapping[str, float]], initial_capital: float, risk_pct: float, fee_pct: float, params: Mapping[str, Any]) -> None:
    if not 100 <= initial_capital <= 10_000_000:
        raise BacktestError("سرمایه باید بین ۱۰۰ و ۱۰٬۰۰۰٬۰۰۰ USDT باشد.")
    if not 0.1 <= risk_pct <= 2:
        raise BacktestError("ریسک هر معامله باید بین ۰٫۱٪ و ۲٪ باشد.")
    if not 0 <= fee_pct <= 1:
        raise BacktestError("کارمزد باید بین ۰٪ و ۱٪ برای هر سمت باشد.")
    if len(candles) < max(int(params["ema_slow"]) + 2, 100):
        raise BacktestError("برای EMA200 و شاخص‌های DayTraderSkill دادهٔ کافی وجود ندارد.")
    if not 0.1 <= float(params["atr_multiplier"]) <= 5:
        raise BacktestError("ضریب ATR باید بین ۰٫۱ و ۵ باشد.")
    if not 1 <= float(params["reward_r"]) <= 5:
        raise BacktestError("نسبت ریسک به بازده باید بین ۱ و ۵ باشد.")
    if not 0 < float(params["breakeven_trigger"]) <= 1:
        raise BacktestError("آستانهٔ Breakeven باید بین صفر و یک باشد.")


def run_backtest(
    candles: Sequence[Mapping[str, float]],
    initial_capital: float = 10_000,
    risk_pct: float = 1,
    fee_pct: float = 0.1,
    stop_atr: float = 2,
    reward_r: float = 2,
    allow_short: bool = False,
    **strategy_overrides: Any,
) -> dict[str, Any]:
    """Run a candle-by-candle, next-open-fill, paper-only simulation.

    The strategy is DayTraderSkill: EMA55/EMA200 trend, ADX>20, RSI14 range,
    CHOP<=61.8, ATR14 stop, fixed R target and automatic breakeven at 50%.
    """
    params = {**DEFAULTS, **strategy_overrides}
    params["atr_multiplier"] = float(strategy_overrides.get("atr_multiplier", stop_atr))
    params["reward_r"] = float(strategy_overrides.get("reward_r", reward_r))
    params["allow_short"] = bool(strategy_overrides.get("allow_short", allow_short))
    _validate(candles, initial_capital, risk_pct, fee_pct, params)

    clean = [dict(c) for c in candles]
    indicators = build_indicators(clean, params)
    fee_rate = fee_pct / 100.0
    cash = float(initial_capital)
    position: dict[str, Any] | None = None
    trades: list[dict[str, Any]] = []
    curve: list[dict[str, float]] = []
    peak = cash
    max_drawdown = 0.0
    breakeven_moves = 0

    def equity(price: float) -> float:
        if not position:
            return cash
        return cash + position["side"] * position["qty"] * price

    def close_position(exit_price: float, candle: Mapping[str, float], reason: str) -> None:
        nonlocal cash, position
        if not position:
            return
        side = position["side"]
        qty = position["qty"]
        exit_fee = exit_price * qty * fee_rate
        gross = side * (exit_price - position["entry"]) * qty
        if side == 1:
            cash += qty * exit_price - exit_fee
        else:
            cash -= qty * exit_price + exit_fee
        net = gross - position["entry_fee"] - exit_fee
        trades.append({
            "side": "long" if side == 1 else "short",
            "entry_time": _iso(position["time"]),
            "exit_time": _iso(float(candle["time"])),
            "entry": round(position["entry"], 8),
            "exit": round(exit_price, 8),
            "qty": round(qty, 8),
            "gross_pnl": round(gross, 4),
            "fees": round(position["entry_fee"] + exit_fee, 4),
            "net_pnl": round(net, 4),
            "return_pct": round(net / (position["entry"] * qty) * 100, 4),
            "reason": reason,
            "breakeven": bool(position["breakeven"]),
        })
        position = None

    for i, candle in enumerate(clean):
        if position:
            side = position["side"]
            risk_unit = position["risk_unit"]
            favorable = candle["high"] >= position["entry"] + risk_unit * float(params["breakeven_trigger"]) if side == 1 else candle["low"] <= position["entry"] - risk_unit * float(params["breakeven_trigger"])
            if favorable and not position["breakeven"]:
                position["stop"] = position["entry"]
                position["breakeven"] = True
                breakeven_moves += 1
            exit_price = None
            reason = None
            if side == 1:
                if candle["open"] <= position["stop"]:
                    exit_price, reason = candle["open"], "stop_gap"
                elif candle["open"] >= position["target"]:
                    exit_price, reason = candle["open"], "target_gap"
                elif candle["low"] <= position["stop"]:
                    exit_price, reason = position["stop"], "breakeven" if position["breakeven"] and position["stop"] == position["entry"] else "stop"
                elif candle["high"] >= position["target"]:
                    exit_price, reason = position["target"], "target"
            else:
                if candle["open"] >= position["stop"]:
                    exit_price, reason = candle["open"], "stop_gap"
                elif candle["open"] <= position["target"]:
                    exit_price, reason = candle["open"], "target_gap"
                elif candle["high"] >= position["stop"]:
                    exit_price, reason = position["stop"], "breakeven" if position["breakeven"] and position["stop"] == position["entry"] else "stop"
                elif candle["low"] <= position["target"]:
                    exit_price, reason = position["target"], "target"
            if exit_price is not None:
                close_position(float(exit_price), candle, str(reason))

        if position is None and i + 1 < len(clean):
            side_name = signal_at(i, clean, indicators, params)
            if side_name:
                side = 1 if side_name == "long" else -1
                entry = float(clean[i + 1]["open"])
                atr_value = indicators["atr"][i]
                if atr_value is not None and float(atr_value) > 0:
                    risk_unit = float(atr_value) * float(params["atr_multiplier"])
                    stop = entry - side * risk_unit
                    target = entry + side * risk_unit * float(params["reward_r"])
                    risk_cash = max(0.0, equity(float(candle["close"]))) * risk_pct / 100.0
                    qty = risk_cash / risk_unit if risk_unit else 0.0
                    if side == 1:
                        qty = min(qty, max(0.0, cash / (entry * (1 + fee_rate))))
                    else:
                        qty = min(qty, max(0.0, cash / entry))
                    if qty > 0:
                        entry_fee = entry * qty * fee_rate
                        cash += (-qty * entry - entry_fee) if side == 1 else (qty * entry - entry_fee)
                        position = {"side": side, "entry": entry, "qty": qty, "stop": stop, "target": target, "risk_unit": risk_unit, "entry_fee": entry_fee, "time": float(clean[i + 1]["time"]), "breakeven": False}

        marked = equity(float(candle["close"]))
        peak = max(peak, marked)
        drawdown = (peak - marked) / peak * 100 if peak else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        curve.append({"time": float(candle["time"]), "equity": round(marked, 4), "drawdown_pct": round(drawdown, 4)})

    if position:
        close_position(float(clean[-1]["close"]), clean[-1], "end_of_test")
        if curve:
            curve[-1]["equity"] = round(cash, 4)

    final_equity = cash
    net_pnl = final_equity - initial_capital
    wins = sum(t["net_pnl"] > 0 for t in trades)
    losses = len(trades) - wins
    gross_profit = sum(max(t["net_pnl"], 0) for t in trades)
    gross_loss = abs(sum(min(t["net_pnl"], 0) for t in trades))
    return {
        "mode": "PAPER_ONLY",
        "real_orders_enabled": False,
        "strategy": "DayTraderSkill: EMA55/EMA200 + ADX>20 + RSI14 + CHOP<=61.8 + ATR14 + Breakeven",
        "symbol": "",
        "timeframe": "",
        "candles": len(clean),
        "initial_capital": round(initial_capital, 2),
        "final_equity": round(final_equity, 2),
        "net_pnl": round(net_pnl, 2),
        "return_pct": round(net_pnl / initial_capital * 100, 3),
        "max_drawdown_pct": round(max_drawdown, 3),
        "trades_count": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(wins / len(trades) * 100, 2) if trades else 0,
        "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss else (None if not gross_profit else "infinite"),
        "fees_total": round(sum(t["fees"] for t in trades), 4),
        "risk_pct": risk_pct,
        "fee_pct_per_side": fee_pct,
        "indicator_config": {k: params[k] for k in ("ema_fast", "ema_slow", "adx_period", "adx_min", "rsi_period", "long_rsi_min", "long_rsi_max", "short_rsi_min", "short_rsi_max", "chop_period", "chop_max", "atr_period", "atr_multiplier", "reward_r", "breakeven_trigger", "allow_short")},
        "latest_indicators": latest_snapshot(indicators),
        "breakeven_moves": breakeven_moves,
        "trades": trades,
        "equity_curve": curve,
        "assumptions": [
            "DayTraderSkill: trend EMA55/EMA200، قدرت روند ADX14>20، RSI14 و CHOP14<=61.8.",
            "سیگنال در بسته‌شدن کندل و ورود در بازشدن کندل بعدی انجام می‌شود.",
            "حد ضرر با ATR14 و هدف با نسبت R محاسبه می‌شود؛ در ۵۰٪ مسیر هدف، حد ضرر به نقطه ورود منتقل می‌شود.",
            "در لمس هم‌زمان حد ضرر و هدف، حد ضرر مقدم است؛ کارمزد ورود و خروج لحاظ شده و لغزش شبیه‌سازی نشده است.",
            "این گزارش تاریخی و PAPER ONLY است و توصیهٔ مالی یا سفارش واقعی نیست.",
        ],
    }


class BacktestEngine:
    """Named façade matching the main Atlas Quant architecture."""

    def __init__(self, **params: Any):
        self.params = dict(params)

    def run(self, candles: Sequence[Mapping[str, float]]) -> dict[str, Any]:
        return run_backtest(candles, **self.params)
