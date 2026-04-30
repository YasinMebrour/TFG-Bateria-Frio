"""Background task to forward Redis events to WebSocket clients."""

import asyncio
import redis.asyncio as aioredis
import json
from app.config import REDIS_URL

# Importa _clients desde donde lo tengas definido (rutas/eventos, etc)
from app.routes.event_stream_routes import _clients

async def ws_emitter_watcher():
    """Listen for Redis events and send them to active sockets."""
    r = aioredis.from_url(REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe("eventos_ws")
    print("[REDIS] Suscrito a eventos_ws")
    while True:
        try:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
            if message and message['type'] == 'message':
                evento = json.loads(message['data'])
                dead = []
                for ws in _clients:
                    try:
                        await ws.send_json([evento])
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    _clients.discard(ws)
        except Exception as e:
            print(f"[REDIS WS WATCHER ERROR]: {e}")
        await asyncio.sleep(0.1)
