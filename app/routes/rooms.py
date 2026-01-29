"""Rutas para la gestión de salas."""

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.manager import room_manager
from app.models import Player

router = APIRouter()

# Constantes de validación
MAX_ROOM_NAME_LENGTH = 100
MAX_PLAYER_NAME_LENGTH = 50
MAX_PLAYERS_PER_ROOM = 20


class CreateRoomRequest(BaseModel):
    """Request para crear una sala."""

    name: str


class JoinRoomRequest(BaseModel):
    """Request para unirse a una sala."""

    player_name: str
    is_observer: bool = False


class RoomResponse(BaseModel):
    """Respuesta con información de la sala."""

    id: str
    name: str
    status: str
    player_count: int


class JoinRoomResponse(BaseModel):
    """Respuesta al unirse a una sala."""

    room_id: str
    player_id: str
    player_name: str


@router.post("/rooms", response_model=RoomResponse)
async def create_room(request: CreateRoomRequest) -> dict[str, Any]:
    """Crea una nueva sala de Scrum Poker."""
    # Validar nombre de sala
    room_name = request.name.strip()
    if not room_name:
        raise HTTPException(status_code=400, detail="El nombre de la sala no puede estar vacío")

    if len(room_name) > MAX_ROOM_NAME_LENGTH:
        raise HTTPException(
            status_code=400,
            detail="El nombre de la sala es demasiado largo (máximo 100 caracteres)",
        )

    room = room_manager.create_room(room_name)
    return {
        "id": room.id,
        "name": room.name,
        "status": room.status.value,
        "player_count": len(room.players),
    }


@router.get("/rooms", response_model=list[RoomResponse])
async def list_rooms() -> list[dict[str, Any]]:
    """Lista todas las salas activas."""
    rooms = room_manager.list_rooms()
    return [
        {
            "id": room.id,
            "name": room.name,
            "status": room.status.value,
            "player_count": len(room.players),
        }
        for room in rooms
    ]


@router.get("/rooms/{room_id}", response_model=RoomResponse)
async def get_room(room_id: str) -> dict[str, Any]:
    """Obtiene información de una sala específica."""
    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Sala no encontrada")

    return {
        "id": room.id,
        "name": room.name,
        "status": room.status.value,
        "player_count": len(room.players),
    }


@router.post("/rooms/{room_id}/join", response_model=JoinRoomResponse)
async def join_room(room_id: str, request: JoinRoomRequest) -> dict[str, str]:
    """Une un jugador a una sala con soporte para reconexión."""
    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Sala no encontrada")

    # Validar nombre de jugador
    player_name = request.player_name.strip()
    if not player_name:
        raise HTTPException(status_code=400, detail="El nombre del jugador no puede estar vacío")

    if len(player_name) > MAX_PLAYER_NAME_LENGTH:
        raise HTTPException(
            status_code=400,
            detail="El nombre del jugador es demasiado largo (máximo 50 caracteres)",
        )

    # Verificar si el jugador ya existe por nombre (reconexión)
    existing_player = room.find_player_by_name(player_name)

    if existing_player:
        # Reconectar jugador existente
        existing_player.connected = True
        existing_player.is_observer = request.is_observer  # Actualizar estado de observador
        return {
            "room_id": room_id,
            "player_id": existing_player.id,
            "player_name": existing_player.name,
        }

    # Verificar límite de jugadores
    if len(room.players) >= MAX_PLAYERS_PER_ROOM:
        raise HTTPException(
            status_code=400,
            detail=f"La sala está llena (máximo {MAX_PLAYERS_PER_ROOM} jugadores)",
        )

    # Crear nuevo jugador
    player_id = str(uuid4())[:8]
    is_facilitator = len(room.players) == 0  # El primer jugador es el facilitador

    player = Player(
        id=player_id,
        name=player_name,
        is_observer=request.is_observer,
        is_facilitator=is_facilitator,
    )
    room.add_player(player)

    return {
        "room_id": room_id,
        "player_id": player_id,
        "player_name": player.name,
    }


@router.delete("/rooms/{room_id}")
async def delete_room(room_id: str) -> dict[str, str]:
    """Elimina una sala."""
    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Sala no encontrada")

    room_manager.delete_room(room_id)
    return {"message": "Sala eliminada correctamente"}
