"""CRUD helpers for ``ModoAhorroIntervalo`` entries."""
from sqlalchemy.orm import Session
from datetime import date
from app.db.models import ModoAhorroIntervalo
from app.db.schemas.intervalo import DiaPlanificacionIn

def replace_date(db: Session, data: DiaPlanificacionIn):
    """Replace all intervals for the given date with ``data``."""
    # borrar lo existente
    db.query(ModoAhorroIntervalo).filter(
        ModoAhorroIntervalo.fecha == data.fecha
    ).delete()

    # insertar lo nuevo
    for itv in data.intervalos:
        db.add(ModoAhorroIntervalo(
            fecha      = data.fecha,
            start_time = itv.start_time,
            end_time   = itv.end_time
        ))
    db.commit()
    print("rows after commit:", db.query(ModoAhorroIntervalo)
                                     .filter(ModoAhorroIntervalo.fecha==data.fecha)
                                     .count())

def get_date(db: Session, fecha: date):
    """Return all intervals stored for ``fecha``."""
    rows = (
        db.query(ModoAhorroIntervalo)
        .filter(ModoAhorroIntervalo.fecha == fecha)
        .all()
    )
    return [
        {"start_time": r.start_time, "end_time": r.end_time}
        for r in rows
    ]
