"""Rutas para consultar datos en InfluxDB."""

from textwrap import dedent
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import INFLUX_ORG
from app.routes.authentication_routes import get_current_user
from app.services.influx_service import (
    get_data,
    list_measurements,
    list_fields,
)
from app.services.influx_client import query_influx


router = APIRouter(
    prefix="/influx",
    tags=["InfluxDB"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/buckets")
def get_buckets():
    """Lista los buckets disponibles en la organización de InfluxDB."""

    # Nos aseguramos de que esté configurada la organización
    if not INFLUX_ORG:
        raise HTTPException(
            500,
            "No está configurada la organización INFLUX_ORG",
        )

    # Consulta Flux para obtener los buckets definidos
    flux = dedent(
        """
        buckets()
        """
    ).strip()

    # Lanzamos la consulta y manejamos posibles errores
    try:
        tables = query_influx(flux)
        logging.info("Buckets listados correctamente")
    except Exception as e:
        logging.exception("Error al consultar InfluxDB")
        logging.error("Flux enviado:\n%s", flux)
        raise HTTPException(
            status_code=500,
            detail=f"Error consultando InfluxDB: {e}",
        )

    # Extraemos los nombres de cada bucket devuelto en la consulta
    buckets = [
        record.values["name"]
        for table in tables
        for record in table.records
    ]
    return {"buckets": buckets}

@router.get("/measurements")
def get_measurements(
    bucket: str = Query(..., description="Nombre del bucket al que pertenece el measurement"),
):
    """Devuelve la lista de measurements disponibles en el bucket."""

    try:
        measurements = list_measurements(bucket)
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error al consultar InfluxDB")
        raise HTTPException(500, detail=str(e))

    return {"measurements": measurements}

@router.get("/fields")
def get_fields(
    bucket: str = Query(..., description="Nombre del bucket"),
    measurement: str = Query(..., description="Nombre del measurement")
):
    """Dado un measurement, devuelve la lista de fields disponibles."""

    try:
        fields = list_fields(bucket, measurement)
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error al consultar InfluxDB")
        raise HTTPException(500, detail=str(e))

    return {"fields": fields}


@router.get("/metadata")
def get_metadata(
    bucket: str = Query(..., description="Nombre del bucket"),
    measurement: str | None = Query(None, description="Measurement opcional")
):
    """Devuelve measurements y, opcionalmente, los fields de un measurement."""

    try:
        measurements = list_measurements(bucket)
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error al consultar InfluxDB")
        raise HTTPException(500, detail=str(e))

    fields: list[str] = []
    if measurement:
        try:
            fields = list_fields(bucket, measurement)
        except HTTPException:
            raise
        except Exception as e:
            logging.exception("Error al consultar InfluxDB")
            raise HTTPException(500, detail=str(e))

    return {"measurements": measurements, "fields": fields}

@router.get("/data")
def get_data_influx(
    bucket: str = Query(..., description="Nombre del bucket"),
    measurement: str = Query(..., description="Measurement"),
    field: str = Query(..., description="Field"),
    start: str = Query("-24h", description="Inicio del rango (RFC 3339 o -24h)"),
    stop: str = Query("now()", description="Fin del rango (RFC 3339 o now())"),
):
    """
    Delega en influx_services.get_data; cualquier excepción HTTP
    saldrá tal cual hacia el cliente.
    """
    # Reutilizamos la lógica común del servicio de InfluxDB
    return get_data(
        bucket=bucket,
        measurement=measurement,
        field=field,
        start=start,
        stop=stop,
    )
