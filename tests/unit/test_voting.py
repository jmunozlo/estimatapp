"""Tests para los Value Objects de votación."""

import pytest

from app.domain.value_objects.voting import (
    PREDEFINED_SCALES,
    VoteSummary,
    VotingScale,
)


class TestVotingScale:
    """Tests para VotingScale."""

    def test_create_with_valid_values(self):
        """Verifica creación con valores válidos."""
        scale = VotingScale(name="test", values=("1", "2", "3"))
        assert scale.name == "test"
        assert scale.values == ("1", "2", "3")

    def test_create_with_minimum_values(self):
        """Verifica creación con el mínimo de valores."""
        scale = VotingScale(name="test", values=("1", "2"))
        assert len(scale.values) == 2

    def test_create_with_too_few_values_raises_error(self):
        """Verifica que menos del mínimo de valores lanza error."""
        with pytest.raises(ValueError, match="al menos"):
            VotingScale(name="test", values=("1",))

    def test_contains_existing_value(self):
        """Verifica que contains detecta valores existentes."""
        scale = VotingScale(name="test", values=("1", "2", "3"))
        assert scale.contains("2") is True

    def test_contains_non_existing_value(self):
        """Verifica que contains detecta valores inexistentes."""
        scale = VotingScale(name="test", values=("1", "2", "3"))
        assert scale.contains("99") is False

    def test_get_values_returns_list(self):
        """Verifica que get_values retorna una lista."""
        scale = VotingScale(name="test", values=("1", "2", "3"))
        values = scale.get_values()
        assert isinstance(values, list)
        assert values == ["1", "2", "3"]

    def test_round_to_scale_exact_match(self):
        """Verifica redondeo con coincidencia exacta."""
        scale = VotingScale(name="test", values=("1", "2", "3", "5", "8"))
        assert scale.round_to_scale(5.0) == "5"

    def test_round_to_scale_closest(self):
        """Verifica redondeo al valor más cercano."""
        scale = VotingScale(name="test", values=("1", "2", "3", "5", "8"))
        assert scale.round_to_scale(4.2) == "5"  # Más cerca de 5 que de 3

    def test_round_to_scale_with_decimals(self):
        """Verifica redondeo con valores decimales."""
        scale = VotingScale(name="test", values=("0.5", "1", "2", "3"))
        assert scale.round_to_scale(0.3) == "0.5"

    def test_round_to_scale_non_numeric_scale(self):
        """Verifica que escala no numérica retorna None."""
        scale = VotingScale(name="test", values=("S", "M", "L", "XL"))
        assert scale.round_to_scale(5.0) is None

    def test_round_to_scale_mixed_scale(self):
        """Verifica redondeo con escala mixta (numéricos y no numéricos)."""
        scale = VotingScale(name="test", values=("1", "2", "3", "?", "☕"))
        assert scale.round_to_scale(2.8) == "3"

    def test_from_predefined_fibonacci(self):
        """Verifica creación desde escala predefinida."""
        scale = VotingScale.from_predefined("fibonacci")
        assert scale.name == "fibonacci"
        assert "1" in scale.values
        assert "?" in scale.values

    def test_from_predefined_unknown_defaults(self):
        """Verifica que escala desconocida usa modified_fibonacci."""
        scale = VotingScale.from_predefined("unknown_scale")
        assert scale.name == "modified_fibonacci"

    def test_custom_scale(self):
        """Verifica creación de escala personalizada."""
        scale = VotingScale.custom(["A", "B", "C"])
        assert scale.name == "custom"
        assert scale.values == ("A", "B", "C")

    def test_custom_scale_cleans_values(self):
        """Verifica que custom limpia valores."""
        scale = VotingScale.custom(["  A  ", "B", "  ", "C"])
        assert scale.values == ("A", "B", "C")

    def test_default_scale(self):
        """Verifica escala por defecto."""
        scale = VotingScale.default()
        assert scale.name == "modified_fibonacci"

    def test_get_available_scales(self):
        """Verifica lista de escalas disponibles."""
        scales = VotingScale.get_available_scales()
        assert "fibonacci" in scales
        assert "modified_fibonacci" in scales
        assert "t_shirt" in scales
        assert len(scales) == len(PREDEFINED_SCALES)


class TestVoteSummary:
    """Tests para VoteSummary."""

    def test_create_empty(self):
        """Verifica creación de resumen vacío."""
        summary = VoteSummary()
        assert summary.votes == {}
        assert summary.vote_counts == {}

    def test_empty_factory(self):
        """Verifica factory method empty."""
        summary = VoteSummary.empty()
        assert summary.votes == {}
        assert summary.has_votes() is False

    def test_from_votes(self):
        """Verifica creación desde diccionario de votos."""
        votes = {"Alice": "5", "Bob": "8", "Charlie": "5"}
        summary = VoteSummary.from_votes(votes)
        assert summary.votes == votes
        assert summary.vote_counts == {"5": 2, "8": 1}

    def test_has_votes_true(self):
        """Verifica has_votes con votos."""
        summary = VoteSummary.from_votes({"Alice": "5"})
        assert summary.has_votes() is True

    def test_has_votes_false(self):
        """Verifica has_votes sin votos."""
        summary = VoteSummary.empty()
        assert summary.has_votes() is False

    def test_get_average_numeric_votes(self):
        """Verifica cálculo de promedio con votos numéricos."""
        summary = VoteSummary.from_votes({"Alice": "5", "Bob": "8", "Charlie": "5"})
        # (5 + 8 + 5) / 3 = 6.0
        assert summary.get_average() == 6.0

    def test_get_average_mixed_votes(self):
        """Verifica promedio ignorando votos no numéricos."""
        summary = VoteSummary.from_votes({"Alice": "5", "Bob": "?", "Charlie": "8"})
        # (5 + 8) / 2 = 6.5
        assert summary.get_average() == 6.5

    def test_get_average_no_numeric_votes(self):
        """Verifica que promedio es None sin votos numéricos."""
        summary = VoteSummary.from_votes({"Alice": "?", "Bob": "☕"})
        assert summary.get_average() is None

    def test_get_average_empty(self):
        """Verifica que promedio es None sin votos."""
        summary = VoteSummary.empty()
        assert summary.get_average() is None

    def test_hash(self):
        """Verifica que VoteSummary es hasheable."""
        summary1 = VoteSummary.from_votes({"Alice": "5"})
        summary2 = VoteSummary.from_votes({"Alice": "5"})
        # Deben tener el mismo hash si tienen los mismos valores
        assert hash(summary1) == hash(summary2)

    def test_hash_different(self):
        """Verifica que resúmenes diferentes tienen hashes diferentes."""
        summary1 = VoteSummary.from_votes({"Alice": "5"})
        summary2 = VoteSummary.from_votes({"Alice": "8"})
        assert hash(summary1) != hash(summary2)
