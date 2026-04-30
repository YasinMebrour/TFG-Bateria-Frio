"""Wrapper around the InfluxDB Python client."""
from influxdb_client import InfluxDBClient
from app.config import INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG

# Creamos el cliente global
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

def query_influx(query_str: str):
    """Ejecuta una consulta Flux en InfluxDB y retorna los resultados."""
    query_api = client.query_api()
    result = query_api.query(org=INFLUX_ORG, query=query_str)
    return result
