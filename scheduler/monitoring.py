from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy import func, select

from config import settings
from db.database import AsyncSessionLocal
from db.models import Alert, ParseRun, Site
from scheduler.celery_app import app as celery_app


async def get_system_status() -> dict:
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_ok = False
    redis_latency_ms: float | None = None
    try:
        started = time.perf_counter()
        redis_ok = bool(await redis.ping())
        redis_latency_ms = round((time.perf_counter() - started) * 1000, 2)
    except Exception:
        redis_ok = False
    finally:
        await redis.aclose()

    pending_alerts = 0
    last_runs = []
    async with AsyncSessionLocal() as session:
        db_ok = True
        try:
            await session.execute(select(func.now()))
            pending_alerts = int(await session.scalar(select(func.count(Alert.id)).where(Alert.sent_at.is_(None))) or 0)
            site_rows = list(await session.scalars(select(Site)))
            for site in site_rows:
                row = await session.scalar(
                    select(ParseRun)
                    .where(ParseRun.site_id == site.id)
                    .order_by(ParseRun.started_at.desc())
                    .limit(1)
                )
                if row is None:
                    continue
                last_runs.append(
                    {
                        "site_name": site.name,
                        "status": row.status,
                        "started_at": row.started_at.isoformat() if row.started_at else None,
                        "products_found": row.products_found,
                    }
                )
        except Exception:
            db_ok = False

    try:
        inspect = celery_app.control.inspect(timeout=1.0)
        workers = {
            "active": inspect.active() or {},
            "reserved": inspect.reserved() or {},
            "scheduled": inspect.scheduled() or {},
        }
    except Exception:
        workers = {"active": {}, "reserved": {}, "scheduled": {}}

    return {
        "redis": {"ok": redis_ok, "latency_ms": redis_latency_ms},
        "db": {"ok": db_ok},
        "celery_workers": workers,
        "last_parse_runs": last_runs,
        "pending_alerts": pending_alerts,
    }


async def get_parse_stats(hours: int = 24) -> dict:
    window_start = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with AsyncSessionLocal() as session:
        try:
            rows = list(await session.scalars(select(ParseRun).where(ParseRun.started_at >= window_start)))
        except Exception:
            return {
                "period_hours": hours,
                "total_runs": 0,
                "success_runs": 0,
                "failed_runs": 0,
                "avg_parse_duration_seconds": 0.0,
                "products_found_total": 0,
                "price_changes_total": 0,
            }
        total = len(rows)
        success = sum(1 for r in rows if r.status == "success")
        failed = sum(1 for r in rows if r.status == "failed")
        products_found = sum(r.products_found or 0 for r in rows)

        durations = []
        for run in rows:
            if run.started_at and run.finished_at:
                durations.append((run.finished_at - run.started_at).total_seconds())
        avg_seconds = round(sum(durations) / len(durations), 2) if durations else 0.0

        changed_prices = int(
            await session.scalar(
                select(func.count(Alert.id))
                .where(Alert.alert_type == "price_changed", Alert.triggered_at >= window_start)
            )
            or 0
        )

    return {
        "period_hours": hours,
        "total_runs": total,
        "success_runs": success,
        "failed_runs": failed,
        "avg_parse_duration_seconds": avg_seconds,
        "products_found_total": products_found,
        "price_changes_total": changed_prices,
    }


health_app = FastAPI()


@health_app.get("/health")
async def health() -> dict:
    status = await get_system_status()
    ok = status["redis"]["ok"] and status["db"]["ok"]
    return {"ok": ok, "status": status}
