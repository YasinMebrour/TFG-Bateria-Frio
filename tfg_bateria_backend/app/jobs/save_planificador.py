"""
save_scheduler.py — Volcado de intervalos *Modo Ahorro* desde InfluxDB → PlanificacionDiaria
============================================================================================
Detecta, para cada día, los tramos en los que el campo `ahorro == 1`
(procedente del measurement `estados` dentro del bucket `CAMARA_2`)
y los guarda en la tabla **PlanificacionDiaria** con origen = OrigenPlan.real.

La rutina está pensada para lanzarse en el *startup* de tu servidor FastAPI;
procesa de forma idempotente desde la última fecha ya volcada.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo
from datetime import datetime, date, time, timedelta, timezone
from typing import List, Dict, Any

import logging

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Modelos y factoría de sesiones del proyecto
# ---------------------------------------------------------------------------

from ..db.models import PlanificacionDiaria, OrigenPlan
from ..db.database import SessionLocal
from app.services.influx_service import query_influx
from app.config import BUCKET_INFLUX_CAMARA

__all__ = [
    "save_daily_schedule",
    "update_schedule",
]

# ---------------------------------------------------------------------------
# Parámetros Influx ----------------------------------------------------------
# ---------------------------------------------------------------------------

BUCKET      = BUCKET_INFLUX_CAMARA
MEASUREMENT = "estados"
FIELD       = "ahorro"

# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _fetch_events(target_date: date) -> List[Dict[str, Any]]:
    """
    Devuelve los puntos de Influx para el día indicado.

    Cada punto es un dict con:
        {
            "time":   datetime en UTC,
            "value":  float | int | str
        }
    """
    start = datetime.combine(target_date, time.min, tzinfo=timezone.utc).isoformat()
    stop  = datetime.combine(target_date, time.max, tzinfo=timezone.utc).isoformat()

    flux = f'''
    from(bucket: "{BUCKET}")
      |> range(start: {start}, stop: {stop})
      |> timeShift(duration: 2h)
      |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
      |> filter(fn: (r) => r._field == "{FIELD}")
      |> keep(columns: ["_time", "_value"])
    '''

    try:
        result = query_influx(flux)
    except Exception:
        logging.exception("Error al consultar InfluxDB")
        return []

    events: List[Dict[str, Any]] = [
        {"time": record.get_time(), "value": record.get_value()}
        for table in result
        for record in table.records
    ]
    events.sort(key=lambda e: e["time"])
    return events


def _to_date(value: Any) -> date | None:
    """Convierte *value* (date | str | None) → date o None."""
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
    """Detecta y guarda los tramos del día *target_date* en PlanificacionDiaria."""
    events = _fetch_events(target_date)
    
    # Limpieza previa (evita duplicar)
    session.query(PlanificacionDiaria).filter(
        and_(
            PlanificacionDiaria.fecha == target_date,
            PlanificacionDiaria.origen == OrigenPlan.real
        )
    ).delete()

    if not events:                      # ← sin datos → sentinela ahorro OFF
        session.add(
            PlanificacionDiaria(
                fecha       = target_date,
                hora_inicio = None,
                hora_fin    = None,
                modo_ahorro = False,    #      AHORRO DESACTIVADO
                origen      = OrigenPlan.real,
            )
        )
        session.commit()
        logging.info("[PlanificacionDiaria] Sin datos para %s → nada que guardar", target_date)
        return


    current_start: datetime | None = None

    for ev in events:
        estado = int(round(ev["value"]))
        timestamp: datetime = ev["time"].replace(tzinfo=None)
        if estado == 1 and current_start is None:
            current_start = timestamp
        elif estado == 0 and current_start is not None:
            _persist_interval(session, target_date, current_start, timestamp)
            current_start = None

    # Si el día termina en estado 1, cierro el tramo
    if current_start is not None:
        # Para el día actual, cerrar hasta 'ahora'; para pasados, hasta 23:59:59
        now_local = datetime.now(ZoneInfo("Europe/Madrid")).replace(tzinfo=None)
        if target_date == now_local.date():
            end_time = now_local
        else:
            end_time = datetime.combine(target_date, time.max)
        _persist_interval(session, target_date, current_start, end_time)
    
    if current_start is None:
        # el día terminó con ahorro OFF → fila sentinela para que quede vacío
        session.add(
            PlanificacionDiaria(
                fecha       = target_date,
                hora_inicio = None,
                hora_fin    = None,
                modo_ahorro = False,
                origen      = OrigenPlan.real,
            )
        )

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
    """Inserta un intervalo [*start_time*, *end_time*) en PlanificacionDiaria."""
    session.add(
        PlanificacionDiaria(
            fecha=target_date,
            hora_inicio=start_time.time(),
            hora_fin=end_time.time(),
            modo_ahorro = True, 
            origen=OrigenPlan.real,
        )
    )


# ---------------------------------------------------------------------------
# Función: update_schedule
# ---------------------------------------------------------------------------

def update_schedule() -> None:
    """Genera los intervalos en *PlanificacionDiaria* desde la última fecha volcada."""
    # 1) Rango presente en Influx
    flux_first = f'''
    from(bucket: "{BUCKET}")
      |> range(start: -365d)
      |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
      |> filter(fn: (r) => r._field == "{FIELD}")
      |> first()
      |> keep(columns: ["_time"])
    '''
    flux_last = flux_first.replace("|> first()", "|> last()")

    first_dt = last_dt = None
    try:
        first_res = query_influx(flux_first)
        last_res  = query_influx(flux_last)
        if first_res and first_res[0].records:
            first_dt = first_res[0].records[0].get_time().date()
        if last_res and last_res[0].records:
            last_dt = last_res[0].records[0].get_time().date()
    except Exception:
        logging.exception("Error obteniendo rango de fechas desde Influx")
        return

    if first_dt is None or last_dt is None:
        logging.info("[PlanificacionDiaria] Influx sin datos → nada que hacer")
        return

    # 2) Recálculo desde la última fecha ya volcada
    session: Session = SessionLocal()
    try:
        last_sched_raw = (
            session.query(func.max(PlanificacionDiaria.fecha))
                   .filter(PlanificacionDiaria.origen == OrigenPlan.real)
                   .scalar()
        )
        last_schedule = _to_date(last_sched_raw)

        start_day = first_dt if last_schedule is None else last_schedule
        current = start_day
        while current <= last_dt:
            save_daily_schedule(session, current)
            current += timedelta(days=1)

        logging.info(
            "[PlanificacionDiaria] Recálculo completo desde %s hasta %s",
            start_day, last_dt
        )
    finally:
        session.close()
