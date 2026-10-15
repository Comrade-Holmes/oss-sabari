from fastapi.responses import RedirectResponse
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import db
from app.dependencies import get_current_user_optional

# --- Routers ---
from app.routers import (
    public,
    auth,
    dashboard,
    restaurants,
    dishes,
    ingredients,
    allergens,
)
from app.routers import graph as graph_router
from app.routers import allergy_checker as allergy_router
from app.routers import profile as profile_router
from app.routers import reports as reports_router
from app.routers import users as users_router
from app.routers import activity_logs as activity_logs_router

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("allergraph")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup + shutdown."""
    logger.info("AllerGraph starting up …")
    try:
        db.connect()
        logger.info("Neo4j connection established.")
    except Exception as exc:
        logger.error(f"Could not connect to Neo4j: {exc}")
    yield
    logger.info("AllerGraph shutting down …")
    db.close()


app = FastAPI(
    title=settings.APP_NAME,
    description="Food Allergy and Ingredient Intelligence Platform powered by Neo4j graph database.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# --- Middleware ---
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET,
    session_cookie="allergraph_session",
    max_age=86400 * 7,   # 7 days
    same_site="lax",
    https_only=False,    # set True in production behind HTTPS
)

# --- Static files & Templates ---
_HERE = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")
templates = Jinja2Templates(directory=str(_HERE / "templates"))


# --- Custom Exception Handlers ---
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Not found."}, status_code=404)
    return templates.TemplateResponse(
        "errors/404.html",
        {"request": request, "current_user": None},
        status_code=404,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error(f"Internal server error on {request.url}: {exc}")
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Internal server error."}, status_code=500)
    return templates.TemplateResponse(
        "errors/500.html",
        {"request": request, "current_user": None},
        status_code=500,
    )


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Forbidden."}, status_code=403)
    user = get_current_user_optional(request)
    if not user:
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)
    return templates.TemplateResponse(
        "errors/403.html",
        {"request": request, "current_user": user},
        status_code=403,
    )


# --- Register Routers ---
app.include_router(public.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(restaurants.router)
app.include_router(dishes.router)
app.include_router(ingredients.router)
app.include_router(allergens.router)
app.include_router(graph_router.router)
app.include_router(allergy_router.router)
app.include_router(profile_router.router)
app.include_router(reports_router.router)
app.include_router(users_router.router)
app.include_router(activity_logs_router.router)
