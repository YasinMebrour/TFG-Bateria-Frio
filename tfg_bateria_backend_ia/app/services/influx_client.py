# app/services/influx_client.py
import logging
from influxdb_client import InfluxDBClient
from app.config import INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG

logger = logging.getLogger(__name__)

# Cliente global de InfluxDB
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)


def query_influx(query: str):
    """Ejecuta una consulta Flux en InfluxDB y retorna los resultados."""
    query_api = client.query_api()
    return query_api.query(org=INFLUX_ORG, query=query)
