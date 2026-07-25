"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api.middleware import RequestContextMiddleware
from app.api.response import error_response, success_response
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger
from app.schemas.common import HealthData

logger = get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app_log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        logger.info(
            "LottoPilot starting env=%s version=%s commit=%s",
            settings.app_env,
            settings.app_version,
            settings.app_git_commit,
        )
        try:
            from app.workers.scheduler import start_scheduler

            start_scheduler(settings)
        except Exception:  # noqa: BLE001
            logger.exception("scheduler bootstrap failed")
        try:
            yield
        finally:
            try:
                from app.workers.scheduler import shutdown_scheduler

                shutdown_scheduler()
            except Exception:  # noqa: BLE001
                logger.exception("scheduler shutdown failed")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version or __version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins + ["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        request_id = getattr(request.state, "request_id", "unknown")
        return error_response(
            request_id=request_id,
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", "unknown")
        return error_response(
            request_id=request_id,
            code="VALIDATION_ERROR",
            message="请求参数校验失败",
            status_code=422,
            details={"errors": exc.errors()},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", "unknown")
        return error_response(
            request_id=request_id,
            code="HTTP_ERROR",
            message=str(exc.detail),
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception("unhandled error request_id=%s", request_id)
        return error_response(
            request_id=request_id,
            code="INTERNAL_ERROR",
            message="服务器内部错误",
            status_code=500,
        )

    @app.get("/health", include_in_schema=False)
    def root_health(request: Request):
        request_id = getattr(request.state, "request_id", "unknown")
        return success_response(HealthData().model_dump(), request_id)

    app.include_router(api_router, prefix="/api/v1")

    frontend_dist = Path(settings.frontend_dist_dir)
    if not frontend_dist.is_absolute():
        # Prefer container path /app/frontend_dist, fallback to repo frontend/dist for local dev.
        candidates = [
            Path("/app/frontend_dist"),
            Path(__file__).resolve().parents[2] / "frontend" / "dist",
            Path.cwd() / "frontend_dist",
            Path.cwd() / "frontend" / "dist",
        ]
        for candidate in candidates:
            if candidate.exists():
                frontend_dist = candidate
                break

    if frontend_dist.exists():
        assets_dir = frontend_dist / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/", include_in_schema=False)
        def spa_index():
            return FileResponse(frontend_dist / "index.html")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str):
            # Do not swallow API/docs/health.
            if full_path.startswith(("api/", "health", "assets/")):
                return error_response(
                    request_id="unknown",
                    code="NOT_FOUND",
                    message="Not Found",
                    status_code=404,
                )
            candidate = frontend_dist / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(frontend_dist / "index.html")

    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )


if __name__ == "__main__":
    run()
