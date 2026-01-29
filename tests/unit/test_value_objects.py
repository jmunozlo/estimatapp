"""Tests para los Value Objects del dominio."""

import pytest

from app.domain.value_objects.identifiers import (
    PlayerId,
    PlayerName,
    RoomId,
    RoomName,
    StoryName,
    Vote,
)


class TestPlayerId:
    """Tests para PlayerId."""

    def test_create_valid_id(self):
        """Verifica que se puede crear un PlayerId válido."""
        player_id = PlayerId("p123")
        assert player_id.value == "p123"
        assert str(player_id) == "p123"

    def test_empty_id_raises_error(self):
        """Verifica que un ID vacío lanza error."""
        with pytest.raises(ValueError, match="no puede estar vacío"):
            PlayerId("")

    def test_whitespace_id_raises_error(self):
        """Verifica que un ID con solo espacios lanza error."""
        with pytest.raises(ValueError, match="no puede estar vacío"):
            PlayerId("   ")


class TestRoomId:
    """Tests para RoomId."""

    def test_create_valid_id(self):
        """Verifica que se puede crear un RoomId válido."""
        room_id = RoomId("room123")
        assert room_id.value == "room123"
        assert str(room_id) == "room123"

    def test_empty_id_raises_error(self):
        """Verifica que un ID vacío lanza error."""
        with pytest.raises(ValueError, match="no puede estar vacío"):
            RoomId("")

    def test_whitespace_id_raises_error(self):
        """Verifica que un ID con solo espacios lanza error."""
        with pytest.raises(ValueError, match="no puede estar vacío"):
            RoomId("   ")


class TestPlayerName:
    """Tests para PlayerName."""

    def test_create_valid_name(self):
        """Verifica que se puede crear un PlayerName válido."""
        name = PlayerName("John Doe")
        assert name.value == "John Doe"
        assert str(name) == "John Doe"

    def test_empty_name_raises_error(self):
        """Verifica que un nombre vacío lanza error."""
        with pytest.raises(ValueError, match="no puede estar vacío"):
            PlayerName("")

    def test_whitespace_name_raises_error(self):
        """Verifica que un nombre con solo espacios lanza error."""
        with pytest.raises(ValueError, match="no puede estar vacío"):
            PlayerName("   ")

    def test_too_long_name_raises_error(self):
        """Verifica que un nombre muy largo lanza error."""
        long_name = "A" * 51
        with pytest.raises(ValueError, match="demasiado largo"):
            PlayerName(long_name)

    def test_create_factory_strips_whitespace(self):
        """Verifica que create normaliza el nombre."""
        name = PlayerName.create("  John Doe  ")
        assert name.value == "John Doe"


class TestRoomName:
    """Tests para RoomName."""

    def test_create_valid_name(self):
        """Verifica que se puede crear un RoomName válido."""
        name = RoomName("Sprint Planning")
        assert name.value == "Sprint Planning"
        assert str(name) == "Sprint Planning"

    def test_empty_name_raises_error(self):
        """Verifica que un nombre vacío lanza error."""
        with pytest.raises(ValueError, match="no puede estar vacío"):
            RoomName("")

    def test_whitespace_name_raises_error(self):
        """Verifica que un nombre con solo espacios lanza error."""
        with pytest.raises(ValueError, match="no puede estar vacío"):
            RoomName("   ")

    def test_too_long_name_raises_error(self):
        """Verifica que un nombre muy largo lanza error."""
        long_name = "A" * 101
        with pytest.raises(ValueError, match="demasiado largo"):
            RoomName(long_name)

    def test_create_factory_strips_whitespace(self):
        """Verifica que create normaliza el nombre."""
        name = RoomName.create("  Sprint Planning  ")
        assert name.value == "Sprint Planning"


class TestStoryName:
    """Tests para StoryName."""

    def test_create_valid_name(self):
        """Verifica que se puede crear un StoryName válido."""
        name = StoryName("US-001: User login")
        assert name.value == "US-001: User login"
        assert str(name) == "US-001: User login"

    def test_empty_name_is_allowed(self):
        """Verifica que un nombre vacío es permitido."""
        name = StoryName("")
        assert name.value == ""
        assert name.is_empty() is True

    def test_too_long_name_raises_error(self):
        """Verifica que un nombre muy largo lanza error."""
        long_name = "A" * 201
        with pytest.raises(ValueError, match="muy larga"):
            StoryName(long_name)

    def test_create_factory_strips_whitespace(self):
        """Verifica que create normaliza el nombre."""
        name = StoryName.create("  US-001  ")
        assert name.value == "US-001"

    def test_empty_factory(self):
        """Verifica que empty crea un nombre vacío."""
        name = StoryName.empty()
        assert name.value == ""
        assert name.is_empty() is True

    def test_is_empty_returns_false_for_non_empty(self):
        """Verifica que is_empty retorna False para nombres no vacíos."""
        name = StoryName("US-001")
        assert name.is_empty() is False


class TestVote:
    """Tests para Vote."""

    def test_create_with_value(self):
        """Verifica que se puede crear un Vote con valor."""
        vote = Vote("5")
        assert vote.value == "5"
        assert str(vote) == "5"

    def test_create_empty(self):
        """Verifica que se puede crear un Vote vacío."""
        vote = Vote(None)
        assert vote.value is None
        assert str(vote) == ""

    def test_empty_factory(self):
        """Verifica que empty crea un voto vacío."""
        vote = Vote.empty()
        assert vote.value is None
        assert vote.is_empty() is True

    def test_create_factory(self):
        """Verifica que create funciona correctamente."""
        vote = Vote.create("8")
        assert vote.value == "8"

    def test_is_empty_returns_false_for_non_empty(self):
        """Verifica que is_empty retorna False para votos no vacíos."""
        vote = Vote("5")
        assert vote.is_empty() is False

    def test_is_numeric_for_integer(self):
        """Verifica que is_numeric detecta enteros."""
        vote = Vote("5")
        assert vote.is_numeric() is True

    def test_is_numeric_for_float(self):
        """Verifica que is_numeric detecta floats."""
        vote = Vote("0.5")
        assert vote.is_numeric() is True

    def test_is_numeric_for_non_numeric(self):
        """Verifica que is_numeric detecta no numéricos."""
        vote = Vote("?")
        assert vote.is_numeric() is False

    def test_is_numeric_for_empty(self):
        """Verifica que is_numeric retorna False para vacíos."""
        vote = Vote.empty()
        assert vote.is_numeric() is False

    def test_to_float_for_integer(self):
        """Verifica conversión a float de enteros."""
        vote = Vote("5")
        assert vote.to_float() == 5.0

    def test_to_float_for_float(self):
        """Verifica conversión a float de decimales."""
        vote = Vote("0.5")
        assert vote.to_float() == 0.5

    def test_to_float_for_non_numeric(self):
        """Verifica que to_float retorna None para no numéricos."""
        vote = Vote("?")
        assert vote.to_float() is None

    def test_to_float_for_empty(self):
        """Verifica que to_float retorna None para vacíos."""
        vote = Vote.empty()
        assert vote.to_float() is None
