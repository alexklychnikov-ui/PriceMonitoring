from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from db.database import AsyncSessionLocal
from db.models import Site


router = APIRouter()


@router.get("")
async def get_sites() -> list[dict]:
    async with AsyncSessionLocal() as session:
        rows = list(await session.scalars(select(Site).order_by(Site.name.asc())))
        return [
            {
                "id": s.id,
                "name": s.name,
                "base_url": s.base_url,
                "catalog_url": s.catalog_url,
                "is_active": s.is_active,
            }
            for s in rows
        ]
