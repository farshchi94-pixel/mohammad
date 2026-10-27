#!/usr/bin/env python3
"""Validate Signal Hub JSON outputs for CI and scheduled runs.

The validator emits one compact JSON event so GitHub Actions summaries and logs
can be searched without exposing credentials or full market payloads.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

DEFAULT_OUTPUTS = (
    "signals.json",
    "whales.json",
    "whalepro.json",
    "candles.json",
    "market.json",
    "competitors.json",
    "consensus.json",
    "dex_consensus.json",
    "paper.json",
)


def event(status: str, **fields: object) -> None:
    payload = {"event": "signal_hub_output_validation", "status": status, **fields}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def main() -> int:
    outputs = tuple(
        x.strip()
        for x in os.getenv("SIGNAL_HUB_OUTPUTS", ",".join(DEFAULT_OUTPUTS)).split(",")
        if x.strip()
    )
    max_age = int(os.getenv("MAX_OUTPUT_AGE_SECONDS", str(6 * 60 * 60)))
    now = int(time.time())
    errors: list[str] = []
    checked: list[dict[str, object]] = []

    for name in outputs:
        path = Path(name)
        if not path.is_file():
            errors.append(f"missing:{name}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - report malformed provider output
            errors.append(f"invalid_json:{name}:{type(exc).__name__}")
            continue
        if not isinstance(data, dict):
            errors.append(f"expected_object:{name}")
            continue
        updated = data.get("updated")
        if not isinstance(updated, (int, float)):
            errors.append(f"missing_updated:{name}")
            continue
        age = now - int(updated)
        if age < -300:
            errors.append(f"future_timestamp:{name}")
        elif age > max_age:
            errors.append(f"stale:{name}:{age}s")
        checked.append({"file": name, "age_seconds": max(0, age)})

    if errors:
        event("failed", checked=checked, errors=errors, max_age_seconds=max_age)
        return 1
    event("ok", checked=checked, max_age_seconds=max_age)
    return 0


if __name__ == "__main__":
    sys.exit(main())
