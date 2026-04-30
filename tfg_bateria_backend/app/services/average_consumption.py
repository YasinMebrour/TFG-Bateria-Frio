from datetime import datetime, time, timedelta
from typing import List
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_


from ..db.models import Consumo, ModoAhorro
# Modelos SQLAlchemy asumidos
# class Consumo(Base): ...
# class ModoAhorro(Base): ...

def mostrar_consumo_medio_por_dias(
    db: Session
) -> None:
    """
    Imprime por pantalla el consumo medio diario para modo_ahorro 0 y 1
    en el rango [start_date, end_date].

    Args:
        start_date: 'YYYY-MM-DD' inclusive.
        end_date:   'YYYY-MM-DD' inclusive.
        db:         sesión SQLAlchemy.
    """
    
    start_date = datetime.strptime("2025-01-01", "%Y-%m-%d").date()
    end_date   = datetime.strptime("2025-05-02", "%Y-%m-%d").date()


    # --- 2) Recuperar todo el periodo de una sola consulta -------------------
    dt_start = datetime.combine(start_date, time.min)
    dt_end   = datetime.combine(end_date + timedelta(days=1), time.min)  # excluyente

    q = (
        db.query(
            Consumo.hora.label("hora"),
            Consumo.consumo.label("consumo"),
            ModoAhorro.modo_ahorro.label("modo_ahorro")
        )
        .join(ModoAhorro, and_(ModoAhorro.hora == Consumo.hora))
        .filter(Consumo.hora >= dt_start, Consumo.hora < dt_end)
    )
    registros = q.all()
    if not registros:
        print("No se encontraron datos en el intervalo solicitado.")
        return

    df = pd.DataFrame(registros, columns=["hora", "consumo", "modo_ahorro"])

    # --- 3) Calcular medias por día y modo -----------------------------------
    df["fecha"] = df["hora"].dt.date
    tabla = (
        df.groupby(["fecha", "modo_ahorro"])["consumo"]
          .mean()
          .unstack(fill_value=0)          # columnas: 0 y 1
          .sort_index()                   # orden cronológico
    )

    # --- 4) Imprimir resultados ---------------------------------------------
    for fecha, fila in tabla.iterrows():
        media0 = fila.get(0, 0.0)
        media1 = fila.get(1, 0.0)
        print(f"{fecha}: modo_ahorro 0 → {media0:.3f}   |   modo_ahorro 1 → {media1:.3f}")

    # Si prefieres ver la tabla completa de un golpe:
    # print(tabla)
