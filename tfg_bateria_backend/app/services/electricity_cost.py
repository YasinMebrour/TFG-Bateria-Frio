import pandas as pd

def _to_local_naive(s: pd.Series) -> pd.Series:
    """
    Convierte una serie datetime a Europe/Madrid sin tz.
    Si ya es naive, simplemente la devuelve.
    """
    if s.dt.tz is not None:
        return s.dt.tz_convert("Europe/Madrid").dt.tz_localize(None)
    return s

def calcular_coste_luz(
    df_consumo: pd.DataFrame,
    df_precios: pd.DataFrame
) -> tuple[pd.DataFrame, float]:
    # 1) Copias y datetime
    consumo = df_consumo.copy()
    precios = df_precios.copy()
    consumo['hora'] = pd.to_datetime(consumo['hora'])
    precios['hora'] = pd.to_datetime(precios['hora'])


    # --- 1. Normalización de zona horaria ----------------------------------
    consumo["hora"]  = _to_local_naive(consumo["hora"])
    precios["hora"]  = _to_local_naive(precios["hora"])
    # -----------------------------------------------------------------------

    # 2) Agrupamos consumo medio por hora
    consumo['hora_hora'] = consumo['hora'].dt.floor('h')
    consumo_horario = (
        consumo
        .groupby('hora_hora', as_index=False)
        .agg(consumo_medio_kW=('consumo', 'mean'))
    )

    # 3) Creamos índice horario completo
    hora_min = consumo_horario['hora_hora'].min()
    hora_max = consumo_horario['hora_hora'].max()
    indice_horas = pd.date_range(hora_min, hora_max, freq='H')

    precios = precios.drop_duplicates(subset='hora', keep='first')

    # 4) Reindexamos precios y rellenamos huecos
    precios = precios.set_index('hora').reindex(indice_horas)
    precios['kwh'] = precios['kwh'].ffill().bfill()
    # Si no existe la columna 'peaje', la creamos con valor 0.0
    if 'peaje' not in precios.columns:
        precios['peaje'] = 0.0
    precios['peaje'] = precios['peaje'].fillna(0.0)  # Por si hay NaN

    precios = precios.reset_index().rename(columns={'index': 'hora'})

    # 5) Merge consumo medio con precios ya completos
    tabla = consumo_horario.merge(precios, left_on='hora_hora', right_on='hora', how='left')

    # 6) Coste horario (incluyendo peaje)
    tabla['coste'] = tabla['consumo_medio_kW'] * tabla['kwh'] * (1 + tabla['peaje'])

    # 7) Formateamos df de salida
    df_coste_kwh = (
        tabla[['hora_hora', 'coste']]
        .rename(columns={'hora_hora': 'hora', 'coste': 'coste_kwh'})
    )

    # 8) Coste total
    coste_total = df_coste_kwh['coste_kwh'].sum()

    return df_coste_kwh, coste_total
