import json
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, TypeAlias

from websockets import WebSocketServerProtocol

ClientConnections: TypeAlias = Dict[int, "ClientConnection"]


@dataclass
class ClientConnection:
    player_num: int
    websocket: WebSocketServerProtocol
    last_message_recieved: str


@dataclass
class Position:
    x: int
    y: int


class Direction(Enum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3

    def to_client_str(self) -> str:
        match self.value:
            case 0:
                return "U"
            case 1:
                return "R"
            case 2:
                return "D"
            case 3:
                return "L"
            case _:
                raise RuntimeError("This should never happen")


@dataclass
class Player:
    connection: ClientConnection
    player_num: int
    position: Position
    direction: Direction
    bullet_position: Optional[Position]
    bullet_direction: Optional[Direction]

    def as_json(self) -> str:
        return json.dumps(
            {
                "id": self.player_num,
                "px": self.position.x,
                "py": self.position.y,
                "d": self.direction.to_client_str(),
                "bx": self.bullet_position.x if self.bullet_position else None,
                "by": self.bullet_position.y if self.bullet_position else None,
                "bd": self.bullet_direction.to_client_str() if self.bullet_direction else None,
            }
        )
