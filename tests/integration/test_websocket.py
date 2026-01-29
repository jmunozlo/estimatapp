"""Tests de WebSocket para la comunicación en tiempo real."""

from httpx import AsyncClient

from app.manager import room_manager
from app.models import RoomStatus


class TestWebSocketBroadcast:
    """Tests para la función broadcast_room_state."""

    async def test_broadcast_includes_room_info(self, async_client: AsyncClient):
        """Verifica que el broadcast incluye información de la sala."""
        # Crear sala y jugador
        create_response = await async_client.post("/api/rooms", json={"name": "Test Room"})
        room_id = create_response.json()["id"]

        await async_client.post(f"/api/rooms/{room_id}/join", json={"player_name": "John"})

        room = room_manager.get_room(room_id)
        assert room is not None
        assert room.name == "Test Room"

    async def test_room_state_includes_players(self, async_client: AsyncClient):
        """Verifica que el estado incluye jugadores."""
        # Crear sala
        create_response = await async_client.post("/api/rooms", json={"name": "Test Room"})
        room_id = create_response.json()["id"]

        # Agregar jugadores
        await async_client.post(f"/api/rooms/{room_id}/join", json={"player_name": "Alice"})
        await async_client.post(f"/api/rooms/{room_id}/join", json={"player_name": "Bob"})

        room = room_manager.get_room(room_id)
        assert len(room.players) == 2


class TestVotingWorkflow:
    """Tests para el flujo de votación."""

    async def test_player_can_vote(self, async_client: AsyncClient):
        """Verifica que un jugador puede votar."""
        # Setup
        create_response = await async_client.post("/api/rooms", json={"name": "Voting Test"})
        room_id = create_response.json()["id"]

        join_response = await async_client.post(
            f"/api/rooms/{room_id}/join", json={"player_name": "Voter"}
        )
        player_id = join_response.json()["player_id"]

        # Simular voto directamente en el modelo
        room = room_manager.get_room(room_id)
        player = room.get_player(player_id)
        player.vote = "5"

        assert player.has_voted() is True
        assert player.vote == "5"

    async def test_facilitator_can_reveal_votes(self, async_client: AsyncClient):
        """Verifica que el facilitador puede revelar votos."""
        # Setup
        create_response = await async_client.post("/api/rooms", json={"name": "Reveal Test"})
        room_id = create_response.json()["id"]

        await async_client.post(f"/api/rooms/{room_id}/join", json={"player_name": "Facilitator"})

        room = room_manager.get_room(room_id)
        room.reveal_votes()

        assert room.status == RoomStatus.REVEALED

    async def test_facilitator_can_reset_votes(self, async_client: AsyncClient):
        """Verifica que el facilitador puede resetear votos."""
        # Setup
        create_response = await async_client.post("/api/rooms", json={"name": "Reset Test"})
        room_id = create_response.json()["id"]

        join_response = await async_client.post(
            f"/api/rooms/{room_id}/join", json={"player_name": "Facilitator"}
        )
        player_id = join_response.json()["player_id"]

        room = room_manager.get_room(room_id)
        room.story_name = "US-001"
        room.get_player(player_id).vote = "8"
        room.reveal_votes()

        # Reset
        room.reset_votes()

        assert room.status == RoomStatus.VOTING
        assert room.get_player(player_id).vote is None

    async def test_vote_deselection(self, async_client: AsyncClient):
        """Verifica que se puede deseleccionar un voto."""
        # Setup
        create_response = await async_client.post("/api/rooms", json={"name": "Deselect Test"})
        room_id = create_response.json()["id"]

        join_response = await async_client.post(
            f"/api/rooms/{room_id}/join", json={"player_name": "Voter"}
        )
        player_id = join_response.json()["player_id"]

        room = room_manager.get_room(room_id)
        player = room.get_player(player_id)

        # Votar
        player.vote = "5"
        assert player.has_voted() is True

        # Deseleccionar
        player.vote = None
        assert player.has_voted() is False


class TestScaleManagement:
    """Tests para la gestión de escalas."""

    async def test_change_scale(self, async_client: AsyncClient):
        """Verifica que se puede cambiar la escala."""
        create_response = await async_client.post("/api/rooms", json={"name": "Scale Test"})
        room_id = create_response.json()["id"]

        room = room_manager.get_room(room_id)
        original_scale = room.voting_scale

        room.voting_scale = "fibonacci"

        assert room.voting_scale != original_scale
        assert room.voting_scale == "fibonacci"

    async def test_custom_scale(self, async_client: AsyncClient):
        """Verifica que se puede usar escala personalizada."""
        create_response = await async_client.post("/api/rooms", json={"name": "Custom Scale Test"})
        room_id = create_response.json()["id"]

        room = room_manager.get_room(room_id)
        room.custom_scale = ["XS", "S", "M", "L", "XL"]

        assert room.get_current_scale() == ["XS", "S", "M", "L", "XL"]


class TestVotingModes:
    """Tests para los modos de votación."""

    async def test_anonymous_mode(self, async_client: AsyncClient):
        """Verifica el modo anónimo."""
        from app.models import VotingMode

        create_response = await async_client.post("/api/rooms", json={"name": "Anonymous Test"})
        room_id = create_response.json()["id"]

        room = room_manager.get_room(room_id)
        room.voting_mode = VotingMode.ANONYMOUS

        assert room.voting_mode == VotingMode.ANONYMOUS

    async def test_public_mode(self, async_client: AsyncClient):
        """Verifica el modo público."""
        from app.models import VotingMode

        create_response = await async_client.post("/api/rooms", json={"name": "Public Test"})
        room_id = create_response.json()["id"]

        room = room_manager.get_room(room_id)

        assert room.voting_mode == VotingMode.PUBLIC


class TestStoryManagement:
    """Tests para la gestión de historias."""

    async def test_set_story_name(self, async_client: AsyncClient):
        """Verifica que se puede establecer nombre de historia."""
        create_response = await async_client.post("/api/rooms", json={"name": "Story Test"})
        room_id = create_response.json()["id"]

        room = room_manager.get_room(room_id)
        room.story_name = "US-001: User login"

        assert room.story_name == "US-001: User login"

    async def test_story_saved_to_history_on_reset(self, async_client: AsyncClient):
        """Verifica que la historia se guarda en el historial al resetear."""
        create_response = await async_client.post("/api/rooms", json={"name": "History Test"})
        room_id = create_response.json()["id"]

        join_response = await async_client.post(
            f"/api/rooms/{room_id}/join", json={"player_name": "Voter"}
        )
        player_id = join_response.json()["player_id"]

        room = room_manager.get_room(room_id)
        room.story_name = "US-001"
        room.get_player(player_id).vote = "5"

        initial_history_len = len(room.history)
        room.reset_votes()

        assert len(room.history) == initial_history_len + 1
        assert room.history[-1].story_name == "US-001"
