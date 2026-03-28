from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED

from api.routers.analytics import router as analytics_router
from api.routers.products import router as products_router
from api.routers.settings import router as settings_router
from api.routers.sites import router as sites_router
from config import settings


def _cors_origins() -> list[str]:
    raw = (settings.CORS_ORIGINS or "").strip()
    if not raw:
        return ["http://localhost:5173"]
    return [p.strip() for p in raw.split(",") if p.strip()]


_basic = HTTPBasic()


def _verify_swagger_basic_auth(credentials: HTTPBasicCredentials = Depends(_basic)) -> None:
    correct_user = settings.FLOWER_USER
    correct_password = settings.FLOWER_PASSWORD
    is_ok = credentials.username == correct_user and credentials.password == correct_password
    if not is_ok:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )


app = FastAPI(title="Price Monitor API", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router, prefix="/api/products", tags=["products"])
app.include_router(sites_router, prefix="/api/sites", tags=["sites"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
app.include_router(settings_router, prefix="/api/settings", tags=["settings"])


@app.get("/openapi.json", include_in_schema=False, dependencies=[Depends(_verify_swagger_basic_auth)])
async def openapi_json() -> dict:
    return app.openapi()


@app.get("/docs", include_in_schema=False, dependencies=[Depends(_verify_swagger_basic_auth)])
async def swagger_ui() -> object:
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Price Monitor API - Swagger UI")


@app.get("/redoc", include_in_schema=False, dependencies=[Depends(_verify_swagger_basic_auth)])
async def redoc_ui() -> object:
    # keep simple: reuse swagger UI; redoc isn't required for this task
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Price Monitor API - Swagger UI")


@app.get("/")
async def root() -> dict:
    return {"ok": True, "service": "price-monitor-api"}
