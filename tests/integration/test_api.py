"""Tests de integración para la API REST."""

from httpx import AsyncClient


class TestRoomsAPI:
    """Tests para los endpoints de salas."""

    async def test_create_room_success(self, async_client: AsyncClient):
        """Verifica que se puede crear una sala."""
        response = await async_client.post("/api/rooms", json={"name": "Sprint Planning"})

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Sprint Planning"
        assert "id" in data
        assert data["status"] == "voting"
        assert data["player_count"] == 0

    async def test_create_room_empty_name_fails(self, async_client: AsyncClient):
        """Verifica que nombre vacío falla."""
        response = await async_client.post("/api/rooms", json={"name": "   "})

        assert response.status_code == 400

    async def test_create_room_long_name_fails(self, async_client: AsyncClient):
        """Verifica que nombre muy largo falla."""
        response = await async_client.post("/api/rooms", json={"name": "x" * 101})

        assert response.status_code == 400

    async def test_list_rooms_empty(self, async_client: AsyncClient):
        """Verifica lista vacía de salas."""
        response = await async_client.get("/api/rooms")

        assert response.status_code == 200
        assert response.json() == []

    async def test_list_rooms_with_rooms(self, async_client: AsyncClient):
        """Verifica lista de salas con salas creadas."""
        # Crear salas
        await async_client.post("/api/rooms", json={"name": "Room 1"})
        await async_client.post("/api/rooms", json={"name": "Room 2"})

        response = await async_client.get("/api/rooms")

        assert response.status_code == 200
        rooms = response.json()
        assert len(rooms) == 2

    async def test_get_room_success(self, async_client: AsyncClient):
        """Verifica obtener una sala específica."""
        # Crear sala
        create_response = await async_client.post("/api/rooms", json={"name": "Test Room"})
        room_id = create_response.json()["id"]

        response = await async_client.get(f"/api/rooms/{room_id}")

        assert response.status_code == 200
        assert response.json()["name"] == "Test Room"

    async def test_get_room_not_found(self, async_client: AsyncClient):
        """Verifica 404 para sala inexistente."""
        response = await async_client.get("/api/rooms/nonexistent")

        assert response.status_code == 404

    async def test_delete_room_success(self, async_client: AsyncClient):
        """Verifica que se puede eliminar una sala."""
        # Crear sala
        create_response = await async_client.post("/api/rooms", json={"name": "To Delete"})
        room_id = create_response.json()["id"]

        # Eliminar
        response = await async_client.delete(f"/api/rooms/{room_id}")

        assert response.status_code == 200

        # Verificar que ya no existe
        get_response = await async_client.get(f"/api/rooms/{room_id}")
        assert get_response.status_code == 404


class TestJoinRoomAPI:
    """Tests para unirse a una sala."""

    async def test_join_room_success(self, async_client: AsyncClient):
        """Verifica que un jugador puede unirse a una sala."""
        # Crear sala
        create_response = await async_client.post("/api/rooms", json={"name": "Test Room"})
        room_id = create_response.json()["id"]

        # Unirse
        response = await async_client.post(
            f"/api/rooms/{room_id}/join", json={"player_name": "John"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["room_id"] == room_id
        assert data["player_name"] == "John"
        assert "player_id" in data

    async def test_join_room_first_player_is_facilitator(self, async_client: AsyncClient):
        """Verifica que el primer jugador es facilitador."""
        # Crear sala
        create_response = await async_client.post("/api/rooms", json={"name": "Test Room"})
        room_id = create_response.json()["id"]

        # Unirse como primer jugador
        await async_client.post(f"/api/rooms/{room_id}/join", json={"player_name": "First"})

        # Verificar player_count
        room_response = await async_client.get(f"/api/rooms/{room_id}")
        assert room_response.json()["player_count"] == 1

    async def test_join_room_as_observer(self, async_client: AsyncClient):
        """Verifica unirse como observador."""
        # Crear sala
        create_response = await async_client.post("/api/rooms", json={"name": "Test Room"})
        room_id = create_response.json()["id"]

        # Unirse como observador
        response = await async_client.post(
            f"/api/rooms/{room_id}/join", json={"player_name": "Observer", "is_observer": True}
        )

        assert response.status_code == 200

    async def test_join_room_reconnection(self, async_client: AsyncClient):
        """Verifica reconexión con el mismo nombre."""
        # Crear sala
        create_response = await async_client.post("/api/rooms", json={"name": "Test Room"})
        room_id = create_response.json()["id"]

        # Primera conexión
        first_response = await async_client.post(
            f"/api/rooms/{room_id}/join", json={"player_name": "John"}
        )
        first_player_id = first_response.json()["player_id"]

        # Reconexión
        second_response = await async_client.post(
            f"/api/rooms/{room_id}/join", json={"player_name": "John"}
        )

        assert second_response.status_code == 200
        assert second_response.json()["player_id"] == first_player_id

    async def test_join_nonexistent_room_fails(self, async_client: AsyncClient):
        """Verifica que unirse a sala inexistente falla."""
        response = await async_client.post(
            "/api/rooms/nonexistent/join", json={"player_name": "John"}
        )

        assert response.status_code == 404

    async def test_join_room_empty_name_fails(self, async_client: AsyncClient):
        """Verifica que nombre vacío falla."""
        # Crear sala
        create_response = await async_client.post("/api/rooms", json={"name": "Test Room"})
        room_id = create_response.json()["id"]

        response = await async_client.post(
            f"/api/rooms/{room_id}/join", json={"player_name": "   "}
        )

        assert response.status_code == 400

    async def test_join_room_long_name_fails(self, async_client: AsyncClient):
        """Verifica que nombre muy largo falla."""
        # Crear sala
        create_response = await async_client.post("/api/rooms", json={"name": "Test Room"})
        room_id = create_response.json()["id"]

        response = await async_client.post(
            f"/api/rooms/{room_id}/join", json={"player_name": "x" * 51}
        )

        assert response.status_code == 400
