from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Body, HTTPException, Request

from tripagent.auth import enforce_daily_plan_quota, require_authenticated_user, rollback_daily_plan_quota
from tripagent.config import get_settings
from tripagent.models import AlternativesResponse, PlanRequest, PlanResponse, ReplanRequest, ReplanResponse
from tripagent.persistence import PERSISTENCE
from tripagent.security import extract_session_id
from tripagent.service import plan, rank_alternatives
from tripagent.web.dependencies import ensure_plan_enabled, guard_costly_endpoint

router = APIRouter(tags=["plan"])


def _record_ab_conversion_if_present(request: Request, username: str, objective: str) -> None:
    experiment = request.headers.get("X-AB-Experiment", "").strip()
    variant = request.headers.get("X-AB-Variant", "").strip()
    if not experiment or not variant:
        return
    session_id = extract_session_id(request)
    PERSISTENCE.record_ab_event(
        session_id=session_id,
        user_id=username,
        experiment=experiment,
        variant=variant,
        objective=objective,
        event_type="conversion",
        value=1.0,
        meta={"source": "plan_endpoint"},
    )


@router.get("/queue/my")
def my_queue(request: Request):
    settings = get_settings()
    username = require_authenticated_user(request, settings)
    return {"items": PERSISTENCE.list_queue_for_user(username)}


@router.post("/plan", response_model=PlanResponse)
def plan_endpoint(request: Request, req: PlanRequest = Body(...)):
    settings = get_settings()
    username = require_authenticated_user(request, settings)
    quota_reserved = False
    run_id = f"{username}_{int(datetime.now().timestamp())}"
    try:
        enforce_daily_plan_quota(settings, username)
        quota_reserved = True
    except HTTPException:
        raise

    try:
        guard_costly_endpoint(
            request=request,
            endpoint="plan",
            limit=settings.rate_limit_plan_per_window,
        )
        ensure_plan_enabled()
    except HTTPException as exc:
        if quota_reserved:
            rollback_daily_plan_quota(username)
        if exc.status_code == 503 and settings.plan_queue_enabled:
            queue_id = PERSISTENCE.enqueue_plan_request(
                username=username,
                payload=req.model_dump(),
                reason=exc.detail,
            )
            raise HTTPException(
                status_code=202,
                detail={
                    "message": "Plan request queued due to fallback mode",
                    "queue_id": queue_id,
                    "reason": exc.detail,
                },
            ) from exc
        raise
    try:
        result = plan(req, out_dir="out", run_id=run_id)
        _record_ab_conversion_if_present(request, username, req.objective)
        return result
    except NotImplementedError as exc:
        if quota_reserved:
            rollback_daily_plan_quota(username)
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        if quota_reserved:
            rollback_daily_plan_quota(username)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        if quota_reserved:
            rollback_daily_plan_quota(username)
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _shift_hhmm(hhmm: str, delay_min: int) -> str:
    base = datetime.strptime(hhmm, "%H:%M")
    shifted = base + timedelta(minutes=delay_min)
    return shifted.strftime("%H:%M")


@router.post("/plan/replan", response_model=ReplanResponse)
def replan_endpoint(request: Request, req: ReplanRequest = Body(...)):
    settings = get_settings()
    username = require_authenticated_user(request, settings)
    guard_costly_endpoint(
        request=request,
        endpoint="plan",
        limit=settings.rate_limit_plan_per_window,
    )
    ensure_plan_enabled()

    plan_req = req.base_request.model_copy(deep=True)
    removed = set(req.removed_place_ids)
    for day in plan_req.days:
        if req.delay_min:
            day.day_start_time = _shift_hhmm(day.day_start_time, req.delay_min)
        if removed:
            day.pois = [poi for poi in day.pois if poi.place_id not in removed]
        if not day.pois:
            raise HTTPException(status_code=400, detail="Replan with no POIs: check removed_place_ids")

    run_id = f"{username}_replan_{int(datetime.now().timestamp())}"
    try:
        result = plan(plan_req, out_dir="out", run_id=run_id)
    except (ValueError, RuntimeError, NotImplementedError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ReplanResponse(
        mode=result.mode,
        objective=result.objective,
        days=result.days,
        replan_reason=req.reason,
        applied_delay_min=req.delay_min,
        removed_place_ids=list(removed),
    )


@router.post("/plan/alternatives", response_model=AlternativesResponse)
def plan_alternatives(request: Request, req: PlanRequest = Body(...)):
    settings = get_settings()
    require_authenticated_user(request, settings)
    guard_costly_endpoint(
        request=request,
        endpoint="plan",
        limit=settings.rate_limit_plan_per_window,
    )
    ensure_plan_enabled()
    return rank_alternatives(req, out_dir="out")
