# coding: utf-8
"""
Módulo de inferencia con XGBoost para la predicción simultánea de
consumo, humedad y temperatura.  Adaptado a la función ``get_data``
y a la zona horaria Europe/Madrid.
"""

import os
import pickle

import numpy as np
import pandas as pd
import pendulum                               # para gestionar zonas horarias

from app.services.influx_service import get_data

from contextlib import redirect_stdout, redirect_stderr


# ----------------------------------------------------------------------
# Configuración general
# ----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "modelo_xgb_hybrid_1min.pkl")
N_LAGS = 360                                # número de lags utilizados
INFLUX_BUCKET_CAMERA = "CAMARA_2"           # bucket principal en InfluxDB
CURRENT_TIME = None                          # actualizado en prediccion_recursiva_xgb

# Cada tupla = (nombre_col, measurement, field)
CONSULTAS = [
    ("humedad",      "sensores",  "humedadCamara"),
    ("modo_ahorro",  "estados",   "ahorro"),
    ("consumo",      "consumo",   "consumo_watios"),
    ("temperatura",  "sensores",  "temperaturaCamara"),
]

# ----------------------------------------------------------------------
# 1. Carga y preprocesado de datos históricos
# ----------------------------------------------------------------------
def _to_rfc3339_utc(dt):
    """pendulum → RFC-3339 en UTC."""
    return pendulum.instance(dt).in_timezone("UTC").to_rfc3339_string()

def cargar_y_preprocesar_datos(start_dt: pendulum.DateTime | None):
    """
    Descarga del rango necesario desde Influx y devuelve un DataFrame
    con 1 minuto de resolución y columnas:
      timestamp (UTC), consumo, humedad, temperatura, modo_ahorro, …
    """
    # ---------- rango a extraer ----------
    if start_dt is None:
        start, stop = "-24h", "now()"
    else:
        fetch_start = _to_rfc3339_utc(start_dt.subtract(minutes=N_LAGS + 180))
        fetch_stop  = _to_rfc3339_utc(start_dt.add(minutes=1))
        start, stop = fetch_start, fetch_stop

    df_combinado = None

    # ---------- descargar cada serie ----------
    for var, measurement, field in CONSULTAS:
        respuesta = get_data(
            bucket=INFLUX_BUCKET_CAMERA,
            measurement=measurement,
            field=field,
            start=start,
            stop=stop,
        )
        df = pd.DataFrame(respuesta["data"]).rename(
            columns={"time": "timestamp", "value": var}
        )
        if df.empty:
            print(f"[WARN] InfluxDB no devolvió datos para {var}.")
            continue


        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df.sort_values("timestamp", inplace=True)

        df_combinado = df if df_combinado is None else pd.merge(
            df_combinado, df, on="timestamp", how="outer"
        )

    if df_combinado is None or df_combinado.empty:
        return pd.DataFrame()

    # ---------- resample 1 min + limpieza ----------
    df_combinado = (
        df_combinado.set_index("timestamp")
              .interpolate(method="time")
              .resample("1min").mean()
              .dropna()
              .reset_index()
    )

    # ---------- variables cíclicas y rolling ----------
    df_combinado["hour_sin"]   = np.sin(2*np.pi*df_combinado["timestamp"].dt.hour   / 24)
    df_combinado["hour_cos"]   = np.cos(2*np.pi*df_combinado["timestamp"].dt.hour   / 24)
    df_combinado["minute_sin"] = np.sin(2*np.pi*df_combinado["timestamp"].dt.minute / 60)
    df_combinado["minute_cos"] = np.cos(2*np.pi*df_combinado["timestamp"].dt.minute / 60)

    ventana = 180
    for v in ["consumo", "humedad", "temperatura"]:
        df_combinado[f"{v}_rolling_mean"] = df_combinado[v].rolling(ventana).mean()
        df_combinado[f"{v}_rolling_std"]  = df_combinado[v].rolling(ventana).std()

    df_combinado.dropna(inplace=True)
    return df_combinado

# ----------------------------------------------------------------------
# 2. Predicción recursiva con el modelo multi-salida
# ----------------------------------------------------------------------
def prediccion_recursiva_xgb(model, ultimas_caracteristicas, pasos, modos_futuros):
    """
    Devuelve np.array(steps, 3) con predicciones de
    [consumo, humedad, temperatura] minuto a minuto.
    """
    global CURRENT_TIME
    predicciones = []

    idx_c0, idx_c1 = 11, 11 + N_LAGS
    idx_h0, idx_h1 = idx_c1, idx_c1 + N_LAGS
    idx_t0, idx_t1 = idx_h1, idx_h1 + N_LAGS

    entrada_actual = ultimas_caracteristicas.copy()

    for i in range(pasos):
        yhat = model.predict(entrada_actual)[0]
        predicciones.append(yhat)

        # desplazar lags
        entrada_actual[0, idx_c0:idx_c1] = np.hstack((yhat[0], entrada_actual[0, idx_c0:idx_c1-1]))
        entrada_actual[0, idx_h0:idx_h1] = np.hstack((yhat[1], entrada_actual[0, idx_h0:idx_h1-1]))
        entrada_actual[0, idx_t0:idx_t1] = np.hstack((yhat[2], entrada_actual[0, idx_t0:idx_t1-1]))

        # modo ahorro siguiente minuto
        entrada_actual[0, 0] = modos_futuros[i]

        # variables cíclicas locales
        CURRENT_TIME = CURRENT_TIME.add(minutes=1)
        h, m = CURRENT_TIME.hour, CURRENT_TIME.minute
        entrada_actual[0, 1:5] = [
            np.sin(2*np.pi*h/24),  np.cos(2*np.pi*h/24),
            np.sin(2*np.pi*m/60),  np.cos(2*np.pi*m/60),
        ]

    return np.array(predicciones)

