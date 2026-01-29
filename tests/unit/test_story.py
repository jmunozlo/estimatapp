"""Tests para la entidad StoryHistory del dominio."""

from datetime import datetime

from app.domain.entities.story import StoryHistory


class TestStoryHistory:
    """Tests para StoryHistory."""

    def test_create_story_history(self):
        """Verifica que se puede crear un StoryHistory."""
        story = StoryHistory(
            story_name="US-001: Login",
            votes={"Alice": "5", "Bob": "8"},
            vote_summary={"5": 1, "8": 1},
            average=6.5,
            rounded_average="5",
        )
        assert story.story_name == "US-001: Login"
        assert story.votes == {"Alice": "5", "Bob": "8"}
        assert story.vote_summary == {"5": 1, "8": 1}
        assert story.average == 6.5
        assert story.rounded_average == "5"
        assert isinstance(story.voted_at, datetime)

    def test_get_total_voters(self):
        """Verifica el conteo de votantes."""
        story = StoryHistory(
            story_name="US-001",
            votes={"Alice": "5", "Bob": "8", "Charlie": "3"},
            vote_summary={"5": 1, "8": 1, "3": 1},
            average=5.3,
            rounded_average="5",
        )
        assert story.get_total_voters() == 3

    def test_get_total_voters_empty(self):
        """Verifica el conteo de votantes cuando no hay votos."""
        story = StoryHistory(
            story_name="US-001",
            votes={},
            vote_summary={},
            average=None,
            rounded_average=None,
        )
        assert story.get_total_voters() == 0

    def test_get_consensus_when_all_same(self):
        """Verifica detección de consenso cuando todos votan igual."""
        story = StoryHistory(
            story_name="US-001",
            votes={"Alice": "5", "Bob": "5", "Charlie": "5"},
            vote_summary={"5": 3},
            average=5.0,
            rounded_average="5",
        )
        assert story.get_consensus() == "5"

    def test_get_consensus_when_different(self):
        """Verifica que no hay consenso con votos diferentes."""
        story = StoryHistory(
            story_name="US-001",
            votes={"Alice": "5", "Bob": "8"},
            vote_summary={"5": 1, "8": 1},
            average=6.5,
            rounded_average="5",
        )
        assert story.get_consensus() is None

    def test_get_consensus_when_empty(self):
        """Verifica que no hay consenso sin votos."""
        story = StoryHistory(
            story_name="US-001",
            votes={},
            vote_summary={},
            average=None,
            rounded_average=None,
        )
        assert story.get_consensus() is None

    def test_has_numeric_average_true(self):
        """Verifica detección de promedio numérico."""
        story = StoryHistory(
            story_name="US-001",
            votes={"Alice": "5"},
            vote_summary={"5": 1},
            average=5.0,
            rounded_average="5",
        )
        assert story.has_numeric_average() is True

    def test_has_numeric_average_false(self):
        """Verifica detección de ausencia de promedio numérico."""
        story = StoryHistory(
            story_name="US-001",
            votes={"Alice": "?"},
            vote_summary={"?": 1},
            average=None,
            rounded_average=None,
        )
        assert story.has_numeric_average() is False

    def test_to_dict_with_votes(self):
        """Verifica conversión a diccionario con votos."""
        story = StoryHistory(
            story_name="US-001",
            votes={"Alice": "5"},
            vote_summary={"5": 1},
            average=5.0,
            rounded_average="5",
        )
        result = story.to_dict(include_individual_votes=True)
        assert result["story_name"] == "US-001"
        assert result["votes"] == {"Alice": "5"}
        assert result["vote_summary"] == {"5": 1}
        assert result["average"] == 5.0
        assert result["rounded_average"] == "5"
        assert "voted_at" in result

    def test_to_dict_without_votes(self):
        """Verifica conversión a diccionario sin votos individuales."""
        story = StoryHistory(
            story_name="US-001",
            votes={"Alice": "5"},
            vote_summary={"5": 1},
            average=5.0,
            rounded_average="5",
        )
        result = story.to_dict(include_individual_votes=False)
        assert "votes" not in result
        assert result["vote_summary"] == {"5": 1}

    def test_create_factory(self):
        """Verifica el factory method create."""
        story = StoryHistory.create(
            story_name="US-001",
            votes={"Alice": "5"},
            vote_summary={"5": 1},
            average=5.0,
            rounded_average="5",
        )
        assert story.story_name == "US-001"
        assert story.average == 5.0
