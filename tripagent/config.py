from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


def load_env() -> None:
    load_dotenv(override=False)


def _bool_env(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _list_env(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class AppSettings:
    # Cost guard / graceful degradation
    costly_endpoints_enabled: bool
    plan_endpoint_enabled: bool
    fallback_mode_enabled: bool
    fallback_message: str
    admin_token: str | None
    auth_enabled: bool
    auth_users: tuple[str, ...]
    session_ttl_sec: int
    plan_daily_quota_per_user: int
    free_daily_quota_per_user: int
    pro_daily_quota_per_user: int
    plan_queue_enabled: bool
    est_ads_revenue_per_request: float
    subscription_monthly_price: float
    monetization_target_margin: float
    infra_monthly_cost_estimate: float
    subscription_price_min: float
    subscription_price_max: float
    max_price_change_pct: float
    target_conversion_rate: float

    # API authentication & limits
    require_api_key: bool
    api_keys: tuple[str, ...]
    rate_limit_window_sec: int
    rate_limit_plan_per_window: int
    rate_limit_search_per_window: int
    rate_limit_parking_per_window: int
    cors_allowed_origins: tuple[str, ...]

    # Caching
    cache_enabled: bool
    cache_backend: str
    cache_redis_url: str | None
    cache_ttl_place_details_sec: int
    cache_ttl_text_search_sec: int
    cache_ttl_nearby_search_sec: int
    cache_ttl_route_matrix_sec: int
    cache_ttl_polyline_sec: int

    # Simple business/cost estimation
    estimate_cost_places_text_search: float
    estimate_cost_places_nearby: float
    estimate_cost_places_details: float
    estimate_cost_routes_matrix: float
    estimate_cost_routes_polyline: float
    health_check_upstream_enabled: bool
    daily_budget_limit: float
    budget_alert_threshold_warn: float
    budget_alert_threshold_critical: float
    budget_auto_fallback: bool
    ab_test_enabled: bool


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    load_env()
    return AppSettings(
        costly_endpoints_enabled=_bool_env("TRIPAGENT_COSTLY_ENDPOINTS_ENABLED", True),
        plan_endpoint_enabled=_bool_env("TRIPAGENT_PLAN_ENDPOINT_ENABLED", True),
        fallback_mode_enabled=_bool_env("TRIPAGENT_FALLBACK_MODE_ENABLED", False),
        fallback_message=os.getenv(
            "TRIPAGENT_FALLBACK_MESSAGE",
            "Optimizacion temporalmente no disponible por control de costos.",
        ),
        admin_token=os.getenv("TRIPAGENT_ADMIN_TOKEN"),
        auth_enabled=_bool_env("TRIPAGENT_AUTH_ENABLED", True),
        auth_users=_list_env("TRIPAGENT_AUTH_USERS"),
        session_ttl_sec=_int_env("TRIPAGENT_SESSION_TTL_SEC", 86_400),
        plan_daily_quota_per_user=_int_env("TRIPAGENT_PLAN_DAILY_QUOTA_PER_USER", 20),
        free_daily_quota_per_user=_int_env("TRIPAGENT_FREE_DAILY_QUOTA_PER_USER", 10),
        pro_daily_quota_per_user=_int_env("TRIPAGENT_PRO_DAILY_QUOTA_PER_USER", 100),
        plan_queue_enabled=_bool_env("TRIPAGENT_PLAN_QUEUE_ENABLED", True),
        est_ads_revenue_per_request=_float_env("TRIPAGENT_EST_ADS_REVENUE_PER_REQUEST", 0.0),
        subscription_monthly_price=_float_env("TRIPAGENT_SUBSCRIPTION_MONTHLY_PRICE", 0.0),
        monetization_target_margin=_float_env("TRIPAGENT_MONETIZATION_TARGET_MARGIN", 0.15),
        infra_monthly_cost_estimate=_float_env("TRIPAGENT_INFRA_MONTHLY_COST_ESTIMATE", 0.0),
        subscription_price_min=_float_env("TRIPAGENT_SUBSCRIPTION_PRICE_MIN", 0.0),
        subscription_price_max=_float_env("TRIPAGENT_SUBSCRIPTION_PRICE_MAX", 1_000_000.0),
        max_price_change_pct=_float_env("TRIPAGENT_MAX_PRICE_CHANGE_PCT", 0.2),
        target_conversion_rate=_float_env("TRIPAGENT_TARGET_CONVERSION_RATE", 0.03),
        require_api_key=_bool_env("TRIPAGENT_REQUIRE_API_KEY", False),
        api_keys=_list_env("TRIPAGENT_API_KEYS"),
        rate_limit_window_sec=_int_env("TRIPAGENT_RATE_LIMIT_WINDOW_SEC", 60),
        rate_limit_plan_per_window=_int_env("TRIPAGENT_RATE_LIMIT_PLAN_PER_WINDOW", 8),
        rate_limit_search_per_window=_int_env("TRIPAGENT_RATE_LIMIT_SEARCH_PER_WINDOW", 20),
        rate_limit_parking_per_window=_int_env("TRIPAGENT_RATE_LIMIT_PARKING_PER_WINDOW", 20),
        cors_allowed_origins=_list_env("TRIPAGENT_CORS_ALLOWED_ORIGINS"),
        cache_enabled=_bool_env("TRIPAGENT_CACHE_ENABLED", True),
        cache_backend=os.getenv("TRIPAGENT_CACHE_BACKEND", "memory").strip().lower(),
        cache_redis_url=os.getenv("TRIPAGENT_CACHE_REDIS_URL"),
        cache_ttl_place_details_sec=_int_env("TRIPAGENT_CACHE_TTL_PLACE_DETAILS_SEC", 3600),
        cache_ttl_text_search_sec=_int_env("TRIPAGENT_CACHE_TTL_TEXT_SEARCH_SEC", 1800),
        cache_ttl_nearby_search_sec=_int_env("TRIPAGENT_CACHE_TTL_NEARBY_SEARCH_SEC", 300),
        cache_ttl_route_matrix_sec=_int_env("TRIPAGENT_CACHE_TTL_ROUTE_MATRIX_SEC", 300),
        cache_ttl_polyline_sec=_int_env("TRIPAGENT_CACHE_TTL_POLYLINE_SEC", 300),
        estimate_cost_places_text_search=_float_env("TRIPAGENT_COST_PLACES_TEXT_SEARCH", 0.0),
        estimate_cost_places_nearby=_float_env("TRIPAGENT_COST_PLACES_NEARBY", 0.0),
        estimate_cost_places_details=_float_env("TRIPAGENT_COST_PLACES_DETAILS", 0.0),
        estimate_cost_routes_matrix=_float_env("TRIPAGENT_COST_ROUTES_MATRIX", 0.0),
        estimate_cost_routes_polyline=_float_env("TRIPAGENT_COST_ROUTES_POLYLINE", 0.0),
        health_check_upstream_enabled=_bool_env("TRIPAGENT_HEALTH_CHECK_UPSTREAM_ENABLED", False),
        daily_budget_limit=_float_env("TRIPAGENT_DAILY_BUDGET_LIMIT", 0.0),
        budget_alert_threshold_warn=_float_env("TRIPAGENT_BUDGET_ALERT_THRESHOLD_WARN", 0.7),
        budget_alert_threshold_critical=_float_env("TRIPAGENT_BUDGET_ALERT_THRESHOLD_CRITICAL", 0.9),
        budget_auto_fallback=_bool_env("TRIPAGENT_BUDGET_AUTO_FALLBACK", False),
        ab_test_enabled=_bool_env("TRIPAGENT_AB_TEST_ENABLED", True),
    )


def require_google_key() -> str:
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key:
        raise RuntimeError("Missing env var GOOGLE_MAPS_API_KEY (create .env and set it).")
    return key