# ----------------------------------------------------------------------
# 3. Utilidades de horario
# ----------------------------------------------------------------------
def rango_a_minutos(hhmm_ini, hhmm_fin):
    h1, m1 = map(int, hhmm_ini.split(":"))
    h2, m2 = map(int, hhmm_fin.split(":"))
    return h1*60 + m1, h2*60 + m2

def construir_intervalos(schedule, weekday):
    """
    Devuelve [(min_ini, min_fin, is_ahorro), ...] para el día indicado.
    """
    bloques = []
    if schedule and "dia" in schedule[0]:
        intervals = [
            (s["dia"],) + rango_a_minutos(s["inicio_ahorro"], s["final_ahorro"])
            for s in schedule
        ]
        day_intervals = [
            (ini, fin) for d, ini, fin in intervals
            if d.lower() == weekday.lower()
        ]
    else:
        day_intervals = [
            rango_a_minutos(s["inicio_ahorro"], s["final_ahorro"]) for s in schedule
        ]

    # fusionar bloques ahorro / normal
    day_intervals.sort()
    cursor = 0
    for ini, fin in day_intervals:
        if fin <= cursor:
            continue
        if ini > cursor:
            bloques.append((cursor, ini, 0))          # modo normal
        bloques.append((ini, fin, 1))                 # modo ahorro
        cursor = fin
    if cursor < 1440:
        bloques.append((cursor, 1440, 0))
    return bloques

# ----------------------------------------------------------------------
# 4. Generación de predicciones (24 h)
# ----------------------------------------------------------------------
def generar_predicciones(schedule: list, start_date: str | None = None):
    """
    schedule   : lista de bloques ahorro {'inicio_ahorro', 'final_ahorro', ...}
    start_date : ISO-8601. Si None, se parte del último dato histórico.
    """
    global CURRENT_TIME

    # ---------- modelo ----------
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"No se encontró el modelo: {MODEL_PATH}")
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    # ---------- histórico ----------
    
    p_start = pendulum.parse(start_date, tz="Europe/Madrid") if start_date else None
   
    expected_rows = N_LAGS + 2

    df_hist = cargar_y_preprocesar_datos(p_start)

    if df_hist.empty or "timestamp" not in df_hist.columns or len(df_hist) != expected_rows:
        p_fallback = pendulum.parse("2025-05-20", tz="Europe/Madrid")
        df_hist = cargar_y_preprocesar_datos(p_fallback)

        if df_hist.empty or "timestamp" not in df_hist.columns:
            raise ValueError("No hay datos disponibles ni siquiera con el fallback.")

        df_hist = df_hist.set_index("timestamp")

        if p_start is None:
            raise ValueError("No había start_date válido para remapear timestamps.")

        target_day = p_start.in_timezone("UTC").start_of("day")
        hora_min_sec = [(ts.hour, ts.minute, ts.second) for ts in df_hist.index]
        new_index = [
            (target_day) + pd.Timedelta(hours=h, minutes=m, seconds=s)
            for h, m, s in hora_min_sec
        ]
        df_hist.index = pd.DatetimeIndex(new_index).tz_convert("UTC")
    else:
        df_hist = df_hist.set_index("timestamp")

    # ---------- instante inicial ----------
    # Queremos que CURRENT_TIME sea el último minuto del día anterior
    
    target_end = p_start.start_of("day").in_timezone("UTC").subtract(minutes=1)
    df_hist = df_hist[df_hist.index <= target_end]

    
    row = df_hist.iloc[-1]
    CURRENT_TIME = pendulum.instance(row.name).in_timezone("Europe/Madrid")
    inicio_prediccion = CURRENT_TIME

    # ---------- vector de features ----------
    modo_actual = 0
    h, m        = CURRENT_TIME.hour, CURRENT_TIME.minute
    base_feats  = [
        modo_actual,
        np.sin(2*np.pi*h/24),  np.cos(2*np.pi*h/24),
        np.sin(2*np.pi*m/60),  np.cos(2*np.pi*m/60),
        row["consumo_rolling_mean"],      row["consumo_rolling_std"],
        row["humedad_rolling_mean"],      row["humedad_rolling_std"],
        row["temperatura_rolling_mean"],  row["temperatura_rolling_std"],
    ]
    lags = np.hstack((
        np.full(N_LAGS, row["consumo"]),
        np.full(N_LAGS, row["humedad"]),
        np.full(N_LAGS, row["temperatura"]),
    ))
    ultimas_caracteristicas = np.hstack((base_feats, lags)).reshape(1, -1)

    # ---------- modos_futuros (24 h) ----------
    modos_futuros = []
    for i in range(1440):
        t = CURRENT_TIME.add(minutes=i+1)
        bloques = construir_intervalos(schedule, t.format("dddd", locale="es"))
        minuto = t.hour*60 + t.minute
        modo   = next((is_ah for ini, fin, is_ah in bloques if ini <= minuto < fin), 0)
        modos_futuros.append(modo)

    # ---------- predicción recursiva ----------

    with open(os.devnull, "w") as devnull:
        with redirect_stdout(devnull), redirect_stderr(devnull):
            preds = prediccion_recursiva_xgb(model["recursive"], ultimas_caracteristicas, 1440, modos_futuros)

    # ---------- salida ----------
    timestamps = [inicio_prediccion.add(minutes=i+1) for i in range(1440)]


    
    return [
        {
            "timestamp": ts.to_iso8601_string(),  # incluye +01:00 / +02:00
            "consumo":     float(c),
            "humedad":     float(h),
            "temperatura": float(t),
        }
        for ts, (c, h, t) in zip(timestamps, preds)
    ]

