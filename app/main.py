"""Aplicación principal FastAPI."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.infrastructure.auth.jwt_validator import (
    JWKSValidator,
    create_auth_middleware,
)
from app.infrastructure.database.connection import close_pool, init_pool
from app.routes import rooms_router, websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize pool on startup, close on shutdown.

    Reads ``DATABASE_URL``, ``POOL_MIN_SIZE``, ``POOL_MAX_SIZE`` from env
    when ``REPOSITORY=postgres``.
    """
    repo_type = os.getenv("REPOSITORY", "inmemory").lower()
    if repo_type == "postgres":
        dsn = os.environ["DATABASE_URL"]
        min_size = int(os.getenv("POOL_MIN_SIZE", "5"))
        max_size = int(os.getenv("POOL_MAX_SIZE", "10"))
        await init_pool(dsn, min_size=min_size, max_size=max_size)

        # Set up JWT validator and middleware
        supabase_url = os.environ["SUPABASE_URL"]
        anon_key = os.environ["SUPABASE_ANON_KEY"]
        validator = JWKSValidator(supabase_url=supabase_url, anon_key=anon_key)

        # Access the app state to store validator for potential use elsewhere
        app.state.jwt_validator = validator

    yield

    if repo_type == "postgres":
        await close_pool()


app = FastAPI(
    title="Scrum Poker",
    description="Aplicación de Planning Poker para equipos ágiles",
    lifespan=lifespan,
)

# Configurar archivos estáticos y templates
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Registrar middlewares
# Auth middleware — protect POST/DELETE /api/rooms, skip /auth/*
# Only meaningful when REPOSITORY=postgres; for inmemory, creates a no-op validator
_supabase_url = os.getenv("SUPABASE_URL", "")
_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
if _supabase_url and _anon_key:
    _validator = JWKSValidator(supabase_url=_supabase_url, anon_key=_anon_key)
    app.middleware("http")(create_auth_middleware(_validator))

# Registrar rutas
app.include_router(rooms_router, prefix="/api", tags=["rooms"])
app.include_router(websocket_router, tags=["websocket"])


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Página principal."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/room/{room_id}", response_class=HTMLResponse)
async def room_page(request: Request, room_id: str) -> HTMLResponse:
    """Página de la sala de votación."""
    return templates.TemplateResponse("room.html", {"request": request, "room_id": room_id})


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
