"""Fixtures compartidas para tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure import reset_room_repository
from app.main import app
from app.manager import RoomManager
from app.models import Player, Room


@pytest.fixture
def fresh_room_manager() -> RoomManager:
    """Crea un RoomManager limpio para tests."""
    # Primero limpiamos el repositorio global
    reset_room_repository()
    return RoomManager()


@pytest.fixture
def sample_room() -> Room:
    """Crea una sala de ejemplo para tests."""
    return Room(id="test123", name="Test Room")


@pytest.fixture
def sample_player() -> Player:
    """Crea un jugador de ejemplo para tests."""
    return Player(id="player1", name="John Doe")


@pytest.fixture
def facilitator_player() -> Player:
    """Crea un jugador facilitador para tests."""
    return Player(id="facilitator1", name="Facilitator", is_facilitator=True)


@pytest.fixture
def observer_player() -> Player:
    """Crea un observador para tests."""
    return Player(id="observer1", name="Observer", is_observer=True)


@pytest.fixture
def room_with_players(sample_room: Room) -> Room:
    """Crea una sala con varios jugadores."""
    players = [
        Player(id="p1", name="Alice", is_facilitator=True),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie"),
        Player(id="p4", name="Observer", is_observer=True),
    ]
    for player in players:
        sample_room.add_player(player)
    return sample_room


@pytest.fixture
def room_with_votes(room_with_players: Room) -> Room:
    """Crea una sala con votos emitidos."""
    room_with_players.story_name = "US-001: Login feature"
    # Alice (facilitador) vota 5
    room_with_players.players["p1"].vote = "5"
    # Bob vota 8
    room_with_players.players["p2"].vote = "8"
    # Charlie vota 5
    room_with_players.players["p3"].vote = "5"
    # Observer no vota (es observador)
    return room_with_players


@pytest.fixture
def revealed_room(room_with_votes: Room) -> Room:
    """Crea una sala con votos revelados."""
    room_with_votes.reveal_votes()
    return room_with_votes


@pytest.fixture(autouse=True)
def clean_rooms():
    """Limpia las salas antes y después de cada test."""
    reset_room_repository()
    yield
    reset_room_repository()


@pytest.fixture
async def async_client():
    """Cliente HTTP asíncrono para tests de API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
