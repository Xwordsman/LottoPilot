"""Analytics routes."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DbSession, RequestIdDep
from app.api.response import success_response
from app.models.draw import Draw
from app.schemas.analytics import AnalyticsOverviewData
from app.services.analytics import (
    DrawView,
    cooccurrence,
    frequency,
    hot_cold,
    missing_streaks,
    overview_metrics,
    sum_span_odd_even,
    zone_distribution,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _load_draws(db: DbSession, lottery_type: str, window: int | None) -> list[DrawView]:
    stmt = (
        select(Draw)
        .where(Draw.lottery_type == lottery_type)
        .order_by(Draw.draw_date.desc(), Draw.issue.desc())
    )
    if window:
        stmt = stmt.limit(window)
    rows = db.scalars(stmt).all()
    return [
        DrawView(
            issue=row.issue,
            draw_date=row.draw_date,
            primary_numbers=list(row.primary_numbers),
            secondary_numbers=list(row.secondary_numbers),
        )
        for row in rows
    ]


@router.get("/overview")
def analytics_overview(
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
    lottery_type: str = Query(default="ssq", pattern="^(ssq|dlt)$"),
    window: int = Query(default=50, ge=1, le=5000),
):
    _ = user
    draws = _load_draws(db, lottery_type, window)
    history = _load_draws(db, lottery_type, None)
    data = AnalyticsOverviewData(
        lottery_type=lottery_type,  # type: ignore[arg-type]
        metrics=overview_metrics(draws),
        hot_cold=hot_cold(draws, lottery_type=lottery_type, window=min(window, 30)),  # type: ignore[arg-type]
        frequency_primary=frequency(draws, lottery_type=lottery_type, zone="primary"),  # type: ignore[arg-type]
        missing_primary=missing_streaks(history, lottery_type=lottery_type, zone="primary"),  # type: ignore[arg-type]
        sum_span=sum_span_odd_even(draws),
        zones=zone_distribution(draws, lottery_type=lottery_type),  # type: ignore[arg-type]
        cooccurrence=cooccurrence(draws, lottery_type=lottery_type, top_k=20),  # type: ignore[arg-type]
    )
    return success_response(data.model_dump(mode="json"), request_id)


@router.get("/frequency")
def analytics_frequency(
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
    lottery_type: str = Query(default="ssq", pattern="^(ssq|dlt)$"),
    zone: str = Query(default="primary", pattern="^(primary|secondary)$"),
    window: int | None = Query(default=50, ge=1, le=5000),
):
    _ = user
    draws = _load_draws(db, lottery_type, window)
    data = {
        "lottery_type": lottery_type,
        "zone": zone,
        "window": window,
        "items": frequency(draws, lottery_type=lottery_type, zone=zone),  # type: ignore[arg-type]
    }
    return success_response(data, request_id)


@router.get("/missing")
def analytics_missing(
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
    lottery_type: str = Query(default="ssq", pattern="^(ssq|dlt)$"),
    zone: str = Query(default="primary", pattern="^(primary|secondary)$"),
):
    _ = user
    draws = _load_draws(db, lottery_type, None)
    data = {
        "lottery_type": lottery_type,
        "zone": zone,
        "items": missing_streaks(draws, lottery_type=lottery_type, zone=zone),  # type: ignore[arg-type]
    }
    return success_response(data, request_id)


@router.get("/hot-cold")
def analytics_hot_cold(
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
    lottery_type: str = Query(default="ssq", pattern="^(ssq|dlt)$"),
    window: int = Query(default=30, ge=1, le=5000),
    hot_n: int = Query(default=6, ge=1, le=20),
    cold_n: int = Query(default=6, ge=1, le=20),
):
    _ = user
    draws = _load_draws(db, lottery_type, window)
    data = {
        "lottery_type": lottery_type,
        **hot_cold(
            draws,
            lottery_type=lottery_type,
            window=window,
            hot_n=hot_n,
            cold_n=cold_n,
        ),  # type: ignore[arg-type]
    }
    return success_response(data, request_id)


@router.get("/sum-span")
def analytics_sum_span(
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
    lottery_type: str = Query(default="ssq", pattern="^(ssq|dlt)$"),
    window: int = Query(default=50, ge=1, le=5000),
):
    _ = user
    draws = _load_draws(db, lottery_type, window)
    data = {
        "lottery_type": lottery_type,
        "window": window,
        "items": sum_span_odd_even(draws),
    }
    return success_response(data, request_id)


@router.get("/zones")
def analytics_zones(
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
    lottery_type: str = Query(default="ssq", pattern="^(ssq|dlt)$"),
    window: int = Query(default=50, ge=1, le=5000),
):
    _ = user
    draws = _load_draws(db, lottery_type, window)
    data = {
        "lottery_type": lottery_type,
        "window": window,
        "items": zone_distribution(draws, lottery_type=lottery_type),  # type: ignore[arg-type]
    }
    return success_response(data, request_id)


@router.get("/cooccurrence")
def analytics_cooccurrence(
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
    lottery_type: str = Query(default="ssq", pattern="^(ssq|dlt)$"),
    window: int = Query(default=100, ge=1, le=5000),
    top_k: int = Query(default=20, ge=1, le=100),
):
    _ = user
    draws = _load_draws(db, lottery_type, window)
    data = {
        "lottery_type": lottery_type,
        "window": window,
        "top_k": top_k,
        "items": cooccurrence(draws, lottery_type=lottery_type, top_k=top_k),  # type: ignore[arg-type]
    }
    return success_response(data, request_id)


@router.get("/numbers")
def analytics_numbers(
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
    lottery_type: str = Query(default="ssq", pattern="^(ssq|dlt)$"),
    zone: str = Query(default="primary", pattern="^(primary|secondary)$"),
    window: int | None = Query(default=50, ge=1, le=5000),
):
    """API.md alias combining frequency + missing streaks."""
    _ = user
    draws = _load_draws(db, lottery_type, window)
    history = _load_draws(db, lottery_type, None)
    data = {
        "lottery_type": lottery_type,
        "zone": zone,
        "window": window,
        "frequency": frequency(draws, lottery_type=lottery_type, zone=zone),  # type: ignore[arg-type]
        "missing": missing_streaks(history, lottery_type=lottery_type, zone=zone),  # type: ignore[arg-type]
        "hot_cold": hot_cold(draws, lottery_type=lottery_type, window=min(window or 30, 30)),  # type: ignore[arg-type]
    }
    return success_response(data, request_id)


@router.get("/distributions")
def analytics_distributions(
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
    lottery_type: str = Query(default="ssq", pattern="^(ssq|dlt)$"),
    window: int = Query(default=50, ge=1, le=5000),
):
    """API.md alias combining sum/span/odd-even and zone distributions."""
    _ = user
    draws = _load_draws(db, lottery_type, window)
    data = {
        "lottery_type": lottery_type,
        "window": window,
        "sum_span": sum_span_odd_even(draws),
        "zones": zone_distribution(draws, lottery_type=lottery_type),  # type: ignore[arg-type]
    }
    return success_response(data, request_id)
