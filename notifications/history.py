from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import quote


class PriceHistoryFormatter:
    def format_history_chart_url(self, product_id: int, days: int = 30) -> str:
        chart = {
            "type": "line",
            "data": {
                "labels": [f"D-{d}" for d in range(days, 0, -1)],
                "datasets": [{"label": f"Product #{product_id}", "data": [0 for _ in range(days)]}],
            },
        }
        payload = quote(json.dumps(chart, ensure_ascii=False))
        return f"https://quickchart.io/chart?c={payload}"

    def format_history_text(self, history: list[dict]) -> str:
        if not history:
            return "История цен отсутствует."
        prices = [float(item["price"]) for item in history]
        min_price, max_price = min(prices), max(prices)
        spread = max(max_price - min_price, 1.0)
        lines = []
        for row in history:
            ts = row.get("scraped_at")
            if isinstance(ts, datetime):
                label = ts.strftime("%d.%m")
            else:
                label = str(ts)[:10]
            price = float(row["price"])
            bars = int(((price - min_price) / spread) * 16) + 1
            lines.append(f"{label}: {int(price)}₽ {'█' * bars}")
        return "\n".join(lines)
