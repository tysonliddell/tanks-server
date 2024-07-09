import asyncio
from typing import Dict
from websockets import Data, WebSocketServerProtocol
from websockets.server import serve

from tanks_server.types import Direction, GameData, PlayerData, Position

game_data = GameData(
    player_data={}
)

MAX_PLAYERS = 4
TICK_SECS = 1 / 10

last_player_move = {}

connections: Dict[int, WebSocketServerProtocol] = {}

def valid_message(message: Data):
    return len(message.strip()) > 0

async def listen_to_players(websocket: WebSocketServerProtocol):
    if len(connections) >= 4:
        await websocket.close(reason="Game Full!")
        return

    curr_players = [p_num for p_num in connections]
    player_num = next(n for n in range(1, MAX_PLAYERS+1) if n not in curr_players)
    connections[player_num] = websocket
    player_data = PlayerData(
        position=Position(0,0),
        direction=Direction.RIGHT,
        bullet_position=None,
        bullet_direction=None,
        last_key_press=Direction.RIGHT,
    )
    game_data.player_data[player_num] = player_data

    try:
        async for message in websocket:
            if valid_message(message):
                dir = message.strip()[0]
                player_data.direction = dir
                await websocket.send("Ack!")
            else:
                print("Received invalid message!")
    finally:
        del game_data.player_data[player_num]
        del connections[player_num]

async def update_players():
    while True:
        for connection in connections.values():
            await connection.send(str(game_data))
        await asyncio.sleep(TICK_SECS)

async def main():
    # async with serve(listen_to_players, "localhost", 8765):
    #     await asyncio.Future()  # run forever
    server = await serve(listen_to_players, "localhost", 8765)
    await asyncio.gather(server.wait_closed(), update_players())

if __name__ == "__main__":
    asyncio.run(main())