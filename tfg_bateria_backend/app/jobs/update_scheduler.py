"""Utilities to update APScheduler jobs at runtime."""

from fastapi import FastAPI
from apscheduler.triggers.cron import CronTrigger

from app.db.database import SessionLocal
from app.jobs.node_red import job_enviar_planificacion_red, get_configuracion

def update_scheduler(app: FastAPI):
    """Reload planning job configuration from the database."""
    scheduler = app.state.scheduler
    with SessionLocal() as db:
        _, hora_envio_planificacion = get_configuracion(db)

    if hora_envio_planificacion:
        print(f"[Scheduler] Reprogramando tarea a las {hora_envio_planificacion.hour}:{hora_envio_planificacion.minute}")
        job = scheduler.get_job("enviar_planificacion_red")
        if job:
            scheduler.remove_job("enviar_planificacion_red")
        scheduler.add_job(
            job_enviar_planificacion_red,
            trigger=CronTrigger(
                hour=hora_envio_planificacion.hour,
                minute=hora_envio_planificacion.minute
            ),
            id="enviar_planificacion_red",
            replace_existing=True,
            misfire_grace_time=600,
            coalesce=True,
            max_instances=1,
        )
