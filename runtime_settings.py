from __future__ import annotations

import copy
import json
from typing import Any

from redis.asyncio import Redis

from config import settings


RUNTIME_SETTINGS_KEY = "settings:runtime:v1"

DEFAULT_RUNTIME_SETTINGS: dict[str, dict[str, Any]] = {
    "parsing": {
        "winter": True,
        "winter_studded": True,
        "winter_non_studded": True,
        "summer": True,
        "parse_interval_hours": max(int(settings.PARSE_INTERVAL_HOURS), 1),
    },
    "alerts": {
        "enabled": True,
        "min_change_pct": float(settings.PRICE_ALERT_THRESHOLD_PCT),
        "send_price_drop": True,
        "send_price_rise": True,
    },
}


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "да"}:
            return True
        if lowered in {"0", "false", "no", "нет"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _to_int(value: Any, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, min_value), max_value)


def _to_float(value: Any, default: float, min_value: float, max_value: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, min_value), max_value)


def normalize_runtime_settings(raw: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    data = raw or {}
    parsing = data.get("parsing", {}) if isinstance(data, dict) else {}
    alerts = data.get("alerts", {}) if isinstance(data, dict) else {}

    return {
        "parsing": {
            "winter": _to_bool(parsing.get("winter"), DEFAULT_RUNTIME_SETTINGS["parsing"]["winter"]),
            "winter_studded": _to_bool(
                parsing.get("winter_studded"),
                DEFAULT_RUNTIME_SETTINGS["parsing"]["winter_studded"],
            ),
            "winter_non_studded": _to_bool(
                parsing.get("winter_non_studded"),
                DEFAULT_RUNTIME_SETTINGS["parsing"]["winter_non_studded"],
            ),
            "summer": _to_bool(parsing.get("summer"), DEFAULT_RUNTIME_SETTINGS["parsing"]["summer"]),
            "parse_interval_hours": _to_int(
                parsing.get("parse_interval_hours"),
                DEFAULT_RUNTIME_SETTINGS["parsing"]["parse_interval_hours"],
                1,
                168,
            ),
        },
        "alerts": {
            "enabled": _to_bool(alerts.get("enabled"), DEFAULT_RUNTIME_SETTINGS["alerts"]["enabled"]),
            "min_change_pct": _to_float(
                alerts.get("min_change_pct"),
                DEFAULT_RUNTIME_SETTINGS["alerts"]["min_change_pct"],
                0.1,
                100.0,
            ),
            "send_price_drop": _to_bool(
                alerts.get("send_price_drop"),
                DEFAULT_RUNTIME_SETTINGS["alerts"]["send_price_drop"],
            ),
            "send_price_rise": _to_bool(
                alerts.get("send_price_rise"),
                DEFAULT_RUNTIME_SETTINGS["alerts"]["send_price_rise"],
            ),
        },
    }


def merge_runtime_settings(
    current: dict[str, dict[str, Any]],
    patch: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if not patch:
        return normalize_runtime_settings(current)
    merged = copy.deepcopy(current)
    for section_name in ("parsing", "alerts"):
        section_patch = patch.get(section_name) if isinstance(patch, dict) else None
        if isinstance(section_patch, dict):
            merged.setdefault(section_name, {})
            merged[section_name].update(section_patch)
    return normalize_runtime_settings(merged)


async def get_runtime_settings() -> dict[str, dict[str, Any]]:
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        raw = await redis.get(RUNTIME_SETTINGS_KEY)
        if not raw:
            return copy.deepcopy(DEFAULT_RUNTIME_SETTINGS)
        parsed = json.loads(raw)
        return normalize_runtime_settings(parsed if isinstance(parsed, dict) else None)
    except Exception:
        return copy.deepcopy(DEFAULT_RUNTIME_SETTINGS)
    finally:
        await redis.aclose()


async def save_runtime_settings(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    normalized = normalize_runtime_settings(payload)
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await redis.set(RUNTIME_SETTINGS_KEY, json.dumps(normalized))
    finally:
        await redis.aclose()
    return normalized

