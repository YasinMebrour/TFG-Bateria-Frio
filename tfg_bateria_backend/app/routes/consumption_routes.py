"""Rutas relacionadas con el consumo eléctrico y sus costes."""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

import httpx
import pandas as pd
import pendulum
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.db.database import get_db
from app.db.models import ConsumoReal, PrediccionXGBoost
from app.services.electricity_cost import calcular_coste_luz
from app.services.influx_service import get_data
from app.config import INFLUX_BUCKET_PRECIOS, INFLUX_BUCKET_CONSUMO
from app.routes.authentication_routes import get_current_user


router = APIRouter(
    prefix="/consumo",
    tags=["consumo"],
    dependencies=[Depends(get_current_user)],
)


def rango_rfc3339(fecha_local: date) -> tuple[str, str]:
    """
    Devuelve dos strings RFC3339 en Europa/Madrid:
      - inicio al 00:00:00 del día
      - fin al 00:00:00 del día siguiente
    Con el offset correcto (+01:00 o +02:00).
    """
    inicio = pendulum.datetime(
        fecha_local.year,
        fecha_local.month,
        fecha_local.day,
        0,
        0,
        0,
        tz="Europe/Madrid",
    )
    fin = inicio.add(days=1)
    return inicio.to_rfc3339_string(), fin.to_rfc3339_string()


@router.get("/real")
def consumo_real(fecha: str, db: Session = Depends(get_db)) -> dict:
    """Return real consumption and cost for a given day."""

    # 1. parseo YYYY-MM-DD
    try:
        fecha_local = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Formato inválido; use 'YYYY-MM-DD'.")

    # 2. cálculo dinámico de RFC3339 con Pendulum
    rfc_inicio, rfc_fin = rango_rfc3339(fecha_local)

    # 3. obtener consumo de Influx
    resp_consumo = get_data(
        bucket=INFLUX_BUCKET_CONSUMO,
        measurement="consumo",
        field="consumo_watios",
        start=rfc_inicio,
        stop=rfc_fin,
    )
    df_consumo = pd.DataFrame(resp_consumo["data"]).rename(
        columns={"time": "hora", "value": "consumo"}
    )

    # Si no hay datos, o no cubren al menos 1 hora, devolvemos vacío:
    if df_consumo.empty or (
        df_consumo["hora"].max() - df_consumo["hora"].min()
    ) < timedelta(hours=1):
        return {"data": [], "total_cost_eur": 0}

    # 4. convertir timestamps UTC→Madrid y hacerlos naïve
    df_consumo["hora"] = (
        pd.to_datetime(df_consumo["hora"], utc=True)
        .dt.tz_convert("Europe/Madrid")
        .dt.tz_localize(None)
    )

    # ------------------------------------------------------------------ #
    # 3. Precios
    # ------------------------------------------------------------------ #
    price_field = "predicted_kwh_price"
    resp_precios = get_data(
        bucket=INFLUX_BUCKET_PRECIOS,
        measurement="pvpc_prices",
        field=price_field,
        start=rfc_inicio,
        stop=rfc_fin,
    )
    df_precios = pd.DataFrame(resp_precios["data"]).rename(
        columns={"time": "hora", "value": "kwh"}
    )
    if df_precios.empty:
        return {"data": [], "total_cost_eur": 0}

    df_precios["hora"] = (
        pd.to_datetime(df_precios["hora"], utc=True)
        .dt.tz_convert("Europe/Madrid")
        .dt.tz_localize(None)
    )

    df_costes, coste_total = calcular_coste_luz(df_consumo, df_precios)

    # ------------------------------------------------------------------ #
    # 5. Persistencia en ConsumoReal (evita duplicados)
    # ------------------------------------------------------------------ #
    existentes = {
        h
        for (h,) in db.query(ConsumoReal.hora)
        .filter(ConsumoReal.hora.between(rfc_inicio, rfc_fin))
        .all()
    }

    nuevos = [
        ConsumoReal(hora=row.hora, consumo=row.consumo)
        for row in df_consumo.itertuples(index=False)
        if row.hora not in existentes
    ]

    if nuevos:
        db.bulk_save_objects(nuevos)
        db.commit()

    # ------------------------------------------------------------------ #
    # 6. Respuesta
    # ------------------------------------------------------------------ #
    return {
        "data": df_costes.to_dict(orient="records"),
        "total_cost_eur": round(float(coste_total), 4),
    }


