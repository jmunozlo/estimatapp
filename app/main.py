"""Aplicación principal FastAPI."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes import rooms_router, websocket_router

app = FastAPI(title="Scrum Poker", description="Aplicación de Planning Poker para equipos ágiles")

# Configurar archivos estáticos y templates
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

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
