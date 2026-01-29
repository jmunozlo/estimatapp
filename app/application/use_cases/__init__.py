"""Application Use Cases."""

from app.application.use_cases.room_use_cases import (
    CreateRoomResult,
    CreateRoomUseCase,
    DeleteRoomUseCase,
    GetRoomUseCase,
    InvalidPlayerNameError,
    InvalidRoomNameError,
    JoinRoomResult,
    JoinRoomUseCase,
    ListRoomsUseCase,
    RoomFullError,
    RoomNotFoundError,
)
from app.application.use_cases.voting_use_cases import (
    ChangeScaleUseCase,
    InvalidScaleError,
    InvalidStoryNameError,
    InvalidVoteError,
    PlayerNotFoundError,
    ResetVotesUseCase,
    RevealVotesUseCase,
    SetStoryNameUseCase,
    ToggleVotingModeUseCase,
    UnauthorizedError,
    VoteResult,
    VoteUseCase,
)

__all__ = [
    "ChangeScaleUseCase",
    "CreateRoomResult",
    # Room Use Cases
    "CreateRoomUseCase",
    "DeleteRoomUseCase",
    "GetRoomUseCase",
    "InvalidPlayerNameError",
    "InvalidRoomNameError",
    "InvalidScaleError",
    "InvalidStoryNameError",
    "InvalidVoteError",
    "JoinRoomResult",
    "JoinRoomUseCase",
    "ListRoomsUseCase",
    "PlayerNotFoundError",
    "ResetVotesUseCase",
    "RevealVotesUseCase",
    "RoomFullError",
    # Errors
    "RoomNotFoundError",
    "SetStoryNameUseCase",
    "ToggleVotingModeUseCase",
    "UnauthorizedError",
    "VoteResult",
    # Voting Use Cases
    "VoteUseCase",
]
