"""Value Objects del dominio.

Los Value Objects son objetos inmutables que representan conceptos del dominio
y se comparan por su valor, no por su identidad.
"""

from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True)
class PlayerId:
    """Identificador único de un jugador."""

    value: str

    def __post_init__(self) -> None:
        """Valida que el ID no esté vacío."""
        if not self.value or not self.value.strip():
            msg = "El ID del jugador no puede estar vacío"
            raise ValueError(msg)

    def __str__(self) -> str:
        """Retorna el valor del ID."""
        return self.value


@dataclass(frozen=True)
class RoomId:
    """Identificador único de una sala."""

    value: str

    def __post_init__(self) -> None:
        """Valida que el ID no esté vacío."""
        if not self.value or not self.value.strip():
            msg = "El ID de la sala no puede estar vacío"
            raise ValueError(msg)

    def __str__(self) -> str:
        """Retorna el valor del ID."""
        return self.value


@dataclass(frozen=True)
class PlayerName:
    """Nombre de un jugador."""

    value: str
    MAX_LENGTH: int = 50

    def __post_init__(self) -> None:
        """Valida el nombre del jugador."""
        if not self.value or not self.value.strip():
            msg = "El nombre del jugador no puede estar vacío"
            raise ValueError(msg)
        if len(self.value) > self.MAX_LENGTH:
            msg = f"El nombre del jugador es demasiado largo (máximo {self.MAX_LENGTH} caracteres)"
            raise ValueError(msg)

    def __str__(self) -> str:
        """Retorna el valor del nombre."""
        return self.value

    @classmethod
    def create(cls, value: str) -> Self:
        """Crea un PlayerName con el valor normalizado."""
        return cls(value=value.strip())


@dataclass(frozen=True)
class RoomName:
    """Nombre de una sala."""

    value: str
    MAX_LENGTH: int = 100

    def __post_init__(self) -> None:
        """Valida el nombre de la sala."""
        if not self.value or not self.value.strip():
            msg = "El nombre de la sala no puede estar vacío"
            raise ValueError(msg)
        if len(self.value) > self.MAX_LENGTH:
            msg = f"El nombre de la sala es demasiado largo (máximo {self.MAX_LENGTH} caracteres)"
            raise ValueError(msg)

    def __str__(self) -> str:
        """Retorna el valor del nombre."""
        return self.value

    @classmethod
    def create(cls, value: str) -> Self:
        """Crea un RoomName con el valor normalizado."""
        return cls(value=value.strip())


@dataclass(frozen=True)
class StoryName:
    """Nombre de una historia de usuario."""

    value: str
    MAX_LENGTH: int = 200

    def __post_init__(self) -> None:
        """Valida el nombre de la historia."""
        if len(self.value) > self.MAX_LENGTH:
            msg = f"Historia muy larga (máximo {self.MAX_LENGTH} caracteres)"
            raise ValueError(msg)

    def __str__(self) -> str:
        """Retorna el valor del nombre."""
        return self.value

    @classmethod
    def create(cls, value: str) -> Self:
        """Crea un StoryName con el valor normalizado."""
        return cls(value=value.strip())

    @classmethod
    def empty(cls) -> Self:
        """Crea un StoryName vacío."""
        return cls(value="")

    def is_empty(self) -> bool:
        """Verifica si el nombre está vacío."""
        return not self.value


@dataclass(frozen=True)
class Vote:
    """Representa un voto en la estimación."""

    value: str | None

    def __str__(self) -> str:
        """Retorna el valor del voto."""
        return self.value or ""

    def is_empty(self) -> bool:
        """Verifica si el voto está vacío."""
        return self.value is None

    def is_numeric(self) -> bool:
        """Verifica si el voto es numérico."""
        if self.value is None:
            return False
        try:
            float(self.value)
            return True
        except ValueError:
            return False

    def to_float(self) -> float | None:
        """Convierte el voto a float si es numérico."""
        if self.value is None:
            return None
        try:
            return float(self.value)
        except ValueError:
            return None

    @classmethod
    def empty(cls) -> Self:
        """Crea un voto vacío."""
        return cls(value=None)

    @classmethod
    def create(cls, value: str | None) -> Self:
        """Crea un voto con el valor dado."""
        return cls(value=value)
