from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

@dataclass
class ClientConnection:
    socket: Any

@dataclass
class Position:
    x: int
    y: int

class Direction(Enum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3

@dataclass
class PlayerData:
    position: Position
    direction: Direction
    bullet_position: Optional[Position]
    bullet_direction: Optional[Position]
    last_key_press: Direction

@dataclass
class GameData:
    player_data: dict[int, PlayerData]
