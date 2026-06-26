"""Shared test fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure import reset_room_repository
from app.main import app
from app.manager import RoomManager
from app.models import Player, Room


@pytest.fixture
async def fresh_room_manager() -> RoomManager:
    """Create a clean RoomManager for tests."""
    reset_room_repository()
    return RoomManager()


@pytest.fixture
def sample_room() -> Room:
    """Create a sample room for tests."""
    return Room(id="test123", name="Test Room")


@pytest.fixture
def sample_player() -> Player:
    """Create a sample player for tests."""
    return Player(id="player1", name="John Doe")


@pytest.fixture
def facilitator_player() -> Player:
    """Create a facilitator player for tests."""
    return Player(id="facilitator1", name="Facilitator", is_facilitator=True)


@pytest.fixture
def observer_player() -> Player:
    """Create an observer for tests."""
    return Player(id="observer1", name="Observer", is_observer=True)


@pytest.fixture
def room_with_players(sample_room: Room) -> Room:
    """Create a room with several players."""
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
    """Create a room with votes cast."""
    room_with_players.story_name = "US-001: Login feature"
    room_with_players.players["p1"].vote = "5"
    room_with_players.players["p2"].vote = "8"
    room_with_players.players["p3"].vote = "5"
    return room_with_players


@pytest.fixture
def revealed_room(room_with_votes: Room) -> Room:
    """Create a room with votes revealed."""
    room_with_votes.reveal_votes()
    return room_with_votes


@pytest.fixture(autouse=True)
async def clean_rooms():
    """Clean rooms before and after each test."""
    reset_room_repository()
    yield
    reset_room_repository()


@pytest.fixture
async def async_client():
    """Async HTTP client for API tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
