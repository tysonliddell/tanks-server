import random
from dataclasses import dataclass
from datetime import datetime
from typing import Generator, Optional

from websockets import WebSocketServerProtocol

from tanks_server.config import (
    ARENA_HEIGHT,
    ARENA_WIDTH,
    BULLET_KILL_PROXIMITY,
    BULLET_SPEED,
    MAX_PLAYERS,
    PLAYER_SPEED,
    RESPAWN_SECONDS,
)
from tanks_server.types import ClientConnection, Direction, Player, Position


class GameFull(Exception):
    """Raised when someone tries to join a full game."""


@dataclass
class Game:
    players: dict[int, Player]

    def as_json(self) -> str:
        players_array = [self.players[i].as_json() if i in self.players else "null" for i in range(1, MAX_PLAYERS + 1)]
        return "[" + ",".join(players_array) + "]"

    def _next_free_player_slot(self) -> Optional[int]:
        try:
            return next(n for n in range(1, MAX_PLAYERS + 1) if n not in self.players)
        except StopIteration:
            return None

    def num_players(self) -> int:
        return len(self.players)

    def add_new_player(self, websocket: WebSocketServerProtocol) -> Player:
        player_num = self._next_free_player_slot()
        if player_num is None:
            raise GameFull

        connection = ClientConnection(player_num, websocket, None)
        player = Player(
            connection=connection,
            player_num=player_num,
            position=Position(x=0, y=0),
            direction=Direction.RIGHT,
            bullet_position=None,
            bullet_direction=None,
            is_dead=False,
            time_killed=None,
            seconds_until_respawn=None,
            score=0,
        )
        self.players[player_num] = player
        return player

    def get_client_websockets(self) -> Generator[WebSocketServerProtocol, None, None]:
        for player in self.players.values():
            yield player.connection.websocket

    def remove_player(self, player_num: int):
        del self.players[player_num]

    def move_player(self, player: Player):
        match player.direction:
            case Direction.LEFT:
                player.position.x -= PLAYER_SPEED
            case Direction.RIGHT:
                player.position.x += PLAYER_SPEED
            case Direction.UP:
                player.position.y -= PLAYER_SPEED
            case Direction.DOWN:
                player.position.y += PLAYER_SPEED

        player.position.x %= ARENA_WIDTH
        player.position.y %= ARENA_HEIGHT

    def move_bullet(self, player: Player):
        if not player.bullet_position:
            return

        match player.bullet_direction:
            case Direction.LEFT:
                player.bullet_position.x -= BULLET_SPEED
            case Direction.RIGHT:
                player.bullet_position.x += BULLET_SPEED
            case Direction.UP:
                player.bullet_position.y -= BULLET_SPEED
            case Direction.DOWN:
                player.bullet_position.y += BULLET_SPEED

        if (
            player.bullet_position.x < 0
            or player.bullet_position.x >= ARENA_WIDTH
            or player.bullet_position.y < 0
            or player.bullet_position.y >= ARENA_HEIGHT
        ):
            player.bullet_position = None
            player.bullet_direction = None

    def get_player_killer(self, player: Player) -> Optional[int]:
        other_players = [p for p in self.players.values() if p.player_num != player.player_num]

        for p in other_players:
            if p.bullet_position and p.bullet_position.l2_distance(player.position) < BULLET_KILL_PROXIMITY:
                return p.player_num

        return None

    def kill_player(self, dead_player: Player, killer: Player):
        dead_player.position = Position(random.randrange(0, ARENA_WIDTH), random.randrange(0, ARENA_HEIGHT))
        dead_player.bullet_position = None
        dead_player.bullet_direction = None
        dead_player.is_dead = True
        dead_player.time_killed = datetime.now()
        dead_player.seconds_until_respawn = float(RESPAWN_SECONDS)

        killer.score += 1

    def tick(self):
        now = datetime.now()
        dead_players = [p for p in self.players.values() if p.is_dead]
        alive_players = [p for p in self.players.values() if not p.is_dead]

        for player in dead_players:
            seconds_until_respawn = float(RESPAWN_SECONDS) - (now - player.time_killed).total_seconds()
            if seconds_until_respawn <= 0:
                player.seconds_until_respawn = None
                player.time_killed = None
                player.is_dead = False
            else:
                player.seconds_until_respawn = seconds_until_respawn

        for player in alive_players:
            self.move_player(player)
            self.move_bullet(player)
            killer_player_num = self.get_player_killer(player)
            if killer_player_num is not None:
                self.kill_player(player, self.players[killer_player_num])
