from __future__ import annotations

import time

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from tripagent.config import get_settings
from tripagent.monetization import monetization_report
from tripagent.models import PlanRequest
from tripagent.ops_services import OpsCostService, OpsExperimentsService, OpsFinanceService
from tripagent.runtime_flags import RUNTIME_FLAGS
from tripagent.security import extract_session_id, resolve_session_user
from tripagent.service import plan
from tripagent.web.dependencies import require_admin_token

router = APIRouter(prefix="/ops", tags=["ops"])

cost_service = OpsCostService()
experiments_service = OpsExperimentsService()
finance_service = OpsFinanceService()


# --- Request Models ---
class CostGuardReq(BaseModel):
    costly_endpoints_enabled: bool | None = None
    plan_endpoint_enabled: bool | None = None

class CostForecastReq(BaseModel):
    baseline_daily_requests: int = Field(default=500, ge=0, le=2_000_000)
    horizon_days: int = Field(default=7, ge=1, le=365)

class WorkloadReplayReq(BaseModel):
    since_hours: int = Field(default=24, ge=1, le=24 * 90)
    multiplier: float = Field(default=1.0, ge=0.0, le=20.0)

class ABAssignReq(BaseModel):
    experiment: str = "objective_default"
    session_id: str | None = None
    variants: list[str] = Field(default_factory=lambda: ["time", "money", "comfort"])

class ABTrackReq(BaseModel):
    experiment: str = "objective_default"
    session_id: str | None = None
    variant: str
    event_type: str = Field(pattern="^(conversion|retention)$")
    value: float = 0.0
    objective: str | None = None

class ReconcileReq(BaseModel):
    month_ym: str | None = None
    apply_price: bool = False

class InfraCostReq(BaseModel):
    month_ym: str | None = None
    amount: float = 0.0
    notes: str | None = None

class AnnualReportReq(BaseModel):
    year: int | None = None
    scope: str = "calendar"


# --- Core Endpoints ---
@router.get("/config")
def ops_config(request: Request):
    require_admin_token(request)
    settings = get_settings()
    runtime = RUNTIME_FLAGS.snapshot()
    return {
        "costly_endpoints_enabled": settings.costly_endpoints_enabled,
        "plan_endpoint_enabled": settings.plan_endpoint_enabled,
        "fallback_mode_enabled": settings.fallback_mode_enabled,
        "fallback_message": settings.fallback_message,
        "cache_backend": settings.cache_backend,
        "rate_limit_window_sec": settings.rate_limit_window_sec,
        "rate_limits": {
            "plan": settings.rate_limit_plan_per_window,
            "search_places": settings.rate_limit_search_per_window,
            "nearest_parking": settings.rate_limit_parking_per_window,
        },
        "auth_required": settings.require_api_key,
        "runtime_flags": runtime,
    }


@router.get("/metrics")
def ops_metrics(request: Request):
    require_admin_token(request)
    return cost_service.metrics()


@router.post("/quality-check")
def quality_check(req: PlanRequest, request: Request):
    require_admin_token(request)
    result = plan(req, out_dir="out", run_id=f"quality_{int(time.time())}")
    warnings = []
    for day in result.days:
        warnings.extend(day.quality_warnings)
    return {
        "days": [day.model_dump() for day in result.days],
        "warnings_count": len(warnings),
        "warnings": warnings,
    }


@router.get("/monetization-report")
def ops_monetization_report(request: Request, days: int = 30):
    require_admin_token(request)
    settings = get_settings()
    return monetization_report(settings, days=days)


# --- Finance and Infrastructure Endpoints ---
@router.get("/finance/cashflow")
def ops_finance_cashflow(request: Request, month_ym: str | None = None):
    require_admin_token(request)
    settings = get_settings()
    return finance_service.cashflow(settings, month_ym=month_ym)

@router.post("/finance/infra-cost")
def ops_finance_infra_cost(req: InfraCostReq, request: Request):
    require_admin_token(request)
    return finance_service.upsert_infra_cost(req.month_ym, req.amount, req.notes)

