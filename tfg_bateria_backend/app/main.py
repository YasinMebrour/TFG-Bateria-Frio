# app/main.py

"""Punto de entrada de la API del Gemelo Digital.
Se mantienen únicamente las dependencias necesarias y se agrupan
por bloques: estándar, terceros y locales.
"""

# ----------------------
# Imports
# ----------------------

# Standard Library
import os
import logging

# Third‑party
from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from fastapi.responses import HTMLResponse

from app.routes.authentication_routes import get_current_user

# Local
from .core.lifespan import lifespan
from .db.database import Base, engine
from .config import (
    DATASETS_DIR,
    DATASETS_DIR_PRE,
    DATASETS_DIR_TEMP_PERIODO,
    DATASETS_DIR_LUZ_PREDI,
)

# ----------------------
# Configuración inicial
# ----------------------

logging.basicConfig(level=logging.INFO)

# Crea tablas si no existen y levanta el esquema
Base.metadata.create_all(bind=engine)

# Instancia de aplicación
app = FastAPI(lifespan=lifespan)

# Seguridad
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ----------------------
# Middleware
# ----------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Ajusta en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------
# Constantes del proyecto (importadas de config)
# ----------------------

# ----------------------
# Endpoints base
# ----------------------

@app.get("/")
def root() -> dict[str, str]:
    """Endpoint de prueba para verificar el estado de la API."""
    return {"message": "API Digital Twin - funcionando"}

# ----------------------
# Routers
# ----------------------

# Importa todos los routers desde app.routes
from app import routes


# Registro de routers
for router in (
    routes.influxdb,
    routes.available_dates,
    routes.tariffs,
    routes.consumption,
    routes.users,
    routes.auth,
    routes.saving_config,
    routes.event_stream,
    routes.event_rules,
    routes.ws_planning,
    routes.planning,
    routes.pre_saving_band,
):
    app.include_router(router)


# Guardar sobre la tabla semanal
# app.include_router(plan_semanal)
# app.include_router(modo_ahorro)
# app.include_router(debug)
