"""Tests para el modelo Player."""

from app.domain.entities.player import Player, PlayerRole


class TestPlayer:
    """Tests para la clase Player."""

    def test_create_player_with_defaults(self):
        """Verifica que un jugador se crea con valores por defecto."""
        player = Player(id="p1", name="John")

        assert player.id == "p1"
        assert player.name == "John"
        assert player.is_observer is False
        assert player.is_facilitator is False
        assert player.vote is None
        assert player.connected is True

    def test_create_observer(self):
        """Verifica que se puede crear un observador."""
        player = Player(id="o1", name="Observer", is_observer=True)

        assert player.is_observer is True
        assert player.is_facilitator is False

    def test_create_facilitator(self):
        """Verifica que se puede crear un facilitador."""
        player = Player(id="f1", name="Facilitator", is_facilitator=True)

        assert player.is_facilitator is True
        assert player.is_observer is False

    def test_has_voted_returns_false_when_no_vote(self):
        """Verifica que has_voted retorna False sin voto."""
        player = Player(id="p1", name="John")

        assert player.has_voted() is False

    def test_has_voted_returns_true_when_voted(self):
        """Verifica que has_voted retorna True con voto."""
        player = Player(id="p1", name="John")
        player.vote = "5"

        assert player.has_voted() is True

    def test_reset_vote_clears_vote(self):
        """Verifica que reset_vote limpia el voto."""
        player = Player(id="p1", name="John")
        player.vote = "8"

        player.reset_vote()

        assert player.vote is None
        assert player.has_voted() is False

    def test_vote_can_be_any_string(self):
        """Verifica que el voto puede ser cualquier string."""
        player = Player(id="p1", name="John")

        # Voto numérico
        player.vote = "5"
        assert player.vote == "5"

        # Voto no numérico
        player.vote = "?"
        assert player.vote == "?"

        # T-shirt size
        player.vote = "XL"
        assert player.vote == "XL"

    def test_connected_state_changes(self):
        """Verifica que el estado de conexión puede cambiar."""
        player = Player(id="p1", name="John")

        assert player.connected is True
        player.connected = False
        assert player.connected is False


class TestPlayerDomainMethods:
    """Tests para los métodos del dominio de Player."""

    def test_set_vote(self):
        """Verifica que set_vote establece el voto."""
        player = Player(id="p1", name="John")
        player.set_vote("5")
        assert player.vote == "5"

    def test_set_vote_none(self):
        """Verifica que set_vote puede limpiar el voto."""
        player = Player(id="p1", name="John")
        player.set_vote("5")
        player.set_vote(None)
        assert player.vote is None

    def test_can_vote_regular_player(self):
        """Verifica que un jugador regular puede votar."""
        player = Player(id="p1", name="John")
        assert player.can_vote() is True

    def test_can_vote_observer_cannot(self):
        """Verifica que un observador no puede votar."""
        player = Player(id="p1", name="John", is_observer=True)
        assert player.can_vote() is False

    def test_can_vote_disconnected_cannot(self):
        """Verifica que un jugador desconectado no puede votar."""
        player = Player(id="p1", name="John")
        player.connected = False
        assert player.can_vote() is False

    def test_disconnect(self):
        """Verifica que disconnect marca al jugador como desconectado."""
        player = Player(id="p1", name="John")
        player.disconnect()
        assert player.connected is False

    def test_reconnect(self):
        """Verifica que reconnect marca al jugador como conectado."""
        player = Player(id="p1", name="John")
        player.disconnect()
        player.reconnect()
        assert player.connected is True

    def test_get_role_voter(self):
        """Verifica que get_role retorna VOTER para jugador regular."""
        player = Player(id="p1", name="John")
        assert player.get_role() == PlayerRole.VOTER

    def test_get_role_observer(self):
        """Verifica que get_role retorna OBSERVER para observador."""
        player = Player(id="p1", name="John", is_observer=True)
        assert player.get_role() == PlayerRole.OBSERVER

    def test_get_role_facilitator(self):
        """Verifica que get_role retorna FACILITATOR para facilitador."""
        player = Player(id="p1", name="John", is_facilitator=True)
        assert player.get_role() == PlayerRole.FACILITATOR

    def test_to_dict_basic(self):
        """Verifica conversión a diccionario sin voto."""
        player = Player(id="p1", name="John")
        result = player.to_dict()
        assert result["id"] == "p1"
        assert result["name"] == "John"
        assert result["is_observer"] is False
        assert result["is_facilitator"] is False
        assert result["connected"] is True
        assert result["has_voted"] is False
        assert "vote" not in result

    def test_to_dict_with_vote(self):
        """Verifica conversión a diccionario con voto."""
        player = Player(id="p1", name="John")
        player.vote = "5"
        result = player.to_dict(include_vote=True)
        assert result["vote"] == "5"

    def test_to_dict_with_vote_but_no_include(self):
        """Verifica que el voto no se incluye si include_vote=False."""
        player = Player(id="p1", name="John")
        player.vote = "5"
        result = player.to_dict(include_vote=False)
        assert "vote" not in result

    def test_create_factory(self):
        """Verifica el factory method create."""
        player = Player.create(
            player_id="p1",
            name="John",
            is_observer=False,
            is_facilitator=True,
        )
        assert player.id == "p1"
        assert player.name == "John"
        assert player.is_facilitator is True
