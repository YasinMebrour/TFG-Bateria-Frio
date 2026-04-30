# app/config.py

"""Configuración centralizada del backend."""

import os
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# InfluxDB
# ---------------------------------------------------------------------------
INFLUX_URL = os.getenv("INFLUX_URL", "")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "")
INFLUX_BUCKET = [s.strip() for s in os.getenv("INFLUX_BUCKET", "").split(",") if s.strip()]
INFLUX_BUCKET_PRECIOS = os.getenv("INFLUX_BUCKET_PRECIOS", "TARIFF_PRICES")
INFLUX_BUCKET_CONSUMO = os.getenv("INFLUX_BUCKET_CONSUMO", "CAMARA_2")
BUCKET_INFLUX_CAMARA = os.getenv("BUCKET_INFLUX_CAMARA", "CAMARA_2")

# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------
def _build_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    postgres_password = os.getenv("POSTGRES_PASSWORD")
    if not postgres_password:
        raise RuntimeError("Set DATABASE_URL or POSTGRES_PASSWORD in the environment.")

    postgres_user = quote_plus(os.getenv("POSTGRES_USER", "myuser"))
    postgres_password = quote_plus(postgres_password)
    postgres_host = os.getenv("POSTGRES_HOST", "db")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = quote_plus(os.getenv("POSTGRES_DB", "mydb"))
    return (
        f"postgresql+psycopg2://{postgres_user}:{postgres_password}"
        f"@{postgres_host}:{postgres_port}/{postgres_db}"
    )


SQLALCHEMY_DATABASE_URL = _build_database_url()

# ---------------------------------------------------------------------------
# Redis & Celery
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_BACKEND_URL = os.getenv("CELERY_BACKEND_URL", REDIS_URL)

# ---------------------------------------------------------------------------
# Servicios externos
# ---------------------------------------------------------------------------
IA_URL = os.getenv(
    "IA_URL",
    "http://localhost:8001/consumo/prediccion",
)
NODE_RED_PLANIFICACION_URL = os.getenv(
    "NODE_RED_PLANIFICACION_URL", "http://192.168.96.1:1880/planificacion"
)
NODE_RED_ESTADO_CRITICO_URL = os.getenv(
    "NODE_RED_ESTADO_CRITICO_URL", "http://localhost:1880/estado_critico"
)

# ---------------------------------------------------------------------------
# Rutas y ficheros
# ---------------------------------------------------------------------------
DATASETS_DIR = BASE_DIR / "datasetscsv"
DATASETS_DIR_PRE = BASE_DIR / "predi"
DATASETS_DIR_TEMP_PERIODO = BASE_DIR / "temp_periodo"
DATASETS_DIR_LUZ_PREDI = BASE_DIR / "datasetscsv"
XGB_MODEL_PATH = BASE_DIR / "modelo_xgb_hybrid_1min.pkl"
NUM_LAGS = int(os.getenv("NUM_LAGS", "360"))

# ---------------------------------------------------------------------------
# Seguridad y correo electrónico
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("Set SECRET_KEY in the environment.")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else 587
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
