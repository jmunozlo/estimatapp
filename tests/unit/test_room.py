"""Tests para el modelo Room."""

from app.models import SCALES, Player, Room, RoomStatus, VotingMode


class TestRoom:
    """Tests para la clase Room."""

    def test_create_room_with_defaults(self):
        """Verifica que una sala se crea con valores por defecto."""
        room = Room(id="room1", name="Sprint Planning")

        assert room.id == "room1"
        assert room.name == "Sprint Planning"
        assert room.status == RoomStatus.VOTING
        assert room.voting_mode == VotingMode.PUBLIC
        assert room.voting_scale == "modified_fibonacci"
        assert room.story_name == ""
        assert len(room.players) == 0
        assert len(room.history) == 0

    def test_add_player(self, sample_room: Room, sample_player: Player):
        """Verifica que se puede agregar un jugador."""
        sample_room.add_player(sample_player)

        assert len(sample_room.players) == 1
        assert sample_player.id in sample_room.players

    def test_remove_player(self, sample_room: Room, sample_player: Player):
        """Verifica que se puede remover un jugador."""
        sample_room.add_player(sample_player)
        sample_room.remove_player(sample_player.id)

        assert len(sample_room.players) == 0

    def test_remove_nonexistent_player_does_not_raise(self, sample_room: Room):
        """Verifica que remover un jugador inexistente no lanza error."""
        sample_room.remove_player("nonexistent")  # No debería lanzar excepción

    def test_get_player(self, sample_room: Room, sample_player: Player):
        """Verifica que se puede obtener un jugador por ID."""
        sample_room.add_player(sample_player)

        found = sample_room.get_player(sample_player.id)

        assert found is sample_player

    def test_get_player_returns_none_for_nonexistent(self, sample_room: Room):
        """Verifica que get_player retorna None para ID inexistente."""
        assert sample_room.get_player("nonexistent") is None

    def test_find_player_by_name(self, sample_room: Room, sample_player: Player):
        """Verifica que se puede buscar un jugador por nombre."""
        sample_room.add_player(sample_player)

        found = sample_room.find_player_by_name("John Doe")

        assert found is sample_player

    def test_find_player_by_name_case_insensitive(self, sample_room: Room, sample_player: Player):
        """Verifica que la búsqueda por nombre es case-insensitive."""
        sample_room.add_player(sample_player)

        assert sample_room.find_player_by_name("john doe") is sample_player
        assert sample_room.find_player_by_name("JOHN DOE") is sample_player

    def test_get_facilitator(self, room_with_players: Room):
        """Verifica que se puede obtener el facilitador."""
        facilitator = room_with_players.get_facilitator()

        assert facilitator is not None
        assert facilitator.is_facilitator is True
        assert facilitator.name == "Alice"

    def test_get_facilitator_returns_none_when_no_facilitator(self, sample_room: Room):
        """Verifica que retorna None cuando no hay facilitador."""
        player = Player(id="p1", name="Regular", is_facilitator=False)
        sample_room.add_player(player)

        assert sample_room.get_facilitator() is None


