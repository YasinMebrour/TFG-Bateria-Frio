# ws_planificacion.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status, HTTPException
from sqlalchemy.orm import Session
from typing import Set

from app.db.database import get_db
from app.routes.authentication_routes import get_current_user

router = APIRouter(prefix="/wsplanificacion")
connections: Set[WebSocket] = set()


async def _notify_all() -> None:
    """Envía 'planificacion_actualizada' a todas las conexiones vivas."""
    muertos = []
    for ws in connections:
        try:
            print("Enviando Ws")
            await ws.send_text("planificacion_actualizada")
        except WebSocketDisconnect:
            muertos.append(ws)
    for ws in muertos:
        connections.discard(ws)


@router.websocket("/ws/planificacion")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """Mantiene abierta la conexión para notificaciones de cambios."""
    db: Session = next(get_db())
    print("WS token crudo: %r", token)
    try:
        get_current_user(token, db)            # valida JWT
    except HTTPException as exc:
        # Usa logger si lo tienes configurado
        print(f"JWT rechazado: {exc.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        db.close()
        return

    await websocket.accept()
    connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()     # ping-pong pasivo
    except WebSocketDisconnect:
        pass
    finally:
        connections.discard(websocket)
        db.close()


async def notificar_cambio_planificacion() -> None:
    """API interna: avisa a todos los clientes de un cambio."""
    print("Notifiar")
    await _notify_all()
