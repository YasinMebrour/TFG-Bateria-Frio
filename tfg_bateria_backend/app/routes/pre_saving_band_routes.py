"""Rutas para calcular la banda previa de ahorro basándose en InfluxDB."""

from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime
from typing import Optional

import pandas as pd

from app.config import INFLUX_BUCKET_CONSUMO
from app.routes.authentication_routes import get_current_user
from app.services.influx_service import get_data


router = APIRouter(
    prefix="/banda_pre_ahorro",
    tags=["banda_pre_ahorro"],
    dependencies=[Depends(get_current_user)],
)

@router.get("/", summary="Calcula banda usando sólo consumo y humedad")
def calcular_banda_simple(
    start: datetime = Query(..., description="Fecha/hora inicio ISO"),
    end: datetime = Query(..., description="Fecha/hora fin ISO"),
) -> dict:
    """Devuelve la banda media de consumo y un historial de estados.

    La banda es la duración media (en minutos) de los tramos en los que el
    consumo está por encima del umbral de 4 W.  Se combina el consumo con la
    humedad obtenida de InfluxDB y se clasifica cada instante como subida o
    bajada de consumo.
    """

    if start >= end:
        raise HTTPException(400, "`start` debe ser anterior a `end`")

    # ─── 1. obtener consumo desde InfluxDB ───────────────────────────────
    resp_consumo = get_data(
        bucket=INFLUX_BUCKET_CONSUMO,
        measurement="consumo",
        field="consumo_watios",
        start=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        stop=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    df_consumo = (
        pd.DataFrame(resp_consumo["data"])
        .rename(columns={"time": "hora", "value": "consumo"})
        .sort_values("hora")
    )

    resp_humedad = get_data(
        bucket=INFLUX_BUCKET_CONSUMO,
        measurement="sensores",
        field="humedadCamara",
        start=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        stop=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    df_humedad = (
        pd.DataFrame(resp_humedad["data"])
        .rename(columns={"time": "hora", "value": "humedad"})
        .sort_values("hora")
    )

    if df_consumo.empty or df_humedad.empty:
        raise HTTPException(
            404,
            "Sin datos de consumo o humedad en InfluxDB para el rango solicitado"
        )

    # ─── 2. fusionar por hora ambos DataFrames ──────────────────────────
    df_merge = pd.merge_asof(
        df_humedad,
        df_consumo,
        on="hora",
        direction="backward",
        tolerance=pd.Timedelta("5m")
    ).sort_values("hora").reset_index(drop=True)

    # ─── 3. clasificar: 0 = bajada (>4 W), 1 = subida (<=4 W) ─────────────
    df_merge["estado"] = df_merge["consumo"].fillna(0).le(4).astype(int)

    # ─── 4. calcular duraciones de cada tramo en bajada ─────────────────
    df_merge["seg"] = (
        df_merge["estado"].shift(1, fill_value=1) != df_merge["estado"]
    ).cumsum()
    duraciones = []
    for _, g in df_merge.groupby("seg"):
        if g["estado"].iloc[0] != 0:
            continue
        t0, t1 = g["hora"].iloc[[0, -1]]
        duraciones.append((t1 - t0).total_seconds() / 60)

    # ─── 5. banda media en minutos ──────────────────────────────────────
    banda: Optional[float] = (
        sum(duraciones) / len(duraciones) if duraciones else None
    )

    # ─── 6. preparar salida para la API ─────────────────────────────────
    datos = [
        {
            "hora": row.hora.isoformat(),
            "humedad": row.humedad,
            "estado": int(row.estado),
        }
        for row in df_merge.itertuples()
    ]

    return {"banda": banda, "datos": datos}
