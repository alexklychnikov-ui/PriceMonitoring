from collections.abc import AsyncGenerator
import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config import settings


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_in_celery = os.environ.get("CELERY_WORKER", "") == "1"

engine = create_async_engine(
    settings.DATABASE_URL,
    future=True,
    poolclass=NullPool if _in_celery else None,
    pool_pre_ping=not _in_celery,
    connect_args={"ssl": False},
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
