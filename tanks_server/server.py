import asyncio
import functools
import json
from typing import Any

from websockets import Data, WebSocketServerProtocol, broadcast
from websockets.server import serve

from tanks_server.config import PORT, TICK_SECS
from tanks_server.game import Game, GameFull
from tanks_server.types import Direction

KEY_TO_DIR = {
    "R": Direction.RIGHT,
    "L": Direction.LEFT,
    "U": Direction.UP,
    "D": Direction.DOWN,
}


def valid_message(message: Data):
    return len(message.strip()) > 0


def debug_message(message: str) -> dict[str, Any]:
    return {
        "message": message,
        "type": "debug",
    }


async def listen_to_players(websocket: WebSocketServerProtocol, game: Game):
    try:
        player = game.add_new_player(websocket)
    except GameFull:
        await websocket.close(reason="Game Full!")
        return

    init_message = {
        "type": "init",
        "player_num": player.player_num,
        "num_players": game.num_players(),
    }
    await player.connection.websocket.send(json.dumps(init_message))

    try:
        async for message in websocket:
            if valid_message(message):
                assert isinstance(message, str), "Message should be a string"
                player.connection.last_message_recieved = message
                await websocket.send(json.dumps(debug_message("ACK")))
            else:
                print("Received invalid message!")
    finally:
        game.remove_player(player.player_num)


async def update_players(game: Game):
    while True:
        for player in game.players.values():
            last_key_pressed = player.connection.last_message_recieved.strip()[0]
            if last_key_pressed == "X":
                player.bullet_position = player.position
                player.bullet_direction = player.direction
            else:
                try:
                    player.direction = KEY_TO_DIR[last_key_pressed]
                except KeyError:
                    pass  # Ignore unknown value

        game.tick()

        update_message = f'{{"type": "frame", "state": {game.as_json()}}}'
        broadcast(game.get_client_websockets(), update_message)
        await asyncio.sleep(TICK_SECS)


async def main():
    game = Game(players={})
    listener = functools.partial(listen_to_players, game=game)
    updator = functools.partial(update_players, game=game)

    server = await serve(listener, "0.0.0.0", PORT)
    await asyncio.gather(server.wait_closed(), updator())


if __name__ == "__main__":
    asyncio.run(main())