class TestRoomVoting:
    """Tests para la funcionalidad de votación."""

    def test_all_voted_returns_false_when_no_players(self, sample_room: Room):
        """Verifica que all_voted retorna False sin jugadores."""
        assert sample_room.all_voted() is False

    def test_all_voted_returns_false_when_not_all_voted(self, room_with_players: Room):
        """Verifica que all_voted retorna False cuando no todos votaron."""
        room_with_players.players["p1"].vote = "5"
        # p2 y p3 no han votado

        assert room_with_players.all_voted() is False

    def test_all_voted_returns_true_when_all_voted(self, room_with_players: Room):
        """Verifica que all_voted retorna True cuando todos votaron."""
        # Solo jugadores activos (no observadores)
        room_with_players.players["p1"].vote = "5"
        room_with_players.players["p2"].vote = "8"
        room_with_players.players["p3"].vote = "3"

        assert room_with_players.all_voted() is True

    def test_all_voted_ignores_observers(self, room_with_players: Room):
        """Verifica que all_voted ignora a los observadores."""
        room_with_players.players["p1"].vote = "5"
        room_with_players.players["p2"].vote = "8"
        room_with_players.players["p3"].vote = "3"
        # p4 es observador, no necesita votar

        assert room_with_players.all_voted() is True

    def test_all_voted_ignores_disconnected_players(self, room_with_players: Room):
        """Verifica que all_voted ignora a jugadores desconectados."""
        room_with_players.players["p1"].vote = "5"
        room_with_players.players["p2"].vote = "8"
        room_with_players.players["p3"].connected = False  # Desconectado

        assert room_with_players.all_voted() is True

    def test_reveal_votes_changes_status(self, sample_room: Room):
        """Verifica que reveal_votes cambia el estado a REVEALED."""
        sample_room.reveal_votes()

        assert sample_room.status == RoomStatus.REVEALED

    def test_get_vote_summary_empty_when_voting(self, room_with_votes: Room):
        """Verifica que get_vote_summary está vacío durante votación."""
        # room_with_votes tiene status VOTING
        assert room_with_votes.get_vote_summary() == {}

    def test_get_vote_summary_after_reveal(self, revealed_room: Room):
        """Verifica el resumen de votos después de revelar."""
        summary = revealed_room.get_vote_summary()

        assert summary == {"5": 2, "8": 1}  # 2 votos de 5, 1 de 8

    def test_get_average_vote_returns_none_when_voting(self, room_with_votes: Room):
        """Verifica que get_average_vote retorna None durante votación."""
        assert room_with_votes.get_average_vote() is None

    def test_get_average_vote_after_reveal(self, revealed_room: Room):
        """Verifica el cálculo del promedio después de revelar."""
        average = revealed_room.get_average_vote()

        # (5 + 8 + 5) / 3 = 6.0
        assert average == 6.0

    def test_get_average_vote_ignores_non_numeric(self, revealed_room: Room):
        """Verifica que el promedio ignora votos no numéricos."""
        revealed_room.players["p1"].vote = "?"

        average = revealed_room.get_average_vote()

        # (8 + 5) / 2 = 6.5
        assert average == 6.5


class TestRoomScales:
    """Tests para las escalas de votación."""

    def test_get_current_scale_default(self, sample_room: Room):
        """Verifica la escala por defecto (modified_fibonacci)."""
        scale = sample_room.get_current_scale()

        assert scale == SCALES["modified_fibonacci"]

    def test_get_current_scale_fibonacci(self, sample_room: Room):
        """Verifica la escala Fibonacci."""
        sample_room.voting_scale = "fibonacci"

        assert sample_room.get_current_scale() == SCALES["fibonacci"]

    def test_get_current_scale_custom(self, sample_room: Room):
        """Verifica la escala personalizada."""
        sample_room.custom_scale = ["S", "M", "L"]

        assert sample_room.get_current_scale() == ["S", "M", "L"]

    def test_round_to_scale(self, sample_room: Room):
        """Verifica el redondeo a la escala."""
        sample_room.voting_scale = "modified_fibonacci"

        # 6.0 debería redondearse a 5 (más cercano)
        assert sample_room.round_to_scale(6.0) == "5"

        # 7.0 debería redondearse a 8
        assert sample_room.round_to_scale(7.0) == "8"

        # 0.3 debería redondearse a 0.5
        assert sample_room.round_to_scale(0.3) == "0.5"

    def test_round_to_scale_with_t_shirt(self, sample_room: Room):
        """Verifica que escalas no numéricas retornan None."""
        sample_room.voting_scale = "t_shirt"

        # T-shirt no tiene valores numéricos, debería retornar None
        assert sample_room.round_to_scale(5.0) is None


