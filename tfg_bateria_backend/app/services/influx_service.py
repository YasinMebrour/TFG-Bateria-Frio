import logging
from typing import List, Dict, Any

import pendulum
from fastapi import HTTPException

from app.services.influx_client import query_influx


def _validate_and_format_time(time_str: str) -> str:
    """
    Recibe una cadena RFC 3339 (o relativa, p. ej. -24h / now())
    y la devuelve en formato RFC 3339 UTC.  Los valores relativos
    y now() se devuelven tal cual para que Flux los interprete.
    """
    if time_str in {"now()"} or time_str.startswith("-"):
        return time_str

    try:
        # Suponemos que el usuario pasa la fecha en su zona horaria local;
        # pendulum hará la conversión interna.
        dt = pendulum.parse(time_str, strict=True).in_timezone("UTC")
        return dt.to_rfc3339_string()          # termina en “Z”
    except pendulum.parsing.ParserError:
        raise HTTPException(
            400,
            detail=f"Fecha inválida: {time_str}. "
                   "Usa RFC 3339, p. ej. 2025-05-22T16:30:00+02:00"
        )


def get_data(
    bucket: str,
    measurement: str,
    field: str,
    start: str = "-24h",
    stop: str = "now()",
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Devuelve los valores de un field dentro de un measurement
    en el rango de tiempo indicado.
    """
    # Validación / normalización de fechas
    formatted_start = _validate_and_format_time(start)
    formatted_stop  = _validate_and_format_time(stop)

    flux = f"""
    from(bucket: "{bucket}")
      |> range(start: {formatted_start}, stop: {formatted_stop})
      |> filter(fn: (r) => r._measurement == "{measurement}")
      |> filter(fn: (r) => r._field == "{field}")
    """

    try:
        tables = query_influx(flux)
        logging.info("Consulta ejecutada en InfluxDB")
    except Exception as e:
        logging.exception("Error al consultar InfluxDB")
        logging.error("Flux enviado:\n%s", flux)
        raise HTTPException(500, f"Error consultando InfluxDB: {e}")

    # Convertimos a lista serializable
    data = [
        {"time": record.get_time(), "value": record.get_value()}
        for table in tables
        for record in table.records
    ]
    return {"data": data}


def list_measurements(bucket: str) -> List[str]:
    """Return the available measurements for the given bucket."""
    flux = f'''
    import "influxdata/influxdb/schema"
    schema.measurements(bucket: "{bucket}")
    '''
    try:
        result = query_influx(flux)
    except Exception as e:
        logging.exception("Error al consultar InfluxDB")
        raise HTTPException(500, detail=str(e))

    return [
        record.get_value()
        for table in result
        for record in table.records
    ]


def list_fields(bucket: str, measurement: str) -> List[str]:
    """Return field keys for a measurement within a bucket."""
    flux = f'''
    import "influxdata/influxdb/schema"
    schema.fieldKeys(
      bucket: "{bucket}",
      predicate: (r) => r._measurement == "{measurement}"
    )
    '''
    try:
        result = query_influx(flux)
    except Exception as e:
        logging.exception("Error al consultar InfluxDB")
        raise HTTPException(500, detail=str(e))

    return [
        record.get_value()
        for table in result
        for record in table.records
    ]


############################################################################33



from datetime import datetime, date, time

# app/services/influx_service.py
from datetime import datetime
from typing import List

def get_prices_range_utc(start_dt: datetime, stop_dt: datetime, field: str) -> List[float]:
    """
    Devuelve los precios horarios (ordenados) del campo *field* entre start_dt y stop_dt (exclusivo).
    Ambos parámetros deben estar en UTC con minutos/segundos = 0.
    """
    flux = f'''
      from(bucket: "TARIFF_PRICES")
        |> range(start: time(v: "{start_dt.isoformat()}Z"), stop: time(v: "{stop_dt.isoformat()}Z"))
        |> filter(fn: (r) => r._measurement == "pvpc_prices")
        |> filter(fn: (r) => r._field == "{field}")
        |> keep(columns: ["_time", "_value"])
        |> sort(columns: ["_time"])
    '''
    result = query_influx(flux)
    prices = [rec.get_value() for tbl in result for rec in tbl.records]

    expected = int((stop_dt - start_dt).total_seconds() // 3600)
    if len(prices) != expected:
        raise ValueError(
            f"Esperados {expected} precios entre {start_dt} y {stop_dt}, obtenidos {len(prices)}"
        )
    return prices




def get_date_range_from_influx(field: str = "predicted_kwh_price") -> tuple[date, date] | None:
    flux = f'''
      from(bucket: "TARIFF_PRICES")
        |> range(start: -30d)
        |> filter(fn: (r) => r._measurement == "pvpc_prices")
        |> filter(fn: (r) => r._field == "{field}")
        |> keep(columns: ["_time"])
        |> sort(columns: ["_time"])
    '''

    try:
        result = query_influx(flux)
    except Exception as e:
        logging.exception("Error consultando fechas desde InfluxDB")
        raise HTTPException(status_code=500, detail=f"Error InfluxDB: {e}")

    times = [record.get_time().date() for table in result for record in table.records]
    if not times:
        return None
    print("Hora inicial:", min(times))
    print("Hora final:",   max(times))
    return min(times), max(times)
