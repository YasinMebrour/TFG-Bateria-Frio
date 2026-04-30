"""Endpoints relacionados con tarifas, festivos y peajes.

Este módulo expone las rutas bajo el prefijo ``/tarifas`` para gestionar la
configuración de precios y la obtención de la tarifa aplicada a un día
determinado. También se encarga de lanzar la tarea de recalculo de la
planificación óptima cuando la configuración cambia.
"""

from datetime import datetime, timedelta, date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.routes.authentication_routes import get_current_user, get_current_admin
from app.db.models import Usuario

from app.tasks.task_ai import tarea_optima
from app.celery_app import celery_app

from redis import Redis
from celery.result import AsyncResult
from app.config import REDIS_URL

from app.db.database import get_db
from app.db.models import ConfigTarifa, Festivo, Peaje, Config
from app.db.schemas.tarifa import (               # importa tus Pydantic
    TarifasFestivos,
    BloqueTarifa,
    PeajeSchema,
    DiaTarifa,
)

router = APIRouter(
    prefix="/tarifas",
    tags=["tarifas"],
    dependencies=[Depends(get_current_user)]
)

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
REDIS_KEY = "tfg:last_task_opt"          # una única tarea global

# ────────────────────────────────────────────────────────────────
# POST /tarifas  
# ────────────────────────────────────────────────────────────────
@router.post("", status_code=204, summary="Sobrescribe tarifas, festivos y peajes")
def cargar_config_tarifas(
    payload: TarifasFestivos,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin)
):
    """Reemplaza tarifas, festivos y peajes y lanza un recálculo de la
    planificación óptima."""

    # Reemplazar tarifas
    db.query(ConfigTarifa).delete()
    db.bulk_save_objects([ConfigTarifa(**t.model_dump()) for t in payload.tarifas])

    # Reemplazar festivos
    db.query(Festivo).delete()
    fest_objs = [Festivo(fecha=f) for f in payload.festivos]
    db.bulk_save_objects(fest_objs)

    # Reemplazar peajes
    db.query(Peaje).delete()
    peaje_objs = [Peaje(**p.model_dump()) for p in (payload.peajes or [])]
    db.bulk_save_objects(peaje_objs)

    db.commit()

    cfg = db.query(Config).first()

    # ────────────────── 2. cancelar tarea previa (si existe) ─────────── #
    last_id = redis_client.get(REDIS_KEY)
    if last_id:
        AsyncResult(last_id, app=celery_app).revoke(terminate=True)

    # ────────────────── 3. preparar parámetros para la nueva tarea ───── #
    restricciones = {
        "total_hours"     : int(cfg.horas_modo_ahorro),
        "max_consecutive" : int(cfg.horas_max_ahorro),
        "min_gap"         : int(cfg.horas_max_entre_ahorro),
        "max_segments"    : int(cfg.rangos_ahorro),
    }

    # rango de fechas a planificar (hoy - hoy + n)
    first = date(2025, 1, 26)
    last = date.today() + timedelta(days=1)
    fechas = [(first + timedelta(days=i)).isoformat()
              for i in range((last - first).days + 1)]

    # ────────────────── 4. lanzar nueva tarea Celery ─────────────────── #
    async_result = tarea_optima.delay(fechas, restricciones)
    redis_client.set(REDIS_KEY, async_result.id)

    return cfg
    
# ────────────────────────────────────────────────────────────────
# GET /tarifas  
# ────────────────────────────────────────────────────────────────

@router.get("", response_model=TarifasFestivos, summary="Devuelve tarifas, festivos y peajes")
def get_tarifas_y_festivos(db: Session = Depends(get_db), _: Usuario = Depends(get_current_admin)):
    """Devuelve todas las tarifas, festivos y peajes configurados."""
    bloques      = db.query(ConfigTarifa).all()
    festivos_raw = db.query(Festivo).order_by(Festivo.fecha).all()
    peajes_raw   = db.query(Peaje).order_by(Peaje.nombre).all()

    if not bloques and not festivos_raw and not peajes_raw:
        raise HTTPException(status_code=404, detail="No hay datos configurados")

    tarifas = [
        BloqueTarifa(
            month=b.month,
            day_type=b.day_type,
            hour=b.hour,
            tarifa=b.tarifa,
        )
        for b in bloques
    ]
    festivos = [f.fecha for f in festivos_raw]
    peajes   = [PeajeSchema.from_orm(p) for p in peajes_raw]

    return TarifasFestivos(tarifas=tarifas, festivos=festivos, peajes=peajes)



# ────────────────────────────────────────────────────────────────
# GET /tarifas/dia  
# ────────────────────────────────────────────────────────────────
@router.get("/dia", response_model=DiaTarifa, summary="Tarifa horaria de un día")
def obtener_tarifas_dia(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Devuelve la tarifa horaria correspondiente a la fecha indicada."""
    try:
        d = datetime.fromisoformat(start_date).date()
    except ValueError as e:
        raise HTTPException(400, "Formato de fecha inválido") from e

    # determinar tipo de día
    if db.query(Festivo).filter_by(fecha=d).first():
        day_type = "holiday"
    elif d.weekday() >= 5:
        day_type = "weekend"
    else:
        day_type = "weekday"

    reglas = (
        db.query(ConfigTarifa)
        .filter(
            ConfigTarifa.day_type == day_type,
            (ConfigTarifa.month == d.month) | (ConfigTarifa.month.is_(None)),
        )
        .all()
    )
    if len(reglas) < 24:
        raise HTTPException(500, "Configuración de tarifas incompleta")

    tarifas_dia = [""] * 24
    for r in reglas:
        tarifas_dia[r.hour] = r.tarifa

    return DiaTarifa(date=start_date, tarifas=tarifas_dia)
