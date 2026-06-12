from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from tripagent.config import get_settings
from tripagent.runtime_flags import RUNTIME_FLAGS
from tripagent.web.paths import ADS_TXT, GUIDES_HTML, INDEX_HTML, LANDING_HTML, POLICIES_HTML, ROBOTS_TXT

router = APIRouter()


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def root_ui():
    if not INDEX_HTML.exists():
        return HTMLResponse(
            content="<h2>UI not found</h2><p>Missing <code>tripagent/static/index.html</code></p>",
            status_code=404,
        )
    return HTMLResponse(content=INDEX_HTML.read_text(encoding="utf-8"))


@router.get("/landing", response_class=HTMLResponse, include_in_schema=False)
def landing_page():
    if not LANDING_HTML.exists():
        return HTMLResponse(
            content="<h2>Landing not found</h2><p>Missing <code>tripagent/static/landing.html</code></p>",
            status_code=404,
        )
    return HTMLResponse(content=LANDING_HTML.read_text(encoding="utf-8"))


@router.get("/guides", response_class=HTMLResponse, include_in_schema=False)
def guides_page():
    if not GUIDES_HTML.exists():
        return HTMLResponse(content="<h2>Guides not found</h2>", status_code=404)
    return HTMLResponse(content=GUIDES_HTML.read_text(encoding="utf-8"))


@router.get("/policies", response_class=HTMLResponse, include_in_schema=False)
def policies_page():
    if not POLICIES_HTML.exists():
        return HTMLResponse(content="<h2>Policies not found</h2>", status_code=404)
    return HTMLResponse(content=POLICIES_HTML.read_text(encoding="utf-8"))


@router.get("/ads.txt", response_class=PlainTextResponse, include_in_schema=False)
def ads_txt():
    if not ADS_TXT.exists():
        return PlainTextResponse("", status_code=404)
    return PlainTextResponse(ADS_TXT.read_text(encoding="utf-8"))


@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
def robots_txt():
    if not ROBOTS_TXT.exists():
        return PlainTextResponse("", status_code=404)
    return PlainTextResponse(ROBOTS_TXT.read_text(encoding="utf-8"))


@router.get("/ui-check", tags=["info"])
def ui_check():
    settings = get_settings()
    runtime = RUNTIME_FLAGS.snapshot()
    plan_enabled = RUNTIME_FLAGS.costly_enabled(settings) and RUNTIME_FLAGS.plan_enabled(settings)
    return {
        "html_ui_active": INDEX_HTML.exists(),
        "html_ui_path": str(INDEX_HTML),
        "plan_enabled": plan_enabled,
        "auth_enabled": settings.auth_enabled,
        "plan_queue_enabled": settings.plan_queue_enabled,
        "fallback_mode_enabled": settings.fallback_mode_enabled,
        "fallback_message": settings.fallback_message,
        "runtime_flags": runtime,
    }

