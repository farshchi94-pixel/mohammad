"""Pure-Python DayTraderSkill indicators and signal rules.

The skill is deliberately dependency-light so it can run inside GitHub Actions and
on a Windows laptop without pandas/numpy. It only produces signals; it never sends
orders or connects to a broker.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


DEFAULTS: dict[str, Any] = {
    "ema_fast": 55,
    "ema_slow": 200,
    "adx_period": 14,
    "adx_min": 20.0,
    "rsi_period": 14,
    "long_rsi_min": 50.0,
    "long_rsi_max": 70.0,
    "short_rsi_min": 30.0,
    "short_rsi_max": 50.0,
    "chop_period": 14,
    "chop_max": 61.8,
    "atr_period": 14,
    "atr_multiplier": 2.0,
    "reward_r": 2.0,
    "breakeven_trigger": 0.5,
    "allow_short": False,
}


def _rma(values: Sequence[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if period <= 0 or len(values) < period:
        return out
    current = sum(values[:period]) / period
    out[period - 1] = current
    for i in range(period, len(values)):
        current = (current * (period - 1) + values[i]) / period
        out[i] = current
    return out


def ema(values: Sequence[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if period <= 0 or len(values) < period:
        return out
    alpha = 2.0 / (period + 1.0)
    current = sum(values[:period]) / period
    out[period - 1] = current
    for i in range(period, len(values)):
        current = values[i] * alpha + current * (1.0 - alpha)
        out[i] = current
    return out


def true_ranges(candles: Sequence[Mapping[str, float]]) -> list[float]:
    values: list[float] = []
    for i, candle in enumerate(candles):
        previous = candles[i - 1]["close"] if i else candle["close"]
        values.append(max(
            candle["high"] - candle["low"],
            abs(candle["high"] - previous),
            abs(candle["low"] - previous),
        ))
    return values


def atr(candles: Sequence[Mapping[str, float]], period: int = 14) -> list[float | None]:
    return _rma(true_ranges(candles), period)


def rsi(values: Sequence[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if period <= 0 or len(values) <= period:
        return out
    gains = [max(values[i] - values[i - 1], 0.0) for i in range(1, period + 1)]
    losses = [max(values[i - 1] - values[i], 0.0) for i in range(1, period + 1)]
    average_gain = sum(gains) / period
    average_loss = sum(losses) / period

    def value() -> float:
        if average_loss == 0:
            return 100.0 if average_gain > 0 else 50.0
        return 100.0 - 100.0 / (1.0 + average_gain / average_loss)

    out[period] = value()
    for i in range(period + 1, len(values)):
        delta = values[i] - values[i - 1]
        average_gain = (average_gain * (period - 1) + max(delta, 0.0)) / period
        average_loss = (average_loss * (period - 1) + max(-delta, 0.0)) / period
        out[i] = value()
    return out


def adx(candles: Sequence[Mapping[str, float]], period: int = 14) -> list[float | None]:
    """Wilder ADX, including the directional movement filter."""
    if not candles:
        return []
    tr = true_ranges(candles)
    plus_dm: list[float] = [0.0]
    minus_dm: list[float] = [0.0]
    for i in range(1, len(candles)):
        up = candles[i]["high"] - candles[i - 1]["high"]
        down = candles[i - 1]["low"] - candles[i]["low"]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
    tr_rma = _rma(tr, period)
    plus_rma = _rma(plus_dm, period)
    minus_rma = _rma(minus_dm, period)
    dx: list[float] = [0.0] * len(candles)
    for i in range(len(candles)):
        if tr_rma[i] in (None, 0) or plus_rma[i] is None or minus_rma[i] is None:
            continue
        plus_di = 100.0 * plus_rma[i] / tr_rma[i]
        minus_di = 100.0 * minus_rma[i] / tr_rma[i]
        total = plus_di + minus_di
        dx[i] = 100.0 * abs(plus_di - minus_di) / total if total else 0.0
    return _rma(dx, period)


def choppiness(candles: Sequence[Mapping[str, float]], period: int = 14) -> list[float | None]:
    """Choppiness Index; values above 61.8 are treated as a no-trade zone."""
    tr = true_ranges(candles)
    out: list[float | None] = [None] * len(candles)
    if period <= 0:
        return out
    denominator = math.log10(period)
    for i in range(period - 1, len(candles)):
        window = candles[i - period + 1:i + 1]
        high = max(c["high"] for c in window)
        low = min(c["low"] for c in window)
        span = high - low
        total_tr = sum(tr[i - period + 1:i + 1])
        out[i] = 100.0 if span <= 0 or total_tr <= 0 else 100.0 * math.log10(total_tr / span) / denominator
    return out


def build_indicators(candles: Sequence[Mapping[str, float]], params: Mapping[str, Any] | None = None) -> dict[str, list[float | None]]:
    p = {**DEFAULTS, **dict(params or {})}
    closes = [float(c["close"]) for c in candles]
    return {
        "ema_fast": ema(closes, int(p["ema_fast"])),
        "ema_slow": ema(closes, int(p["ema_slow"])),
        "adx": adx(candles, int(p["adx_period"])),
        "rsi": rsi(closes, int(p["rsi_period"])),
        "chop": choppiness(candles, int(p["chop_period"])),
        "atr": atr(candles, int(p["atr_period"])),
    }


def signal_at(index: int, candles: Sequence[Mapping[str, float]], indicators: Mapping[str, Sequence[float | None]], params: Mapping[str, Any] | None = None) -> str | None:
    p = {**DEFAULTS, **dict(params or {})}
    try:
        close = float(candles[index]["close"])
        fast = indicators["ema_fast"][index]
        slow = indicators["ema_slow"][index]
        strength = indicators["adx"][index]
        oscillator = indicators["rsi"][index]
        chop = indicators["chop"][index]
    except (IndexError, KeyError, TypeError):
        return None
    if None in (fast, slow, strength, oscillator, chop) or float(strength) <= float(p["adx_min"]):
        return None
    if float(chop) > float(p["chop_max"]):
        return None
    if close > float(fast) > float(slow) and float(p["long_rsi_min"]) <= float(oscillator) <= float(p["long_rsi_max"]):
        return "long"
    if bool(p.get("allow_short", False)) and close < float(fast) < float(slow) and float(p["short_rsi_min"]) <= float(oscillator) <= float(p["short_rsi_max"]):
        return "short"
    return None


def latest_snapshot(indicators: Mapping[str, Sequence[float | None]]) -> dict[str, float | None]:
    snapshot: dict[str, float | None] = {}
    for name, values in indicators.items():
        snapshot[name] = None if not values else values[-1]
    return snapshot
