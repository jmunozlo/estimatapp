"""Rutas WebSocket para Scrum Poker."""

from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.manager import room_manager
from app.models import Player, Room, RoomStatus, VotingMode
from app.websocket import ws_manager

router = APIRouter()

# Constantes de validación
MAX_STORY_NAME_LENGTH = 200
MIN_SCALE_VALUES = 2


async def broadcast_room_state(room_id: str) -> None:
    """Envía el estado actual de la sala a todos los jugadores."""
    room = room_manager.get_room(room_id)
    if not room:
        return

    players_data = _build_players_data(room)
    history_data = _build_history_data(room)

    message: dict[str, Any] = {
        "type": "room_update",
        "data": {
            "room_id": room.id,
            "room_name": room.name,
            "status": room.status.value,
            "voting_mode": room.voting_mode.value,
            "voting_scale": room.voting_scale,
            "current_scale": room.get_current_scale(),
            "story_name": room.story_name,
            "players": players_data,
            "all_voted": room.all_voted(),
            "history": history_data,
            "total_story_points": room.get_total_story_points(),
        },
    }

    if room.status == RoomStatus.REVEALED:
        message["data"]["vote_summary"] = room.get_vote_summary()
        average = room.get_average_vote()
        message["data"]["average"] = average
        if average is not None:
            message["data"]["rounded_average"] = room.round_to_scale(average)

    await ws_manager.broadcast(room_id, message)


def _build_players_data(room: Room) -> list[dict[str, Any]]:
    """Construye la lista de datos de jugadores para el broadcast."""
    players_data = []
    for player in room.players.values():
        player_data = {
            "id": player.id,
            "name": player.name,
            "is_observer": player.is_observer,
            "is_facilitator": player.is_facilitator,
            "connected": player.connected,
            "has_voted": player.has_voted(),
        }
        if room.status == RoomStatus.REVEALED and player.vote:
            player_data["vote"] = player.vote
        players_data.append(player_data)
    return players_data


def _build_history_data(room: Room) -> list[dict[str, Any]]:
    """Construye la lista de historial para el broadcast."""
    history_data = []
    for story in room.history:
        history_item = {
            "story_name": story.story_name,
            "vote_summary": story.vote_summary,
            "average": story.average,
            "rounded_average": story.rounded_average,
            "voted_at": story.voted_at.isoformat(),
        }
        if room.voting_mode.value == "public":
            history_item["votes"] = story.votes
        history_data.append(history_item)
    return history_data


async def _handle_vote(
    websocket: WebSocket, room: Room, player: Player, data: dict[str, Any]
) -> None:
    """Maneja la acción de votar."""
    vote_value = data.get("vote")

    if vote_value is None:
        player.vote = None
        await broadcast_room_state(room.id)
        return

    current_scale = room.get_current_scale()
    if vote_value not in current_scale:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"Voto inválido: {vote_value} no está en la escala actual",
            }
        )
        return

    player.vote = vote_value
    await broadcast_room_state(room.id)


async def _handle_reveal(websocket: WebSocket, room: Room, player: Player) -> None:
    """Maneja la acción de revelar votos."""
    if not player.is_facilitator:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Solo el facilitador puede revelar los votos",
            }
        )
        return

    room.reveal_votes()
    await broadcast_room_state(room.id)


async def _handle_reset(websocket: WebSocket, room: Room, player: Player) -> None:
    """Maneja la acción de resetear votos."""
    if not player.is_facilitator:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Solo el facilitador puede iniciar una nueva ronda",
            }
        )
        return

    room.reset_votes()
    await broadcast_room_state(room.id)


async def _handle_set_story(websocket: WebSocket, room: Room, data: dict[str, Any]) -> None:
    """Maneja la acción de establecer nombre de historia."""
    story_name = data.get("story_name", "").strip()

    if len(story_name) > MAX_STORY_NAME_LENGTH:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"El nombre de la historia es demasiado largo "
                f"(máximo {MAX_STORY_NAME_LENGTH} caracteres)",
            }
        )
        return

    room.story_name = story_name
    await broadcast_room_state(room.id)


async def _handle_toggle_voting_mode(websocket: WebSocket, room: Room, player: Player) -> None:
    """Maneja el cambio de modo de votación."""
    if not player.is_facilitator:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Solo el facilitador puede cambiar el modo de votación",
            }
        )
        return

    if room.voting_mode == VotingMode.PUBLIC:
        room.voting_mode = VotingMode.ANONYMOUS
    else:
        room.voting_mode = VotingMode.PUBLIC

    await broadcast_room_state(room.id)


async def _handle_change_scale(
    websocket: WebSocket, room: Room, player: Player, data: dict[str, Any]
) -> None:
    """Maneja el cambio de escala de votación."""
    if not player.is_facilitator:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Solo el facilitador puede cambiar la escala de votación",
            }
        )
        return

    scale_name = data.get("scale")
    if scale_name:
        room.voting_scale = scale_name
        room.custom_scale = []
        await broadcast_room_state(room.id)


async def _handle_set_custom_scale(
    websocket: WebSocket, room: Room, player: Player, data: dict[str, Any]
) -> None:
    """Maneja la configuración de escala personalizada."""
    if not player.is_facilitator:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Solo el facilitador puede establecer una escala personalizada",
            }
        )
        return

    custom_values = data.get("values", [])

    if not custom_values or not isinstance(custom_values, list):
        await websocket.send_json(
            {
                "type": "error",
                "message": "La escala personalizada no puede estar vacía",
            }
        )
        return

    if len(custom_values) < MIN_SCALE_VALUES:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"La escala debe tener al menos {MIN_SCALE_VALUES} valores",
            }
        )
        return

    custom_values = [v.strip() for v in custom_values if v and str(v).strip()]

    if len(custom_values) < MIN_SCALE_VALUES:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"La escala debe tener al menos {MIN_SCALE_VALUES} valores",
            }
        )
        return

    room.custom_scale = custom_values
    room.voting_scale = "custom"
    await broadcast_room_state(room.id)


@router.websocket("/ws/{room_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_id: str) -> None:
    """Endpoint WebSocket para la comunicación en tiempo real."""
    room = room_manager.get_room(room_id)
    if not room:
        await websocket.close(code=1008, reason="Sala no encontrada")
        return

    player = room.get_player(player_id)
    if not player:
        await websocket.close(code=1008, reason="Jugador no encontrado")
        return

    await ws_manager.connect(websocket, room_id, player_id)
    player.connected = True

    try:
        await broadcast_room_state(room_id)

        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "vote":
                await _handle_vote(websocket, room, player, data)
            elif action == "reveal":
                await _handle_reveal(websocket, room, player)
            elif action == "reset":
                await _handle_reset(websocket, room, player)
            elif action == "set_story":
                await _handle_set_story(websocket, room, data)
            elif action == "toggle_voting_mode":
                await _handle_toggle_voting_mode(websocket, room, player)
            elif action == "change_scale":
                await _handle_change_scale(websocket, room, player, data)
            elif action == "set_custom_scale":
                await _handle_set_custom_scale(websocket, room, player, data)

    except WebSocketDisconnect:
        ws_manager.disconnect(room_id, player_id)
        player.connected = False
        await broadcast_room_state(room_id)
