"""Integration helpers to communicate with Node-RED."""

import requests
from sqlalchemy.orm import Session
from app.config import (
    NODE_RED_PLANIFICACION_URL,
    NODE_RED_ESTADO_CRITICO_URL,
)
from datetime import datetime
from app.db.database import SessionLocal
from app.db.models import Config, PlanificacionSemanal, PlanificacionDiaria, OrigenPlan
from collections import defaultdict

def get_configuracion(db: Session) -> tuple[dict, int | None]:
    """Return the Node-RED configuration stored in the database."""
    config = db.query(Config).first()
    if not config:
        return {}, None

    payload_config = {
        "banda_seguridad_temperatura": config.banda_seguridad_temperatura,
        "banda_seguridad_humedad": config.banda_seguridad_humedad,
        "ahorro_energia_habilitado": "Si" if config.ahorro_energia_habilitado else "No",
        "banda_condiciones_optimas": config.banda_condiciones_optimas
    }
    return payload_config, config.hora_envio_planificacion if config.hora_envio_planificacion else None



from datetime import date, datetime, timedelta
from typing import Dict, List

DAY_NAMES = ["lunes", "martes", "miercoles", "jueves",
             "viernes", "sabado", "domingo"]

def _row_to_interval(row) -> dict:
    """Convierte un row SQLAlchemy en dict {hora_inicio, hora_fin}."""
    return {"hora_inicio": str(row.hora_inicio), "hora_fin": str(row.hora_fin)}

def construir_planificacion(db: Session) -> Dict[str, List[dict]]:
    """
    Construye la planificación de la *semana actual* (lunes-domingo).

    Reglas:
        • PlanificaciónDiaria, si existe para un día, sustituye a la plantilla.
        • modo_ahorro = False  → lista vacía.
        • modo_ahorro = True   → lista de intervalos válidos.
    """
    today   = date.today()
    monday  = today - timedelta(days=today.weekday())
    sunday  = monday + timedelta(days=6)

    # ───────────── 1) PLANTILLA SEMANAL ─────────────
    plantillas = (
        db.query(PlanificacionSemanal)
          .order_by(PlanificacionSemanal.dia_semana,
                    PlanificacionSemanal.hora_inicio)
    )

    plantilla_map: Dict[int, List[dict]] = {i: [] for i in range(7)}
    ahorro_off_template: set[int] = set()

    for row in plantillas:
        if not row.modo_ahorro:
            ahorro_off_template.add(row.dia_semana)      # día vacío
            continue
        if row.hora_inicio and row.hora_fin:
            plantilla_map[row.dia_semana].append(_row_to_interval(row))

    # ───────────── 2) PLANIFICACIÓN DIARIA (semana actual) ─────────────
    diarios = (
        db.query(PlanificacionDiaria)
          .filter(PlanificacionDiaria.fecha.between(monday, sunday),
                    PlanificacionDiaria.origen == OrigenPlan.establecida)
          .order_by(PlanificacionDiaria.fecha,
                    PlanificacionDiaria.hora_inicio)
    )

    diaria_map: Dict[date, List[dict]] = {}
    ahorro_off_dates: set[date] = set()

    for row in diarios:
        if not row.modo_ahorro:
            # sentinela OFF: el día entero queda vacío
            ahorro_off_dates.add(row.fecha)
            continue
        if row.hora_inicio and row.hora_fin:
            diaria_map.setdefault(row.fecha, []).append(_row_to_interval(row))

    # ───────────── 3) FUSIÓN SEMANAL ─────────────
    plan: Dict[str, List[dict]] = {}

    for i, name in enumerate(DAY_NAMES):
        current_date = monday + timedelta(days=i)

        if current_date in ahorro_off_dates:
            plan[name] = []
        elif current_date in diaria_map:
            plan[name] = diaria_map[current_date]
        elif i in ahorro_off_template:
            plan[name] = []
        else:
            plan[name] = plantilla_map[i]

        # ordenar y eliminar duplicados exactos
        plan[name] = sorted(
            {tuple(d.items()) for d in plan[name]},
            key=lambda t: t[0][1]          # hora_inicio
        )
        plan[name] = [dict(p) for p in plan[name]]

    return plan


def job_enviar_planificacion_red():
    """Send the weekly planning to the Node-RED endpoint."""
    with SessionLocal() as db:
        try:
            config_payload, _ = get_configuracion(db)
            planificacion = construir_planificacion(db)

            payload = {
                    "planificacion": {
                        **planificacion,
                        **config_payload
                    }
                
            }
            import json
            print("[Debug] Payload a enviar:", json.dumps(payload, indent=2))

            resp = requests.post(NODE_RED_PLANIFICACION_URL, json=payload)
            print("Planificación enviada:", resp.json())
        except Exception as e:
            print("Error al enviar planificación:", str(e))


def job_enviar_estado_critico_red():
    """Send a critical state notification to Node-RED."""
    try:
        payload = {"estado_critico": "Si"}
        resp = requests.post(NODE_RED_ESTADO_CRITICO_URL, json=payload)
        print("Estado crítico enviado:", resp.json())
    except Exception as e:
        print("Error al enviar estado crítico:", str(e))
