"""Routes related to IA consumption predictions."""

from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any
import datetime as dt
import pandas as pd
from datetime import date
import pendulum

from app.services.xgboost_inference import generar_predicciones

router = APIRouter(
    prefix="/consumo",
    tags=["consumo"]
)

def rango_rfc3339_pendulum(fecha_local: date):
    """Devuelve inicio y fin del día en RFC3339 Europe/Madrid."""
    inicio = pendulum.datetime(
        fecha_local.year,
        fecha_local.month,
        fecha_local.day,
        0, 0, 0,
        tz="Europe/Madrid",
    )
    fin = inicio.add(days=1)
    return inicio.to_rfc3339_string(), fin.to_rfc3339_string()


@router.post("/prediccion")
async def consumo_prediccion_xgboost(request: Request) -> Dict[str, Any]:
    """Genera una predicción de 24 h con XGBoost."""
    # 1. Validación del body
    try:
        params: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(400, "Cuerpo JSON inválido o ausente")

    if not {"schedule", "start_date"}.issubset(params):
        raise HTTPException(422, "Se requieren las claves 'schedule' y 'start_date'")

    schedule: List[Dict[str, str]] = params["schedule"]
    start_date_raw: str = params["start_date"]

    # 2. Parseo de start_date → pendulum.DateTime(Europe/Madrid)
    try:
        if len(start_date_raw) == 10:
            p_start = pendulum.parse(start_date_raw, tz="Europe/Madrid")
        else:
            p_start = pendulum.parse(start_date_raw)
            if p_start.tz is None:
                p_start = p_start.replace(tz="Europe/Madrid")
    except Exception:
        raise HTTPException(
            400,
            "start_date debe ser 'YYYY-MM-DD' o ISO-8601 (p.ej. 2025-02-12T00:00:00+01:00).",
        )

    # 3. Validación rápida del schedule
    if not isinstance(schedule, list):
        raise HTTPException(422, "'schedule' debe ser una lista")

    for i, intervalo in enumerate(schedule, 1):
        if not isinstance(intervalo, dict) or {"inicio_ahorro", "final_ahorro"} - intervalo.keys():
            raise HTTPException(422, f"Intervalo {i} inválido en 'schedule'")
        for clave in ("inicio_ahorro", "final_ahorro"):
            try:
                dt.datetime.strptime(intervalo[clave], "%H:%M")
            except ValueError:
                raise HTTPException(422, f"'{clave}' del intervalo {i} no cumple 'HH:MM'")

    # 4. Generar predicciones
    predicciones = generar_predicciones(
        schedule=schedule,
        start_date=p_start.to_datetime_string(),
    )

    if not predicciones:
        return {"datasets": [], "humedad": []}

    df_pred = pd.DataFrame(predicciones)

    datasets = [
        {"hora": h.isoformat(), "consumo": float(c)}
        for h, c in zip(
            pd.to_datetime(df_pred["timestamp"]).dt.tz_convert("Europe/Madrid").dt.tz_localize(None),
            df_pred["consumo"],
        )
    ]

    humedad = [
        {"hora": h.isoformat(), "humedad": float(hm)}
        for h, hm in zip(
            pd.to_datetime(df_pred["timestamp"]).dt.tz_convert("Europe/Madrid").dt.tz_localize(None),
            df_pred["humedad"],
        )
    ]

    return {
        "datasets": datasets,
        "humedad": humedad,
    }
