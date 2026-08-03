from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.account_mapping import router as account_mapping_router
from app.routers.agent import router as agent_router
from app.routers.health import router as health_router
from app.routers.tax_declaration import router as tax_declaration_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(account_mapping_router, prefix=settings.api_prefix)
    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(agent_router, prefix=settings.api_prefix)
    app.include_router(tax_declaration_router, prefix=settings.api_prefix)
    return app


app = create_app()
