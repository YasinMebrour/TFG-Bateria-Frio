from __future__ import annotations

"""
scheduler_opt
=============

Planificación óptima diaria ajustada automáticamente a la zona horaria local
(España, "Europe/Madrid").

Restricciones leídas de la tabla ``Config`` para el **modo ahorro**:

* ``horas_modo_ahorro``          → **total** de horas a activar por día.
* ``horas_max_ahorro``           → máximo de **horas consecutivas** activas.
* ``horas_max_entre_ahorro``     → horas mínimas de **espera** entre dos
  bloques activos.
* ``rangos_ahorro``              → número máximo de **segmentos** (bloques) que
  se pueden activar en un mismo día.

Coste horario:
``coste = precio_spot_kwh * (1 + penalizacion_pct)``
"""

from datetime import date, datetime, time, timedelta
from itertools import combinations
from typing import Any, List, Sequence, Tuple
from zoneinfo import ZoneInfo
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.database import SessionLocal
from ..db.models import (
    Config,
    ConfigTarifa,
    Festivo,
    OrigenPlan,
    Peaje,
    PlanificacionDiaria,
)
from app.services.influx_service import get_prices_range_utc

# --------------------------------------------------------------------------- #
logger = logging.getLogger(__name__)
TZ_EUROPE_MADRID = ZoneInfo("Europe/Madrid")
Segment = Tuple[int, int]  # (hora_inicio, duracion_horas)
# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #

def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value).date()
    raise TypeError(f"Valor no convertible a fecha: {value!r}")


def _day_type(d: date, holidays: set[date]) -> str:
    if d in holidays:
        return "holiday"
    if d.weekday() >= 5:
        return "weekend"
    return "weekday"


# --------------------------------------------------------------------------- #
# Algoritmo bajo restricciones
# --------------------------------------------------------------------------- #

def _is_valid_combo(
    combo: Tuple[int, ...],
    *,
    max_consecutive: int,
    min_gap: int,
    max_segments: int,
) -> bool:
    """Comprueba si *combo* cumple todas las restricciones."""
    if not combo:
        return False

    segments = 1
    run = 1
    prev = combo[0]

    for h in combo[1:]:
        if h == prev + 1:           # sigue el bloque
            run += 1
            if run > max_consecutive:
                return False
        else:                       # se corta el bloque
            gap = h - prev - 1
            if gap < min_gap:
                return False
            segments += 1
            if segments > max_segments:
                return False
            run = 1
        prev = h

    return segments <= max_segments


def _combo_to_segments(combo: Tuple[int, ...]) -> List[Segment]:
    if not combo:
        return []
    segments: List[Segment] = []
    start = prev = combo[0]
    for h in combo[1:]:
        if h == prev + 1:
            prev = h
        else:
            segments.append((start, prev - start + 1))
            start = prev = h
    segments.append((start, prev - start + 1))
    return segments


def _compute_optimal_segments(
    prices: Sequence[float],
    *,
    total_hours: int,
    max_consecutive: int,
    min_gap: int,
    max_segments: int,
) -> List[Segment]:
    """Busca la combinación que maximiza el coste sujeta a las restricciones."""

    # Viabilidad rápida: límite teórico de bloques por min_gap y max_consecutive
    max_blocks_gap = (24 + min_gap) // (max_consecutive + min_gap)
    if max_segments < 1 or total_hours < 1:
        return []
    if total_hours > max_blocks_gap * max_consecutive or total_hours > max_segments * max_consecutive:
        return []

    best_cost = float("-inf")
    best_combo: Tuple[int, ...] | None = None

    for combo in combinations(range(24), total_hours):
        if not _is_valid_combo(
            combo,
            max_consecutive=max_consecutive,
            min_gap=min_gap,
            max_segments=max_segments,
        ):
            continue
        cost = sum(prices[h] for h in combo)
        if cost > best_cost:
            best_cost = cost
            best_combo = combo

    return _combo_to_segments(best_combo) if best_combo else []