from app.config import IA_URL
from httpx import Timeout, AsyncClient

TIMEOUT = Timeout(connect=10.0, read=180.0, write=10.0, pool=None)


@router.post("/prediccion/manual")
async def proxy_y_calcula_coste(request: Request) -> Dict[str, Any]:
    """Proxy to the IA service and calculate energy cost from the response."""

    # 0. Cuerpo JSON
    try:
        cuerpo: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(400, "Cuerpo JSON inválido o ausente")

    # 1. Microservicio IA
    try:
        async with AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(IA_URL, json=cuerpo)
            logger.debug("IA STATUS: %s", resp.status_code)
            logger.debug("IA BODY: %s", resp.text)
            resp.raise_for_status()
            ia_out = resp.json()
    except httpx.ReadTimeout:
        raise HTTPException(504, "IA: tiempo de espera agotado (leer respuesta)")
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            e.response.status_code,
            f"IA devolvió {e.response.status_code}: {e.response.text}",
        )

    datasets: List[Dict[str, Any]] = ia_out.get("datasets", [])
    if not datasets:
        return {
            "data": [],
            "total_cost_eur": 0,
            "datasets": [],
            "humedad": ia_out.get("humedad", []),
        }

    # 2. DataFrame de consumo
    df_cons = pd.DataFrame(datasets)
    df_cons["hora"] = pd.to_datetime(df_cons["hora"])
    df_cons["consumo"] = df_cons["consumo"].astype(float)

    # 3. Ventana de precios (24 h)
    p_ini = pendulum.instance(df_cons["hora"].min(), tz="Europe/Madrid")
    start_rfc = p_ini.to_rfc3339_string()
    stop_rfc = p_ini.add(hours=24).to_rfc3339_string()

    prices_resp = get_data(
        bucket=INFLUX_BUCKET_PRECIOS,
        measurement="pvpc_prices",
        field="predicted_kwh_price", 
        start=start_rfc,
        stop=stop_rfc,
    )

    df_prec = pd.DataFrame(prices_resp["data"]).rename(
        columns={"time": "hora", "value": "kwh"}
    )
    if df_prec.empty:
        return {
            "data": [],
            "total_cost_eur": 0,
            "datasets": datasets,
            "humedad": ia_out.get("humedad", []),
        }

    df_prec["hora"] = (
        pd.to_datetime(df_prec["hora"], utc=True)
        .dt.tz_convert("Europe/Madrid")
        .dt.tz_localize(None)
    )

    # 4. Costes (peajes aplicados dentro de la función)
    df_coste, coste_total = calcular_coste_luz(df_cons, df_prec)

    # 5. Respuesta
    return {
        "data": df_coste.to_dict(orient="records"),
        "total_cost_eur": round(float(coste_total), 4),
        "datasets": datasets,
        "humedad": ia_out.get("humedad", []),
    }


