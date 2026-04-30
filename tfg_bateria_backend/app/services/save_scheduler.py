"""save_scheduler.py — Volcado de intervalos *Modo Ahorro* → scheduleReal
==========================================================================
Detecta, para cada día, los tramos en los que **ModoAhorro.modo_ahorro == 1**
y los guarda en la tabla **scheduleReal**.  Pensado para ejecutarse en el
*startup* de tu servidor FastAPI; solo procesa los días aún no volcados.

Este archivo **ya no usa la columna `scheduler_name`**, porque tu modelo
`scheduleReal` incluye solo:
    id · date · inicio_ahorro · final_ahorro
"""

from __future__ import annotations

from datetime import datetime, date, time, timedelta
from typing import List, Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Modelos y factoría de sesiones del proyecto
# ---------------------------------------------------------------------------

from ..db.models import ModoAhorro, ScheduleReal  # tu tabla destino
from ..db.database import SessionLocal            # factoría de sesiones

__all__ = [
    "save_daily_schedule",
    "update_schedule",
]

# ---------------------------------------------------------------------------
# Utilidad interna: normalizar resultados de SQLite
# ---------------------------------------------------------------------------

def _to_date(value: Any) -> date | None:
    """Convierte *value* (date | str | None) → date o None.

    En SQLite, `func.date()` y `func.max()` devuelven strings ISO.
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value).date()
    raise TypeError(f"Valor no convertible a date: {value!r}")

# ---------------------------------------------------------------------------
# Función: save_daily_schedule
# ---------------------------------------------------------------------------

def save_daily_schedule(session: Session, target_date: date) -> None:
    """Detecta y guarda los tramos del día *target_date*.

    La función es **idempotente**: borra las filas existentes de ese día antes
    de insertar las nuevas.
    """

    start_dt = datetime.combine(target_date, time.min)
    end_dt   = datetime.combine(target_date, time.max)

    # Eventos del día -------------------------------------------------------
    events: List[ModoAhorro] = (
        session.execute(
            select(ModoAhorro)
            .where(ModoAhorro.hora >= start_dt, ModoAhorro.hora <= end_dt)
            .order_by(ModoAhorro.hora)
        ).scalars().all()
    )

    if not events:
        return

    # Limpieza previa (evita duplicar) -------------------------------------
    session.query(ScheduleReal).filter_by(date=target_date).delete()

    current_start = None

    for ev in events:
        estado = int(round(ev.modo_ahorro))
        if estado == 1 and current_start is None:
            current_start = ev.hora                   # 0 → 1
        elif estado == 0 and current_start is not None:
            _persist_interval(session, target_date, current_start, ev.hora)
            current_start = None                      # 1 → 0

    # Si el día termina en 1 ----------------------------------------------
    if current_start is not None:
        _persist_interval(session, target_date, current_start, end_dt)

    session.commit()

# ---------------------------------------------------------------------------
# Auxiliar: _persist_interval
# ---------------------------------------------------------------------------

def _persist_interval(
    session: Session,
    target_date: date,
    start_time: datetime,
    end_time: datetime,
) -> None:
    """Inserta un intervalo [*start_time*, *end_time*) en *scheduleReal*."""

    session.add(
        ScheduleReal(
            date=target_date,
            inicio_ahorro=start_time,
            final_ahorro=end_time,
        )
    )

# ---------------------------------------------------------------------------
# Función: update_schedule
# ---------------------------------------------------------------------------

def update_schedule() -> None:
    """Genera los intervalos en *scheduleReal* que aún falten.

    1. Determina el rango de fechas presente en *ModoAhorro*.
    2. Averigua la última fecha ya volcadas en *scheduleReal*.
    3. Procesa los días faltantes mediante `save_daily_schedule()`.
    """

    session: Session = SessionLocal()

    try:
        # Rango presente en ModoAhorro -------------------------------------
        first_modo_raw = session.query(func.date(func.min(ModoAhorro.hora))).scalar()
        last_modo_raw  = session.query(func.date(func.max(ModoAhorro.hora))).scalar()
        first_modo = _to_date(first_modo_raw)
        last_modo  = _to_date(last_modo_raw)

        if first_modo is None or last_modo is None:
            print("[scheduleReal] modo_ahorro vacío → nada que hacer")
            return

        # Última fecha en scheduleReal -------------------------------------
        last_sched_raw = session.query(func.max(ScheduleReal.date)).scalar()
        last_schedule  = _to_date(last_sched_raw)

        if last_schedule is not None and last_schedule >= last_modo:
            print(f"[scheduleReal] Ya actualizado hasta {last_schedule} → sin cambios")
            return

        # Primer día a procesar -------------------------------------------
        start_day = first_modo if last_schedule is None else last_schedule + timedelta(days=1)

        current = start_day
        while current <= last_modo:
            save_daily_schedule(session, current)
            current += timedelta(days=1)

        print("[scheduleReal] Actualizado hasta", last_modo)

    finally:
        session.close()