"""Scheduler configuration for periodic jobs."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


from app.jobs.node_red import job_enviar_planificacion_red, get_configuracion
from app.jobs.schedule_opt import update_schedule_opt
from app.jobs.save_planificador import update_schedule

from app.db.models import Config

from datetime import datetime


from app.db.database import SessionLocal


__all__ = ["build_scheduler"]

def build_scheduler() -> AsyncIOScheduler:
    """Create and configure the application's job scheduler."""

    scheduler = AsyncIOScheduler(timezone="Europe/Madrid")

    with SessionLocal() as db:
        _, hora_envio = get_configuracion(db)

    # Ejemplo: ejecutar cada día a las 02:30 UTC
    

    if hora_envio:
        scheduler.add_job(
            job_enviar_planificacion_red,
            trigger=CronTrigger(hour=hora_envio.hour, minute=hora_envio.minute, timezone="Europe/Madrid"),
            id="enviar_planificacion_red",
            replace_existing=True,
            misfire_grace_time=600,
            coalesce=True,
            max_instances=1,
        )
        print(f"[Scheduler] Planificado envío a Node-Red a las {hora_envio.hour:02d}:{hora_envio.minute:02d} (hora local)")

    else:
        print("[Scheduler] Aviso: 'hora_envio_planificacion' no está configurado. No se programará el envío.")

     # Job 1: Update schedule
    scheduler.add_job(
        update_schedule,
        trigger=IntervalTrigger(minutes=10, timezone="Europe/Madrid"),
        next_run_time=datetime.now(),
        id="actualizar_datos_base",
        replace_existing=True,
        misfire_grace_time=300,
        coalesce=True,
        max_instances=1,
    )
    print("[Scheduler] Job 'actualizar_datos_base' programado cada 10 minutos")

    cfg = db.query(Config).first()

    # Job 2: Update schedule (optimizaciones)
    scheduler.add_job(
        update_schedule_opt,
        trigger=IntervalTrigger(minutes=10, timezone="Europe/Madrid"),
        next_run_time=datetime.now(),
        id="actualizar_datos_opt",
        replace_existing=True,
        misfire_grace_time=300,
        coalesce=True,
        max_instances=1,
    )

    print("[Scheduler] Job 'actualizar_datos_opt' programado cada 10 minutos")
    
    return scheduler
