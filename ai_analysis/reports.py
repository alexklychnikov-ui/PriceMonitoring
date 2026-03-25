from __future__ import annotations

import json

import pandas as pd


def format_sites_comparison(df: pd.DataFrame) -> str:
    if df.empty:
        return "Нет данных по сайтам."
    lines = []
    for _, row in df.iterrows():
        lines.append(f"- {row['site_name']}: {row['current_price']} ₽ ({row['url']})")
    return "\n".join(lines)


def format_top_changes(rows: list[dict]) -> str:
    if not rows:
        return "Нет значимых изменений."
    return "\n".join(
        f"- {item['name']} ({item['site']}): {item['change_pct']}%" for item in rows[:5]
    )


def safe_json_loads(raw: str) -> dict:
    try:
        return json.loads(raw)
    except Exception:
        return {"raw": raw}
