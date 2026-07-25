"""API v1 router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import ai, analytics, auth, backtests, draws, recommendations, settings, strategies, system

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(system.router)
api_router.include_router(draws.router)
api_router.include_router(analytics.router)
api_router.include_router(recommendations.router)
api_router.include_router(backtests.router)
api_router.include_router(strategies.router)
api_router.include_router(settings.router)
api_router.include_router(ai.router)