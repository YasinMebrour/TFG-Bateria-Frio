# app/tasks.py
from celery.result import AsyncResult
from app.celery_app import celery_app
import httpx, pendulum, pandas as pd
from datetime import date, timedelta, time, datetime
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import PrediccionXGBoost, PlanificacionDiaria, OrigenPlan
from app.jobs.schedule_opt import save_optimal_schedule, update_schedule_opt
from celery.utils.log import get_task_logger

from app.redis.publisher import publicar_evento
from app.services.notifier import crear_y_emitir_evento
from app.config import IA_URL


logger = get_task_logger(__name__)




@celery_app.task(bind=True)
def tarea_optima(self, fechas, restricciones):
    """
    Parámetros
    ----------
    fechas : list[str]
        Lista de fechas ISO-8601 (YYYY-MM-DD) sobre las que operar.
    restricciones : dict
        Restricciones para el algoritmo de optimización:
        total_hours, max_consecutive, min_gap, max_segments.
    """
    session: Session = SessionLocal()
    try:

        crear_y_emitir_evento(
            session,
            tipo="Recalculando plan Optimizado",
            descripcion="Peajes y Tarifas cambiados",
        )

        update_schedule_opt(recalcular_todo = True)

        crear_y_emitir_evento(
            session,
            tipo="Recalculando plan Optimizado",
            descripcion="Calculando consumo",
        )

        # ---------------------------------------------------------------------
        # FASE B ───── consumir el micro-servicio IA y guardar predicciones
        # ---------------------------------------------------------------------
        # Borra toda la tabla de predicciones
        session.query(PrediccionXGBoost).delete()
        session.commit()
        print("Tabla PrediccionXGBoost borrada completamente antes de regenerar")


        for dia_iso in sorted(fechas, reverse=True):
            dia = date.fromisoformat(dia_iso)

            print(f"Procesando día: {dia}")  # Esto se verá en stdout del worker

            # 1. Recuperar las franjas recién guardadas
            franjas = (
                session.query(PlanificacionDiaria)
                       .filter_by(fecha=dia, origen=OrigenPlan.opt)
                       .order_by(PlanificacionDiaria.hora_inicio)
                       .all()
            )
            if not franjas:
                print(f"[{dia}] Sin planificación, se omite") 
                continue  # no hay planificación → pasamos al siguiente día

            schedule = [
                {
                    "inicio_ahorro": f.hora_inicio.strftime("%H:%M"),
                    "final_ahorro" : f.hora_fin.strftime("%H:%M"),
                }
                for f in franjas
            ]

            payload = {
                "schedule"  : schedule,
                "start_date": pendulum.datetime(
                    dia.year, dia.month, dia.day, tz="Europe/Madrid"
                ).isoformat(),
            }

            timeout = httpx.Timeout(connect=5.0, read=400.0, write=30.0, pool=5.0)

            # 2. Llamada al servicio IA
            try:
                
                r = httpx.post(IA_URL, json=payload, timeout=timeout)
                r.raise_for_status()
                res = r.json()
            except Exception as exc:
                print(f"[{dia}] fallo IA: {exc}")
                continue

            # 3. Guardar la predicción
            df = pd.DataFrame(res["datasets"])
            if df.empty:
                continue

            df["hora"] = (
                pd.to_datetime(df["hora"])
                .dt.tz_localize("Europe/Madrid")
                .dt.tz_convert("UTC")
                .dt.tz_localize(None)
            )

            session.bulk_save_objects([
                PrediccionXGBoost(hora=row.hora, consumo=row.consumo)
                for row in df.itertuples(index=False)
            ])
            session.commit()

    finally:
        session.close()
        crear_y_emitir_evento(
            session,
            tipo="Recalculando plan Optimizado",
            descripcion="Consumo calculado",
        )


