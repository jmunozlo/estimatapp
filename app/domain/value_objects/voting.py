"""Escalas de votación como Value Object."""

from dataclasses import dataclass, field
from typing import ClassVar, Self

# Escalas de votación predefinidas
PREDEFINED_SCALES: dict[str, list[str]] = {
    "fibonacci": ["0", "1", "2", "3", "5", "8", "13", "21", "34", "55", "89", "?", "☕"],
    "modified_fibonacci": [
        "0",
        "0.5",
        "1",
        "2",
        "3",
        "5",
        "8",
        "13",
        "20",
        "40",
        "100",
        "?",
        "☕",
    ],
    "powers_of_2": ["0", "1", "2", "4", "8", "16", "32", "64", "?", "☕"],
    "t_shirt": ["XXS", "XS", "S", "M", "L", "XL", "XXL", "?", "☕"],
    "linear": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "?", "☕"],
}


@dataclass(frozen=True)
class VotingScale:
    """Escala de votación para estimaciones.

    Puede ser una escala predefinida (fibonacci, t_shirt, etc.) o personalizada.
    """

    name: str
    values: tuple[str, ...]
    MIN_VALUES: ClassVar[int] = 2

    def __post_init__(self) -> None:
        """Valida la escala de votación."""
        if len(self.values) < self.MIN_VALUES:
            msg = f"La escala debe tener al menos {self.MIN_VALUES} valores"
            raise ValueError(msg)

    def contains(self, value: str) -> bool:
        """Verifica si un valor está en la escala."""
        return value in self.values

    def get_values(self) -> list[str]:
        """Retorna los valores de la escala como lista."""
        return list(self.values)

    def round_to_scale(self, value: float) -> str | None:
        """Redondea un valor al más cercano en la escala."""
        numeric_scale = []

        for item in self.values:
            try:
                numeric_scale.append((float(item), item))
            except ValueError:
                continue  # Ignora valores no numéricos

        if not numeric_scale:
            return None

        # Encuentra el valor más cercano
        closest = min(numeric_scale, key=lambda x: abs(x[0] - value))
        return closest[1]

    @classmethod
    def from_predefined(cls, name: str) -> Self:
        """Crea una escala desde las predefinidas."""
        if name not in PREDEFINED_SCALES:
            # Default a modified_fibonacci si no existe
            name = "modified_fibonacci"
        return cls(name=name, values=tuple(PREDEFINED_SCALES[name]))

    @classmethod
    def custom(cls, values: list[str]) -> Self:
        """Crea una escala personalizada."""
        # Limpiar valores
        clean_values = [v.strip() for v in values if v and str(v).strip()]
        return cls(name="custom", values=tuple(clean_values))

    @classmethod
    def default(cls) -> Self:
        """Retorna la escala por defecto (modified_fibonacci)."""
        return cls.from_predefined("modified_fibonacci")

    @classmethod
    def get_available_scales(cls) -> list[str]:
        """Retorna los nombres de las escalas disponibles."""
        return list(PREDEFINED_SCALES.keys())


@dataclass(frozen=True)
class VoteSummary:
    """Resumen de votos de una estimación."""

    votes: dict[str, str] = field(default_factory=dict)  # player_name -> vote_value
    vote_counts: dict[str, int] = field(default_factory=dict)  # vote_value -> count

    def __hash__(self) -> int:
        """Hace el objeto hasheable."""
        return hash(
            (
                tuple(sorted(self.votes.items())),
                tuple(sorted(self.vote_counts.items())),
            )
        )

    def get_average(self) -> float | None:
        """Calcula el promedio de los votos numéricos."""
        numeric_votes = []
        for vote_value in self.votes.values():
            try:
                numeric_votes.append(float(vote_value))
            except ValueError:
                continue  # Ignora votos no numéricos

        return sum(numeric_votes) / len(numeric_votes) if numeric_votes else None

    def has_votes(self) -> bool:
        """Verifica si hay votos."""
        return len(self.votes) > 0

    @classmethod
    def from_votes(cls, votes: dict[str, str]) -> Self:
        """Crea un resumen a partir de un diccionario de votos."""
        vote_counts: dict[str, int] = {}
        for vote_value in votes.values():
            vote_counts[vote_value] = vote_counts.get(vote_value, 0) + 1
        return cls(votes=votes, vote_counts=vote_counts)

    @classmethod
    def empty(cls) -> Self:
        """Crea un resumen vacío."""
        return cls()
