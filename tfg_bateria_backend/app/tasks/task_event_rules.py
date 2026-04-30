from celery import shared_task
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import EventRule
from app.services.influx_service import get_data
from app.services.notifier import crear_y_emitir_evento
from app.config import BUCKET_INFLUX_CAMARA

import operator


@shared_task
def evaluate_event_rules():
    """Evalúa las reglas de eventos definidas en la base de datos."""
    db: Session = SessionLocal()
    try:
        reglas = db.query(EventRule).filter(EventRule.habilitada == True).all()
        for regla in reglas:
            start = f"-{regla.ventana_segundos}s"
            datos = get_data(
                BUCKET_INFLUX_CAMARA,
                regla.measurement,
                regla.field,
                start=start,
            )["data"]

            triggered = False

            if regla.tipo_condicion == "comparacion":
                ops = {
                    ">": operator.gt,
                    ">=": operator.ge,
                    "<": operator.lt,
                    "<=": operator.le,
                    "==": operator.eq,
                    "!=": operator.ne,
                }
                op = ops.get(regla.operador)
                if op and datos:
                    valor = float(datos[-1]["value"])
                    try:
                        umbral = float(regla.valor_derecho)
                    except ValueError:
                        continue
                    triggered = op(valor, umbral)

            elif regla.tipo_condicion == "inactividad":
                triggered = len(datos) == 0

            elif regla.tipo_condicion == "ocurrencia":
                for row in datos:
                    if str(row["value"]) == regla.valor_derecho:
                        triggered = True
                        break

            if triggered:
                descripcion = regla.descripcion or regla.nombre
                print(f"[Regla activada] {regla.nombre} -> {descripcion}")
                crear_y_emitir_evento(
                    db,
                    tipo=regla.nombre,
                    descripcion=descripcion,
                    rule_id=regla.id,
                )
    finally:
        db.close()