@router.post("/finance/reconcile")
def ops_finance_reconcile(req: ReconcileReq, request: Request):
    require_admin_token(request)
    settings = get_settings()
    return finance_service.reconcile(settings, month_ym=req.month_ym, apply_price=req.apply_price)

@router.get("/finance/feasibility")
def ops_finance_feasibility(request: Request):
    require_admin_token(request)
    settings = get_settings()
    return finance_service.feasibility(settings)

@router.post("/finance/report")
def ops_finance_report(req: ReconcileReq, request: Request):
    require_admin_token(request)
    settings = get_settings()
    return finance_service.report_monthly(settings, month_ym=req.month_ym, apply_price=req.apply_price)

@router.post("/finance/report/annual")
def ops_finance_report_annual(req: AnnualReportReq, request: Request):
    require_admin_token(request)
    settings = get_settings()
    return finance_service.report_annual(settings, year=req.year, scope=req.scope)


# --- Cost Control Endpoints (Guardrails) ---
@router.post("/cost-guard")
def set_cost_guard(req: CostGuardReq, request: Request):
    require_admin_token(request)
    if req.costly_endpoints_enabled is not None:
        RUNTIME_FLAGS.set_costly_enabled(req.costly_endpoints_enabled)
    if req.plan_endpoint_enabled is not None:
        RUNTIME_FLAGS.set_plan_enabled(req.plan_endpoint_enabled)
    settings = get_settings()
    return {
        "effective_costly_endpoints_enabled": RUNTIME_FLAGS.costly_enabled(settings),
        "effective_plan_endpoint_enabled": RUNTIME_FLAGS.plan_enabled(settings),
        "runtime_flags": RUNTIME_FLAGS.snapshot(),
    }

@router.get("/budget-alerts")
def budget_alerts(request: Request):
    require_admin_token(request)
    settings = get_settings()
    return cost_service.budget_alerts(settings)

@router.post("/cost-forecast")
def cost_forecast(req: CostForecastReq, request: Request):
    require_admin_token(request)
    settings = get_settings()
    return cost_service.cost_forecast(settings, baseline_daily_requests=req.baseline_daily_requests, horizon_days=req.horizon_days)

@router.post("/cost-simulator")
def cost_simulator(req: CostForecastReq, request: Request):
    return cost_forecast(req, request)

@router.post("/workload-replay")
def workload_replay(req: WorkloadReplayReq, request: Request):
    require_admin_token(request)
    settings = get_settings()
    return cost_service.workload_replay(settings, since_hours=req.since_hours, multiplier=req.multiplier)

@router.get("/cache-efficiency")
def cache_efficiency(request: Request):
    require_admin_token(request)
    settings = get_settings()
    return cost_service.cache_efficiency(settings)


# --- A/B Testing Endpoints ---
def _resolve_user_session(request: Request) -> tuple[str | None, str | None]:
    session_id = extract_session_id(request)
    user_id = resolve_session_user(request)
    return session_id, user_id

@router.post("/ab/assign")
def ab_assign(req: ABAssignReq, request: Request):
    settings = get_settings()
    session_id, user_id = _resolve_user_session(request)
    return experiments_service.ab_assign(settings, experiment=req.experiment, override_session_id=req.session_id, variants=req.variants, session_id=session_id, user_id=user_id)

@router.post("/ab/track")
def ab_track(req: ABTrackReq, request: Request):
    settings = get_settings()
    session_id, user_id = _resolve_user_session(request)
    return experiments_service.ab_track(settings, experiment=req.experiment, variant=req.variant, objective=req.objective, event_type=req.event_type, value=req.value, session_id=session_id, user_id=user_id, override_session_id=req.session_id)

@router.get("/ab/report")
def ab_report(request: Request, experiment: str = "objective_default", since_days: int = 14):
    require_admin_token(request)
    return experiments_service.ab_report(experiment=experiment, since_days=since_days)
