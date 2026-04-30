"""Publish events to Redis for WebSocket consumers."""

import redis
import json
from app.config import REDIS_URL

def publicar_evento(evento_dict):
    """Publish ``evento_dict`` to the ``eventos_ws`` channel."""
    r = redis.Redis.from_url(REDIS_URL)
    r.publish("eventos_ws", json.dumps(evento_dict))
    # Mostrar el evento en la salida estándar del worker de Celery
    print(f"[Evento publicado] {evento_dict}")
