"""Tests para el RoomManager."""

from app.manager import RoomManager


class TestRoomManager:
    """Tests para la clase RoomManager."""

    def test_create_room(self, fresh_room_manager: RoomManager):
        """Verifica que se puede crear una sala."""
        room = fresh_room_manager.create_room("Sprint Planning")

        assert room.name == "Sprint Planning"
        assert room.id is not None
        assert len(room.id) == 8

    def test_create_room_generates_unique_ids(self, fresh_room_manager: RoomManager):
        """Verifica que cada sala tiene un ID único."""
        room1 = fresh_room_manager.create_room("Room 1")
        room2 = fresh_room_manager.create_room("Room 2")

        assert room1.id != room2.id

    def test_create_room_stores_in_rooms_dict(self, fresh_room_manager: RoomManager):
        """Verifica que la sala se almacena correctamente."""
        room = fresh_room_manager.create_room("Test Room")

        assert room.id in fresh_room_manager.rooms
        assert fresh_room_manager.rooms[room.id] is room

    def test_get_room_returns_existing_room(self, fresh_room_manager: RoomManager):
        """Verifica que se puede obtener una sala existente."""
        created = fresh_room_manager.create_room("Test")

        retrieved = fresh_room_manager.get_room(created.id)

        assert retrieved is created

    def test_get_room_returns_none_for_nonexistent(self, fresh_room_manager: RoomManager):
        """Verifica que retorna None para sala inexistente."""
        assert fresh_room_manager.get_room("nonexistent") is None

    def test_delete_room(self, fresh_room_manager: RoomManager):
        """Verifica que se puede eliminar una sala."""
        room = fresh_room_manager.create_room("To Delete")

        fresh_room_manager.delete_room(room.id)

        assert room.id not in fresh_room_manager.rooms

    def test_delete_nonexistent_room_does_not_raise(self, fresh_room_manager: RoomManager):
        """Verifica que eliminar sala inexistente no lanza error."""
        fresh_room_manager.delete_room("nonexistent")  # No debería lanzar

    def test_list_rooms_returns_all_rooms(self, fresh_room_manager: RoomManager):
        """Verifica que list_rooms retorna todas las salas."""
        room1 = fresh_room_manager.create_room("Room 1")
        room2 = fresh_room_manager.create_room("Room 2")
        room3 = fresh_room_manager.create_room("Room 3")

        rooms = fresh_room_manager.list_rooms()

        assert len(rooms) == 3
        assert room1 in rooms
        assert room2 in rooms
        assert room3 in rooms

    def test_list_rooms_returns_empty_when_no_rooms(self, fresh_room_manager: RoomManager):
        """Verifica que list_rooms retorna lista vacía sin salas."""
        rooms = fresh_room_manager.list_rooms()

        assert rooms == []

    def test_multiple_operations(self, fresh_room_manager: RoomManager):
        """Verifica múltiples operaciones en secuencia."""
        # Crear
        room1 = fresh_room_manager.create_room("Room 1")
        room2 = fresh_room_manager.create_room("Room 2")
        assert len(fresh_room_manager.list_rooms()) == 2

        # Eliminar
        fresh_room_manager.delete_room(room1.id)
        assert len(fresh_room_manager.list_rooms()) == 1

        # Verificar que la correcta fue eliminada
        assert fresh_room_manager.get_room(room1.id) is None
        assert fresh_room_manager.get_room(room2.id) is room2
