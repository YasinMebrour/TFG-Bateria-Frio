# app/config.py

import os
from dotenv import load_dotenv

load_dotenv()

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
# Convertir la cadena en lista, quitando espacios
INFLUX_BUCKET = [s.strip() for s in os.getenv("INFLUX_BUCKET", "").split(",") if s.strip()]
INFLUX_BUCKET_PRECIOS = os.getenv("INFLUX_BUCKET_PRECIOS")
INFLUX_BUCKET_CONSUMO = os.getenv("INFLUX_BUCKET_CONSUMO")
