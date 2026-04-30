from datetime import datetime, timedelta, time
from typing import List, Dict

import pandas as pd
from sqlalchemy.orm import Session

from ..db.models import Consumo, ModoAhorro


def calcular_consumo_medio_ahorro(
    schedule: List[Dict[str, str]],
    start_date: str,
    db: Session
) -> pd.DataFrame:
    """
    Calcula:
      * Media de consumo cuando modo_ahorro == 1 (on).
      * Media de consumo por hora tras cada fin de tramo de ahorro (off), hasta 12 h.

    Args:
        schedule: lista de dicts con 'inicio_ahorro' y 'final_ahorro' (HH:MM).
        start_date: fecha en formato 'YYYY-MM-DD'.
        db: sesión SQLAlchemy.

    Returns:
        DataFrame con columnas:
          - period: 'on' o 'off_{i}h' para i en [1..12]
          - mean_consumo: float
    """
    # 1) Parsear fecha y rango de 24h
    try:
        fecha = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("start_date debe tener formato 'YYYY-MM-DD'.")

    day_start = datetime.combine(fecha, time.min)
    day_end   = day_start + timedelta(days=1)

    # 2) Obtener datos de consumo y modo_ahorro
    query = (
        db.query(
            Consumo.hora.label('hora'),
            Consumo.consumo.label('consumo'),
            ModoAhorro.modo_ahorro.label('modo_ahorro')
        )
        .join(
            ModoAhorro,
            Consumo.hora == ModoAhorro.hora
        )
        .filter(Consumo.hora >= day_start, Consumo.hora < day_end)
        .order_by(Consumo.hora)
    )
    records = query.all()
    if not records:
        return pd.DataFrame(columns=['period', 'mean_consumo'])

    df = pd.DataFrame(records, columns=['hora', 'consumo', 'modo_ahorro'])

    # 3) Media de consumo cuando modo_ahorro == 1
    mean_on = df.loc[df['modo_ahorro'] == 1, 'consumo'].mean() or 0.0

    # 4) Preparar mapa hora->consumo para off
    consumo_map = {row['hora']: row['consumo'] for _, row in df.iterrows()}

    # 5) Para cada tramo de schedule, recolectar consumos de horas posteriores
    offsets: Dict[int, List[float]] = {}
    for tramo in schedule:
        # parsear final_ahorro
        hf, mf = map(int, tramo['final_ahorro'].split(':'))
        tramo_end = datetime.combine(fecha, time(hour=hf, minute=mf))
        # recorrer horas siguientes hasta 12 h o fin del día
        for i in range(1, 13):
            t = tramo_end + timedelta(hours=i)
            if t >= day_end:
                break
            if t in consumo_map:
                offsets.setdefault(i, []).append(consumo_map[t])

    # 6) Media off por hora tras ahorro
    mean_off = {i: (sum(vals)/len(vals)) for i, vals in offsets.items() if vals}

    # 7) Formatear resultado
    rows = [{'period': 'on', 'mean_consumo': float(mean_on)}]
    for i in range(1, 13):
        key = f'off_{i}h'
        mean_i = float(mean_off.get(i, 0.0))
        rows.append({'period': key, 'mean_consumo': mean_i})

    return pd.DataFrame(rows, columns=['period', 'mean_consumo'])
