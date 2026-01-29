"""Entidad StoryHistory del dominio."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StoryHistory:
    """Representa una historia votada con su historial.

    Esta entidad almacena el resultado de una votación completada.
    """

    story_name: str
    votes: dict[str, str]  # player_name -> vote_value
    vote_summary: dict[str, int]  # vote_value -> count
    average: float | None
    rounded_average: str | None
    voted_at: datetime = field(default_factory=datetime.now)

    def get_total_voters(self) -> int:
        """Obtiene el número total de votantes."""
        return len(self.votes)

    def get_consensus(self) -> str | None:
        """Obtiene el valor de consenso si todos votaron igual."""
        if not self.votes:
            return None
        unique_votes = set(self.votes.values())
        return next(iter(unique_votes)) if len(unique_votes) == 1 else None

    def has_numeric_average(self) -> bool:
        """Verifica si la historia tiene un promedio numérico."""
        return self.average is not None

    def to_dict(self, include_individual_votes: bool = True) -> dict:
        """Convierte la historia a un diccionario."""
        data = {
            "story_name": self.story_name,
            "vote_summary": self.vote_summary,
            "average": self.average,
            "rounded_average": self.rounded_average,
            "voted_at": self.voted_at.isoformat(),
        }
        if include_individual_votes:
            data["votes"] = self.votes
        return data

    @classmethod
    def create(
        cls,
        story_name: str,
        votes: dict[str, str],
        vote_summary: dict[str, int],
        average: float | None = None,
        rounded_average: str | None = None,
    ) -> "StoryHistory":
        """Factory method para crear un historial de historia."""
        return cls(
            story_name=story_name,
            votes=votes.copy(),
            vote_summary=vote_summary.copy(),
            average=average,
            rounded_average=rounded_average,
        )
