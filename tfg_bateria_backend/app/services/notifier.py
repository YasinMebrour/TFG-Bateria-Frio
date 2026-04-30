# app/services/notifier.py  (nuevo)
from datetime import datetime
from sqlalchemy.orm import Session
from app.redis.publisher import publicar_evento
from app.services.telegram_service import send_telegram_message

def crear_y_emitir_evento(
    session: Session, *, tipo: str, descripcion: str, **extra: object
) -> None:
    """Crea un registro en BD y lo publica por Redis/WebSocket.

    Datos extra proporcionados se adjuntarán en el mensaje publicado.
    """
    from app.db.models import EventoCritico  # import local para no crear ciclos

    evt = EventoCritico(
        fecha=datetime.now(),
        tipo=tipo,
        descripcion=descripcion,
    )
    session.add(evt)
    session.commit()
    session.refresh(evt)

    evento_dict = {
        "id": evt.id,
        "fecha": evt.fecha.isoformat(timespec="seconds"),
        "tipo": evt.tipo,
        "descripcion": evt.descripcion,
    }
    if extra:
        evento_dict.update(extra)

    publicar_evento(evento_dict)

    # Notificar a usuarios por Telegram si lo tienen configurado
    from app.db.models import Usuario  # import local para evitar ciclos
    usuarios = (
        session.query(Usuario)
        .filter(Usuario.telegram_notify == True)  # noqa: E712
        .all()
    )
    mensaje = f"{evt.tipo}: {evt.descripcion or ''}".strip()
    for usr in usuarios:
        if usr.telegram_chat_id:
            send_telegram_message(usr.telegram_chat_id, mensaje, usr.telegram_bot_token or "")
