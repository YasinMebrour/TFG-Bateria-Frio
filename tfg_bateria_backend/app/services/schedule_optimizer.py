from __future__ import annotations

from datetime import datetime, date, time, timedelta
from itertools import combinations
from typing import Any, List, Sequence, Tuple

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import PreciosLuz, ScheduleOpt, ConfigTarifa, Peaje, Festivo  # type: ignore
from app.db.database import SessionLocal  # type: ignore

DEFAULT_MAX_SEGMENTS = 2
DEFAULT_MAX_HOURS = 6

Segment = Tuple[int, int]  # (hora_inicio, duracion_horas)

__all__ = [
    "save_optimal_schedule",
    "update_schedule_opt",
]

def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value).date()
    raise TypeError(value)

def _day_type(d: date, festivos: set[date]) -> str:
    if d in festivos:
        return "holiday"
    if d.weekday() >= 5:
        return "weekend"
    return "weekday"

def _compute_worst_segments(prices: Sequence[float], max_segments: int, max_hours: int) -> List[Segment]:
    worst_cost = float("-inf")
    worst_combo: Tuple[int, ...] | None = None

    for combo in combinations(range(24), max_hours):
        segments = 1
        for i in range(1, len(combo)):
            if combo[i] != combo[i - 1] + 1:
                segments += 1
        if segments > max_segments:
            continue
        cost = sum(prices[h] for h in combo)
        if cost > worst_cost:
            worst_cost = cost
            worst_combo = combo

    if worst_combo is None:
        return []

    segments_out: List[Segment] = []
    start = worst_combo[0]
    prev = start
    for h in worst_combo[1:]:
        if h == prev + 1:
            prev = h
        else:
            segments_out.append((start, prev - start + 1))
            start = h
            prev = h
    segments_out.append((start, prev - start + 1))
    return segments_out

def save_optimal_schedule(
    session: Session,
    target_date: date,
    *,
    max_segments: int = DEFAULT_MAX_SEGMENTS,
    max_hours: int = DEFAULT_MAX_HOURS,
) -> None:
    start_dt = datetime.combine(target_date, time.min)
    end_dt = datetime.combine(target_date, time.max)

    precios_rows = session.execute(
        select(PreciosLuz)
        .where(PreciosLuz.hora >= start_dt, PreciosLuz.hora <= end_dt)
        .order_by(PreciosLuz.hora)
    ).scalars().all()
    if len(precios_rows) != 24:
        return
    precios_kwh = [r.kwh for r in precios_rows]

    festivos_rows = session.execute(select(Festivo.fecha)).scalars().all()
    tipo_dia = _day_type(target_date, set(festivos_rows))

    tarifas_rows = session.execute(
        select(ConfigTarifa.hour, ConfigTarifa.tarifa)
        .where(ConfigTarifa.month == target_date.month)
        .where(ConfigTarifa.day_type == tipo_dia)
    ).all()
    tarifas_dict = {h: t for h, t in tarifas_rows}

    peajes_rows = session.execute(select(Peaje)).scalars().all()
    peaje_dict = {p.nombre: p.peaje for p in peajes_rows}

    costes = []
    for h in range(24):
        precio = precios_kwh[h]
        tarifa = tarifas_dict.get(h, "P6")  # valor por defecto
        peaje = peaje_dict.get(tarifa, 0.0)
        costes.append(precio + peaje)

    segmentos = _compute_worst_segments(costes, max_segments=max_segments, max_hours=max_hours)
    if not segmentos:
        return

    session.query(ScheduleOpt).filter_by(date=target_date).delete()
    for start_h, dur in segmentos:
        ini = start_dt + timedelta(hours=start_h)
        fin = ini + timedelta(hours=dur)
        session.add(ScheduleOpt(date=target_date, inicio_ahorro=ini, final_ahorro=fin))
    session.commit()

def update_schedule_opt(*, max_segments: int = DEFAULT_MAX_SEGMENTS, max_hours: int = DEFAULT_MAX_HOURS) -> None:
    session = SessionLocal()
    try:
        first_raw = session.query(func.date(func.min(PreciosLuz.hora))).scalar()
        last_raw = session.query(func.date(func.max(PreciosLuz.hora))).scalar()
        first_date = _to_date(first_raw)
        last_date = _to_date(last_raw)

        if not first_date or not last_date:
            print("[scheduleOpt] No hay datos de precios")
            return

        last_saved = _to_date(session.query(func.max(ScheduleOpt.date)).scalar())
        current = first_date if last_saved is None else last_saved + timedelta(days=1)

        while current <= last_date:
            save_optimal_schedule(session, current, max_segments=max_segments, max_hours=max_hours)
            current += timedelta(days=1)

        print(f"[scheduleOpt] Actualizado hasta {last_date}")
    finally:
        session.close()