# --------------------------------------------------------------------------- #
# Lógica principal
# --------------------------------------------------------------------------- #
def _get_local_day_prices(local_date: date, field: str) -> List[float]:
    local_midnight = datetime.combine(local_date, time.min, tzinfo=TZ_EUROPE_MADRID)
    utc_start = local_midnight.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    utc_stop = utc_start + timedelta(hours=24)
    return get_prices_range_utc(utc_start, utc_stop, field)

def save_optimal_schedule(
    session: Session,
    target_date: date,
    *,
    total_hours: int,
    max_consecutive: int,
    min_gap: int,
    max_segments: int,
) -> None:
    """Calcula y guarda la planificación óptima para *target_date*."""

    start_dt = datetime.combine(target_date, time.min)
    field = "predicted_kwh_price"

    # 1. Precios spot
    try:
        precios_kwh = _get_local_day_prices(target_date, field)
    except Exception as exc:  # noqa: BLE001
        logger.error("Error al obtener precios para %s: %s", target_date, exc)
        return

    # 2. Tipo de día
    holidays = set(session.execute(select(Festivo.fecha)).scalars().all())
    day_kind = _day_type(target_date, holidays)

    # 3. Tarifas por hora
    tarifas_by_hour = {
        h: t
        for h, t in session.execute(
            select(ConfigTarifa.hour, ConfigTarifa.tarifa)
            .where(ConfigTarifa.month == target_date.month)
            .where(ConfigTarifa.day_type == day_kind)
        ).all()
    }

    # 4. Penalización por tarifa
    pct_by_tarifa = {
        p.nombre: float(p.peaje) for p in session.execute(select(Peaje)).scalars()
    }

    # 5. Coste ponderado por hora
    costes = [
        precios_kwh[h] * (1 + pct_by_tarifa.get(tarifas_by_hour.get(h, "P6"), 0.0))
        for h in range(24)
    ]

    # 6. Selección óptima
    segments = _compute_optimal_segments(
        costes,
        total_hours=total_hours,
        max_consecutive=max_consecutive,
        min_gap=min_gap,
        max_segments=max_segments,
    )
    if not segments:
        logger.info("No se encontraron segmentos viables para %s", target_date)
        return

    # 7. Guardado en BD
    session.query(PlanificacionDiaria).filter_by(
        fecha=target_date,
        origen=OrigenPlan.opt,
    ).delete()

    for start_h, dur in segments:
        ini_dt = start_dt + timedelta(hours=start_h)
        fin_dt = start_dt + timedelta(hours=start_h + dur)
        if fin_dt.time() == time.min:
            fin_dt -= timedelta(minutes=1)
        session.add(
            PlanificacionDiaria(
                fecha=target_date,
                hora_inicio=ini_dt.time(),
                hora_fin=fin_dt.time(),
                origen=OrigenPlan.opt,
                modo_ahorro=True,
            )
        )
    session.commit()

def update_schedule_opt(*, recalcular_todo: bool = False) -> None:
    """Recalcula la planificación óptima usando los parámetros actuales."""

    session = SessionLocal()
    try:
        cfg: Config | None = session.query(Config).first()
        if not cfg:
            logger.warning("No hay registro Config; no se calcula planificación óptima")
            return

        total_hours = int(cfg.horas_modo_ahorro)
        max_consecutive = int(cfg.horas_max_ahorro)
        min_gap = int(cfg.horas_max_entre_ahorro)
        max_segments = int(cfg.rangos_ahorro)

        first_date = date(2025, 1, 26)
        last_date = date.today() + timedelta(days=1)

        current = first_date if recalcular_todo else (
            (_to_date(
                session.query(func.max(PlanificacionDiaria.fecha))
                .filter(PlanificacionDiaria.origen == OrigenPlan.opt)
                .scalar()
            ) or first_date - timedelta(days=1)) + timedelta(days=1)
        )

        while current <= last_date:
            save_optimal_schedule(
                session,
                current,
                total_hours=total_hours,
                max_consecutive=max_consecutive,
                min_gap=min_gap,
                max_segments=max_segments,
            )
            current += timedelta(days=1)
    finally:
        session.close()
