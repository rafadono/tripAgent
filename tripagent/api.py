from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

from tripagent.config import get_settings
from tripagent.health import router as health_router
from tripagent.web.middleware import install_metrics_middleware
from tripagent.web.paths import INDEX_HTML, STATIC_DIR
from tripagent.web.routers_auth import router as auth_router
from tripagent.web.routers_ops import router as ops_router
from tripagent.web.routers_pages import router as pages_router
from tripagent.web.routers_places import router as places_router
from tripagent.web.routers_plan import router as plan_router

async def lifespan(app: FastAPI):
    if INDEX_HTML.exists():
        print(f"\nUI HTML found at {INDEX_HTML}")
    else:
        print(f"\nUI HTML not found at {INDEX_HTML}")
    print("    -> http://localhost:8000/      <- UI")
    print("    -> http://localhost:8000/docs  <- Swagger\n")
    yield


app = FastAPI(
    title="TripAgent API",
    version="0.2.0",
    description="Urban itinerary optimizer with guardrails",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

settings = get_settings()
allowed_origins = list(settings.cors_allowed_origins) or [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
allow_credentials = "*" not in allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

install_metrics_middleware(app)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(health_router)
app.include_router(pages_router)
app.include_router(ops_router)
app.include_router(auth_router)
app.include_router(places_router)
app.include_router(plan_router)