"""Application lifespan utilities for startup and shutdown."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.orm import Session
from ..db.database import get_db, engine, Base, SessionLocal



from app.core.scheduler import build_scheduler


from sqlalchemy import func
from app.db.database import SessionLocal

from datetime import datetime, timedelta, timezone

from app.db.models import Config, PlanificacionDiaria, PlanificacionSemanal, UltimoEstado

from app.redis.ws_watcher import ws_emitter_watcher

#from app.jobs.ws_eventos import event_watcher
import asyncio


__all__ = ["lifespan"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application resources during startup and shutdown."""
    db = SessionLocal()
    try:

        engine = db.get_bind()
        #Config.__table__.drop(bind=engine, checkfirst=True)
        #UltimoEstado.__table__.drop(bind=engine, checkfirst=True)
        #Config.__table__.create(bind=engine, checkfirst=True)
        #UltimoEstado.__table__.create(bind=engine, checkfirst=True)

        
        # Scheduler
        scheduler = build_scheduler()
        if scheduler:  # Solo iniciar si existe
            scheduler.start(paused=False)
            app.state.scheduler = scheduler
            print(f"Scheduler activo con {len(scheduler.get_jobs())} trabajos")
        else:
            print("Scheduler no iniciado: configuración incompleta.")
        
        #app.state.watcher_task = asyncio.create_task(event_watcher())
        # Iniciar watcher Redis para WS
        app.state.redis_ws_task = asyncio.create_task(ws_emitter_watcher())

        yield

    finally:
        db.close()
        sched = getattr(app.state, "scheduler", None)
        if sched:
            sched.shutdown(wait=True)
            print("Scheduler detenido")