class TestRoomReset:
    """Tests para el reset de votos."""

    def test_reset_votes_clears_all_votes(self, room_with_votes: Room):
        """Verifica que reset_votes limpia todos los votos."""
        room_with_votes.reset_votes()

        for player in room_with_votes.players.values():
            assert player.vote is None

    def test_reset_votes_changes_status_to_voting(self, revealed_room: Room):
        """Verifica que reset_votes cambia el estado a VOTING."""
        revealed_room.reset_votes()

        assert revealed_room.status == RoomStatus.VOTING

    def test_reset_votes_clears_story_name(self, room_with_votes: Room):
        """Verifica que reset_votes limpia el nombre de la historia."""
        room_with_votes.reset_votes()

        assert room_with_votes.story_name == ""

    def test_reset_votes_saves_to_history(self, room_with_votes: Room):
        """Verifica que reset_votes guarda en el historial."""
        initial_history_len = len(room_with_votes.history)

        room_with_votes.reset_votes()

        assert len(room_with_votes.history) == initial_history_len + 1

    def test_reset_votes_history_contains_correct_data(self, room_with_votes: Room):
        """Verifica que el historial contiene los datos correctos."""
        room_with_votes.reset_votes()

        story = room_with_votes.history[0]

        assert story.story_name == "US-001: Login feature"
        assert story.votes == {"Alice": "5", "Bob": "8", "Charlie": "5"}
        assert story.vote_summary == {"5": 2, "8": 1}
        assert story.average == 6.0

    def test_reset_votes_does_not_save_empty_story(self, sample_room: Room):
        """Verifica que no se guarda historia sin nombre."""
        sample_room.reset_votes()

        assert len(sample_room.history) == 0


class TestRoomHistory:
    """Tests para el historial de votaciones."""

    def test_update_or_add_history_adds_new(self, sample_room: Room):
        """Verifica que se agrega nueva historia."""
        sample_room.update_or_add_history(
            story_name="US-001",
            votes={"Alice": "5"},
            vote_summary={"5": 1},
            average=5.0,
            rounded_average="5",
        )

        assert len(sample_room.history) == 1
        assert sample_room.history[0].story_name == "US-001"

    def test_update_or_add_history_updates_existing(self, sample_room: Room):
        """Verifica que se actualiza historia existente y solo una queda vigente."""
        sample_room.update_or_add_history(
            story_name="US-001",
            votes={"Alice": "5"},
            vote_summary={"5": 1},
            average=5.0,
            rounded_average="5",
        )

        # Actualizar la misma historia
        sample_room.update_or_add_history(
            story_name="US-001",
            votes={"Alice": "8", "Bob": "8"},
            vote_summary={"8": 2},
            average=8.0,
            rounded_average="8",
        )

        vigentes = [
            h for h in sample_room.history if h.story_name == "US-001" and not h.is_superseded
        ]
        assert len(vigentes) == 1
        assert vigentes[0].average == 8.0

    def test_get_total_story_points(self, sample_room: Room):
        """Verifica el cálculo del total de story points."""
        sample_room.update_or_add_history(
            story_name="US-001", votes={}, vote_summary={}, average=5.0, rounded_average="5"
        )
        sample_room.update_or_add_history(
            story_name="US-002", votes={}, vote_summary={}, average=8.0, rounded_average="8"
        )

        assert sample_room.get_total_story_points() == 13.0

    def test_get_total_story_points_ignores_non_numeric(self, sample_room: Room):
        """Verifica que ignora story points no numéricos."""
        sample_room.update_or_add_history(
            story_name="US-001", votes={}, vote_summary={}, average=None, rounded_average="?"
        )
        sample_room.update_or_add_history(
            story_name="US-002", votes={}, vote_summary={}, average=5.0, rounded_average="5"
        )

        assert sample_room.get_total_story_points() == 5.0

    def test_get_total_story_points_deduplicates(self, sample_room: Room):
        """Verifica que no cuenta historias duplicadas."""
        # Primera votación de US-001
        sample_room.update_or_add_history(
            story_name="US-001", votes={}, vote_summary={}, average=5.0, rounded_average="5"
        )
        # Re-votación de US-001 (debería actualizar, no duplicar)
        sample_room.update_or_add_history(
            story_name="US-001", votes={}, vote_summary={}, average=8.0, rounded_average="8"
        )

        # Solo debería contar 8, no 5+8
        assert sample_room.get_total_story_points() == 8.0


class TestVotingModes:
    """Tests para los modos de votación."""

    def test_default_mode_is_public(self, sample_room: Room):
        """Verifica que el modo por defecto es público."""
        assert sample_room.voting_mode == VotingMode.PUBLIC

    def test_can_set_anonymous_mode(self, sample_room: Room):
        """Verifica que se puede establecer modo anónimo."""
        sample_room.voting_mode = VotingMode.ANONYMOUS

        assert sample_room.voting_mode == VotingMode.ANONYMOUS
