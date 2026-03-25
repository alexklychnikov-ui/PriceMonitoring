from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.analytics import router as analytics_router
from api.routers.products import router as products_router
from api.routers.settings import router as settings_router
from api.routers.sites import router as sites_router


app = FastAPI(title="Price Monitor API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router, prefix="/api/products", tags=["products"])
app.include_router(sites_router, prefix="/api/sites", tags=["sites"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
app.include_router(settings_router, prefix="/api/settings", tags=["settings"])


@app.get("/")
async def root() -> dict:
    return {"ok": True, "service": "price-monitor-api"}
