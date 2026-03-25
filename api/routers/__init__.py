from api.routers.analytics import router as analytics_router
from api.routers.products import router as products_router
from api.routers.settings import router as settings_router
from api.routers.sites import router as sites_router

__all__ = ["products_router", "sites_router", "analytics_router", "settings_router"]