# Consumme scheduler real de la camara
@router.post("/prediccion/ia")
async def consumo_prediccion_xgboost(
    request: Request,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Placeholder endpoint for scheduled IA predictions."""

    return {
        "data": [],
        "total_cost_eur": [],
    }


@router.get("/optimizado")
def consumo_opt(fecha: str, db: Session = Depends(get_db)) -> dict:
    """Devuelve el consumo previsto optimizado para la fecha indicada."""
    logger.debug("Endpoint /optimizado con fecha %s", fecha)
    # 1. Parseo YYYY-MM-DD
    try:
        fecha_local = datetime.strptime(fecha, "%Y-%m-%d").date()
        logger.debug("Fecha parseada correctamente: %s", fecha_local)
    except ValueError:
        logger.error("Formato de fecha inválido recibido")
        raise HTTPException(400, "Formato inválido; use 'YYYY-MM-DD'.")

    # 2. Calcular rango de horas del día en Madrid (naive)
    # intervalo local del día seleccionado
    dt_ini_local = pendulum.datetime(
        fecha_local.year, fecha_local.month, fecha_local.day, tz="Europe/Madrid"
    )
    dt_fin_local = dt_ini_local.add(days=1)

    # pasamos a UTC (sin tz para la query SQL)
    dt_ini_utc = dt_ini_local.in_tz("UTC").naive()
    dt_fin_utc = dt_fin_local.in_tz("UTC").naive()

    rows = (
        db.query(PrediccionXGBoost)
        .filter(PrediccionXGBoost.hora >= dt_ini_utc)
        .filter(PrediccionXGBoost.hora < dt_fin_utc)
        .order_by(PrediccionXGBoost.hora)
        .all()
    )
    logger.debug("Nº de filas extraídas de PrediccionXGBoost: %s", len(rows))

    if not rows:
        logger.debug("No hay filas en PrediccionXGBoost para ese rango")
        return {"data": [], "total_cost_eur": 0}

    df_consumo = pd.DataFrame(
        {"hora": [r.hora for r in rows], "consumo": [r.consumo for r in rows]}
    )

    # de UTC → Europe/Madrid → naive
    df_consumo["hora"] = (
        pd.to_datetime(df_consumo["hora"], utc=True)
        .dt.tz_convert("Europe/Madrid")
        .dt.tz_localize(None)
    )

    logger.debug("DataFrame de consumo creado:\n%s", df_consumo.head())

    # Asegura que hay al menos una hora de datos
    if (df_consumo["hora"].max() - df_consumo["hora"].min()) < timedelta(hours=1):
        logger.debug("Menos de 1 hora de datos de consumo")
        return {"data": [], "total_cost_eur": 0}

    rfc_inicio, rfc_fin = rango_rfc3339(fecha_local)
    logger.debug("Intervalo RFC3339: %s -> %s", rfc_inicio, rfc_fin)

    price_field = "predicted_kwh_price"
    resp_precios = get_data(
        bucket=INFLUX_BUCKET_PRECIOS,
        measurement="pvpc_prices",
        field=price_field,
        start=rfc_inicio,
        stop=rfc_fin,
    )
    logger.debug(
        "Datos de precios recuperados de Influx: %s filas", len(resp_precios["data"])
    )

    df_precios = pd.DataFrame(resp_precios["data"]).rename(
        columns={"time": "hora", "value": "kwh"}
    )
    logger.debug("DataFrame de precios creado:\n%s", df_precios.head())

    if df_precios.empty:
        logger.debug("DataFrame de precios vacío")
        return {"data": [], "total_cost_eur": 0}

    df_precios["hora"] = (
        pd.to_datetime(df_precios["hora"], utc=True)
        .dt.tz_convert("Europe/Madrid")
        .dt.tz_localize(None)
    )
    logger.debug(
        "DataFrame de precios tras conversión de zona horaria:\n%s", df_precios.head()
    )

    # 5. Calcular costes
    df_costes, coste_total = calcular_coste_luz(df_consumo, df_precios)
    logger.debug("DataFrame final de costes:\n%s", df_costes.head())
    logger.debug("Coste total calculado: %s", coste_total)

    # 6. Respuesta
    respuesta = {
        "data": df_costes.to_dict(orient="records"),
        "total_cost_eur": round(float(coste_total), 4),
    }
    logger.debug("RETURN final: %s", respuesta)
    return respuesta


@router.get("/consumo_comparativo")
def consumo_comparativo(
    fecha_inicio: str, fecha_fin: str, db: Session = Depends(get_db)
) -> dict:
    """Compare real and optimized consumption for a date range."""

    # Validación y parseo de fechas
    try:
        fecha_ini = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        if fecha_fin_dt < fecha_ini:
            raise ValueError
    except ValueError:
        raise HTTPException(
            400, "Formato de fecha inválido o rango no válido. Use 'YYYY-MM-DD'."
        )

    # Calcular límites para el rango completo: 00:00 del primer día a 00:00 del día después del último
    dt_ini_local = pendulum.datetime(
        fecha_ini.year, fecha_ini.month, fecha_ini.day, 0, 0, 0, tz="Europe/Madrid"
    )
    dt_fin_local = pendulum.datetime(
        fecha_fin_dt.year,
        fecha_fin_dt.month,
        fecha_fin_dt.day,
        0,
        0,
        0,
        tz="Europe/Madrid",
    ).add(days=1)

    start_rfc = dt_ini_local.to_rfc3339_string()
    stop_rfc = dt_fin_local.to_rfc3339_string()
    logger.debug("start_rfc: %s", start_rfc)
    logger.debug("stop_rfc: %s", stop_rfc)

    # ==============================
    # 1. CONSUMO REAL
    # ==============================
    resp_c = get_data(
        bucket=INFLUX_BUCKET_CONSUMO,
        measurement="consumo",
        field="consumo_watios",
        start=start_rfc,
        stop=stop_rfc,
    )
    logger.debug("Rows consumo: %s", len(resp_c["data"]))
    df_consumo_real = pd.DataFrame(resp_c["data"]).rename(
        columns={"time": "hora", "value": "consumo"}
    )
    if not df_consumo_real.empty:
        df_consumo_real["hora"] = (
            pd.to_datetime(df_consumo_real["hora"], utc=True)
            .dt.tz_convert("Europe/Madrid")
            .dt.tz_localize(None)
        )

    # ==============================
    # 2. CONSUMO OPTIMIZADO
    # ==============================
    dt_ini_utc = dt_ini_local.in_tz("UTC").naive()
    dt_fin_utc = dt_fin_local.in_tz("UTC").naive()

    rows = (
        db.query(PrediccionXGBoost)
        .filter(PrediccionXGBoost.hora >= dt_ini_utc)
        .filter(PrediccionXGBoost.hora < dt_fin_utc)
        .order_by(PrediccionXGBoost.hora)
        .all()
    )
    logger.debug("Rows pred: %s", len(rows))

    if rows:
        df_consumo_opt = pd.DataFrame(
            {"hora": [r.hora for r in rows], "consumo": [r.consumo for r in rows]}
        )
        df_consumo_opt["hora"] = (
            pd.to_datetime(df_consumo_opt["hora"], utc=True)
            .dt.tz_convert("Europe/Madrid")
            .dt.tz_localize(None)
        )
    else:
        df_consumo_opt = pd.DataFrame(columns=["hora", "consumo"])

    # ==============================
    # 3. PRECIOS
    # ==============================
    price_field = "predicted_kwh_price"
    resp_p = get_data(
        bucket=INFLUX_BUCKET_PRECIOS,
        measurement="pvpc_prices",
        field=price_field,
        start=start_rfc,
        stop=stop_rfc,
    )
    logger.debug("Rows precios: %s", len(resp_p["data"]))
    df_precios = pd.DataFrame(resp_p["data"]).rename(
        columns={"time": "hora", "value": "kwh"}
    )
    if not df_precios.empty:
        df_precios["hora"] = (
            pd.to_datetime(df_precios["hora"], utc=True)
            .dt.tz_convert("Europe/Madrid")
            .dt.tz_localize(None)
        )

    # ==============================
    # 4. CALCULAR COSTES
    # ==============================
    if not df_consumo_real.empty and not df_precios.empty:
        df_kwh_real, coste_total_real = calcular_coste_luz(df_consumo_real, df_precios)
    else:
        df_kwh_real, coste_total_real = pd.DataFrame(), 0

    if not df_consumo_opt.empty and not df_precios.empty:
        df_kwh_opt, coste_total_opt = calcular_coste_luz(df_consumo_opt, df_precios)
    else:
        df_kwh_opt, coste_total_opt = pd.DataFrame(), 0

    # ==============================
    # 5. RESPUESTA UNIFICADA
    # ==============================
    return {
        "real": {
            "data": (
                df_kwh_real.to_dict(orient="records") if not df_kwh_real.empty else []
            ),
            "total_cost_eur": round(float(coste_total_real), 4),
        },
        "optimizado": {
            "data": (
                df_kwh_opt.to_dict(orient="records") if not df_kwh_opt.empty else []
            ),
            "total_cost_eur": round(float(coste_total_opt), 4),
        },
    }
