from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.services.xgboost_inference import MODEL_PATH
from app.config import INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG
import os


__all__ = ["lifespan"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:

        # Verificaciones iniciales
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Modelo no encontrado en {MODEL_PATH}")
        if not all([INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG]):
            raise RuntimeError("Configuración de InfluxDB incompleta")
        yield

    finally:
        sched = getattr(app.state, "scheduler", None)
        if sched:
            sched.shutdown(wait=True)
            print("Scheduler detenido")
