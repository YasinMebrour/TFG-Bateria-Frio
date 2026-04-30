"""Rutas para leer y guardar la configuración de modo ahorro."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from datetime import date, timedelta

from redis import Redis
from celery.result import AsyncResult
from app.config import REDIS_URL

from app.routes.authentication_routes import get_current_user, get_current_admin

from app.tasks.task_ai import tarea_optima
from app.celery_app import celery_app
from app.jobs.update_scheduler import update_scheduler

from app.db.database import get_db
from app.db.models import Config, Usuario
from app.db.schemas.config_banda import (
    ConfigBandaRead,
    ConfigBandaCreate,
)

router = APIRouter(prefix="/config", tags=["config"], dependencies=[Depends(get_current_user)])

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
REDIS_KEY = "tfg:last_task_opt"          # una única tarea global

@router.get("/", response_model=ConfigBandaRead)
def get_config(db: Session = Depends(get_db)):
    """Devuelve la configuración de modo ahorro si existe."""

    cfg = db.query(Config).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    return cfg

@router.post("/", response_model=ConfigBandaRead)
def create_or_update_config(
    payload: ConfigBandaCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin)        # solo admins
):
    """
    Guarda la nueva configuración de modo-ahorro y relanza
    la tarea de planificación óptima + IA en segundo plano.
    """

    # ────────────────── 1. guardar/actualizar Config ────────────────── #
    cfg = db.query(Config).first()
    if not cfg:
        cfg = Config(**payload.dict())
        db.add(cfg)
        old_time = None
        old_vals = {}
        restrictions_changed = True
    else:
        old_time = cfg.hora_envio_planificacion
        old_vals = {
            "horas_modo_ahorro"    : cfg.horas_modo_ahorro,
            "horas_max_ahorro"     : cfg.horas_max_ahorro,
            "horas_max_entre_ahorro": cfg.horas_max_entre_ahorro,
            "rangos_ahorro"        : cfg.rangos_ahorro,
        }
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(cfg, field, value)

        restrictions_changed = any(
            getattr(cfg, k) != old_vals[k] for k in old_vals
        )

    db.commit()
    db.refresh(cfg)

    changed_time = old_time != cfg.hora_envio_planificacion
    if changed_time:
        update_scheduler(request.app)

    if not restrictions_changed:
        return cfg

    # ────────────────── cancelar tarea previa (si existe) ─────────── #
    last_id = redis_client.get(REDIS_KEY)
    if last_id:
        AsyncResult(last_id, app=celery_app).revoke(terminate=True)

    # ────────────────── preparar parámetros para la nueva tarea ───── #
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

    # ────────────────── lanzar nueva tarea Celery ─────────────────── #
    async_result = tarea_optima.delay(fechas, restricciones)
    redis_client.set(REDIS_KEY, async_result.id)

    return cfg
