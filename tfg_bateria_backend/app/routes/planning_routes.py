# File: app/routes/planificacion.py
# ============================================================================
#  Rutas de planificación
#  • Plantilla semanal      (/semana  GET / POST)
#  • Listado de días        (/lista   GET)
#  • Planificación diaria   (/dia     POST)
#  • Consultas día concreto (/diaEstablecido, /dia, /optimizada  GET)
# ============================================================================

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from app.routes.event_stream_routes import crear_y_emitir_evento
from app.routes.planning_ws_routes import notificar_cambio_planificacion

from app.db.database import get_db
from app.db.models import (
    PlanificacionSemanal,
    PlanificacionDiaria,
    OrigenPlan,
    UltimoEstado, 
    Config
)
from app.db.schemas.planificacion import (
    IntervaloDiarioOut,
    WeekSchema,
    DiaPlanificacionIn,
    DiaPlanificacionListOut,
    DaySchedule,
    Interval,
    SemanaConOrigenIn,
)


from app.jobs.node_red import job_enviar_planificacion_red
from app.routes.authentication_routes import get_current_user, get_current_admin
from app.db.models import Usuario

router = APIRouter(
    prefix="/planificacion",
    tags=["planificacion"],
    dependencies=[Depends(get_current_user)],
)

DAY_NAMES = [
    "LUNES", "MARTES", "MIERCOLES",
  "JUEVES", "VIERNES", "SABADO", "DOMINGO",
]


# --------------------------------------------------------------------------- #
# Herramientas internas                                                       #
# --------------------------------------------------------------------------- #
def get_monday(d: date) -> date:
    """Devuelve el lunes de la semana que contiene «d»."""
    return d - timedelta(days=d.weekday())  # 0 = lunes


# ---------------------------------------------------------------------------- #
# 1. Utilidad: convertir PlanificacionSemanal → dict Día → IntervalosOut       #
# ---------------------------------------------------------------------------- #
def read_week_template(db: Session) -> Dict[str, List[IntervaloDiarioOut]]:
    """Devuelve la plantilla semanal almacenada formateada por día."""

    config = db.query(Config).first()
    modo_ahorro_global = bool(config.ahorro_energia_habilitado)
    dias_ahorro_cfg = config.dias_ahorro or {}

    rows = (
        db.query(PlanificacionSemanal)
        .order_by(PlanificacionSemanal.dia_semana, PlanificacionSemanal.hora_inicio)
        .all()
    )

    by_day: Dict[int, List[IntervaloDiarioOut]] = {i: [] for i in range(7)}
    ahorro_off: set[int] = set()                     # ← días explícitamente “OFF”

    for r in rows:
        # 1) Si la fila es “apagada”, marca ese día y continúa
        if r.modo_ahorro is False:
            ahorro_off.add(r.dia_semana)
            continue

        # 2) Solo guarda intervalos válidos
        if r.hora_inicio is not None and r.hora_fin is not None:
            by_day[r.dia_semana].append(
                IntervaloDiarioOut(
                    hora_inicio=r.hora_inicio,
                    hora_fin=r.hora_fin,
                    modo_ahorro=True,
                )
            )

    result: Dict[str, List[IntervaloDiarioOut]] = {}
    for i, name in enumerate(DAY_NAMES):
        key_cfg = name.lower()

        # Condición para que el día esté activo:
        activo = (
            modo_ahorro_global and                       # modo global ON
            dias_ahorro_cfg.get(key_cfg, False) and      # día activo en config
            i not in ahorro_off                          # día no desactivado en plantilla
        )

        result[name] = by_day[i] if activo else []

    return result



# ---------------------------------------------------------------------------- #
# 2.  GET /semana   – Devuelve la única semana tipo                            #
# ---------------------------------------------------------------------------- #
@router.get(
    "/semana",
    response_model=WeekSchema,
    summary="Devuelve la semana tipo (lunes–domingo) almacenada",
)
def leer_semana(db: Session = Depends(get_db)):
    """Retorna la plantilla semanal en formato de esquema de salida."""

    data = read_week_template(db)
    return WeekSchema(root=data)

def plantilla_semanal_actual_normalizada(db):
    """Normaliza la plantilla semanal almacenada para comparaciones."""

    registros = (
        db.query(PlanificacionSemanal)
        .order_by(PlanificacionSemanal.dia_semana, PlanificacionSemanal.hora_inicio)
        .all()
    )
    intervals = []
    for r in registros:
        intervals.append({
            "dia": int(r.dia_semana),
            "modo_ahorro": bool(r.modo_ahorro),
            "hora_inicio": r.hora_inicio.strftime('%H:%M') if r.hora_inicio else None,
            "hora_fin": r.hora_fin.strftime('%H:%M') if r.hora_fin else None,
        })
    # Ordena por día y hora_inicio para asegurar comparación
    return sorted(intervals, key=lambda x: (x['dia'], x['hora_inicio'] or ''))


def plantilla_de_payload_normalizada(payload):
    """Convierte el payload recibido a un formato comparable con la BD."""

    intervals = []
    for dia in payload.dias:
        idx = DAY_NAMES.index(dia.day_name)
        if not dia.modo_ahorro:
            intervals.append({
                "dia": idx,
                "modo_ahorro": False,
                "hora_inicio": None,
                "hora_fin": None,
            })
        else:
            for itv in dia.intervalos:
                def norm(x):
                    if hasattr(x, 'strftime'):
                        return x.strftime('%H:%M')
                    return str(x)[:5]
                intervals.append({
                    "dia": idx,
                    "modo_ahorro": True,
                    "hora_inicio": norm(itv.hora_inicio),
                    "hora_fin": norm(itv.hora_fin),
                })
    # Ordena igual que la función de la BD
    return sorted(intervals, key=lambda x: (x['dia'], x['hora_inicio'] or ''))



# ---------------------------------------------------------------------------- #
# 3. POST /semana – Reemplaza completamente la semana tipo                     #
# ---------------------------------------------------------------------------- #
@router.post(
    "/semana",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sobrescribe la semana tipo (lunes-domingo) y actualiza origen",
)
async def guardar_semana(
    payload: SemanaConOrigenIn,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    """Sobrescribe la semana tipo y registra el origen indicado."""

    # 1. Consultar último estado
    ultimo_estado = db.query(UltimoEstado).order_by(UltimoEstado.id.desc()).first()

    # 2. Si tanto el estado como el payload son "Optimizado" → return
    if ultimo_estado and ultimo_estado.modo_planif == "Optimizado" and payload.modo_planif == "Optimizado":
        return

    # 3. Si el modo solicitado ES "Optimizado", tampoco hace falta comparar plantilla
    if payload.modo_planif == "Optimizado":
        db.add(
            UltimoEstado(
                modo_planif=payload.modo_planif,
                actualizado_en=datetime.now(),
            )
        )
        db.commit()
        await notificar_cambio_planificacion()
        crear_y_emitir_evento(
            db,
            fecha=datetime.now(),
            tipo=f"Planificacion Establecida {payload.modo_planif}",
            descripcion=f"Nueva planificación semanal con origen {payload.modo_planif}"
        )
        job_enviar_planificacion_red()
        return

    # 4. Para el resto de modos SÍ comparas la plantilla
    actual = plantilla_semanal_actual_normalizada(db)
    nueva = plantilla_de_payload_normalizada(payload)


    if actual == nueva and ultimo_estado.modo_planif != "Optimizado":
        return


    dias = payload.dias
    if len(dias) != 7:
        raise HTTPException(400, "Debes enviar exactamente 7 objetos, uno por día")
    recibidos = {d.day_name for d in dias}
    if set(recibidos) != set(DAY_NAMES):
        raise HTTPException(
            400,
            "Debe incluir LUNES, MARTES, MIERCOLES, JUEVES, VIERNES, SABADO y DOMINGO",
        )

    db.query(PlanificacionSemanal).delete()

    for dia in dias:
        idx = DAY_NAMES.index(dia.day_name)
        if not dia.modo_ahorro:
            db.add(
                PlanificacionSemanal(
                    dia_semana=idx,
                    hora_inicio=None,
                    hora_fin=None,
                    modo_ahorro=False,
                )
            )
            continue
        for itv in dia.intervalos:
            db.add(
                PlanificacionSemanal(
                    dia_semana=idx,
                    hora_inicio=itv.hora_inicio,
                    hora_fin=itv.hora_fin,
                    modo_ahorro=True,
                )
            )

    db.commit()

    db.add(
            UltimoEstado(
                modo_planif=payload.modo_planif,
                actualizado_en=datetime.now(),
            )
        )
    db.commit()

    crear_y_emitir_evento(
        db,
        fecha=datetime.now(),
        tipo=f"Planificacion Establecida {payload.modo_planif}",
        descripcion=f"Nueva planificación semanal con origen {payload.modo_planif}"
    )

    await notificar_cambio_planificacion()

    job_enviar_planificacion_red()



# --------------------------- listado de días ---------------------------------
@router.get(
    "/lista",
    response_model=List[DiaPlanificacionListOut],
    summary="Lista todos los días con planificación establecida",
)
def listar_dias(db: Session = Depends(get_db)):
    """Lista todos los días con planificación establecida."""

    rows = (
        db.query(PlanificacionDiaria)
        .filter(PlanificacionDiaria.origen == OrigenPlan.establecida)
        .order_by(PlanificacionDiaria.fecha, PlanificacionDiaria.hora_inicio)
        .all()
    )

    grouped: Dict[date, List[PlanificacionDiaria]] = defaultdict(list)
    for r in rows:
        grouped[r.fecha].append(r)

    salida: List[DiaPlanificacionListOut] = []
    for fecha, regs in grouped.items():
        modo = regs[0].modo_ahorro
        schedule = [
            {
                "inicio_ahorro": datetime.combine(fecha, r.hora_inicio),
                "final_ahorro": datetime.combine(fecha, r.hora_fin),
            }
            for r in regs
            if r.hora_inicio and r.hora_fin
        ]
        salida.append({"fecha": fecha, "modo_ahorro": modo, "schedule": schedule})

    return salida


# --------------------------- guardar día -------------------------------------
@router.post(
    "/dias",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Guarda en bloque la planificación personalizada de varios días",
)
async def guardar_dias(
    data: List[DiaPlanificacionIn],
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    """Guarda o actualiza múltiples días de planificación personalizada."""

    # 1. Recopilar fechas recibidas
    fechas_recibidas = {d.fecha for d in data}
    fechas_actuales = {row.fecha for row in db.query(PlanificacionDiaria)
                       .filter(PlanificacionDiaria.origen == OrigenPlan.establecida).all()}

    # 2. Borrar días que han desaparecido (el usuario los ha quitado)
    dias_a_borrar = fechas_actuales - fechas_recibidas
    if dias_a_borrar:
        db.query(PlanificacionDiaria).filter(
            PlanificacionDiaria.origen == OrigenPlan.establecida,
            PlanificacionDiaria.fecha.in_(dias_a_borrar)
        ).delete(synchronize_session=False)

    # 3. Actualizar o crear días recibidos
    for d in data:
        if d.fecha < date.today():
            raise HTTPException(400, f"No se puede modificar un día ya pasado: {d.fecha}")

        # Borrar planificación anterior de ese día
        db.query(PlanificacionDiaria).filter(
            PlanificacionDiaria.fecha == d.fecha,
            PlanificacionDiaria.origen == OrigenPlan.establecida,
        ).delete()

        # Insertar nueva planificación
        if not d.modo_ahorro:
            db.add(
                PlanificacionDiaria(
                    fecha=d.fecha,
                    hora_inicio=None,
                    hora_fin=None,
                    origen=OrigenPlan.establecida,
                    modo_ahorro=False,
                )
            )
        else:
            for it in d.intervalos:
                db.add(
                    PlanificacionDiaria(
                        fecha=d.fecha,
                        hora_inicio=it.hora_inicio,
                        hora_fin=it.hora_fin,
                        origen=OrigenPlan.establecida,
                        modo_ahorro=True,
                    )
                )
    await notificar_cambio_planificacion()

    db.commit()

    # Notificar si algún día corresponde a la semana actual
    monday = get_monday(date.today())
    sunday = monday + timedelta(days=6)
    for d in data:
        if monday <= d.fecha <= sunday:
            break

    return {"detail": f"Planificación de {len(data)} días guardada"}


# --------------------------- consultas de día --------------------------------
def _fetch_day(
    db: Session, fecha: date, origen: OrigenPlan
) -> List[PlanificacionDiaria]:
    """Obtiene las filas de planificación de un día según su origen."""
    return (
        db.query(PlanificacionDiaria)
        .filter(
            PlanificacionDiaria.fecha == fecha,
            PlanificacionDiaria.origen == origen,
        )
        .order_by(PlanificacionDiaria.hora_inicio)
        .all()
    )


def _build_day_schedule(fecha: date, rows: List[PlanificacionDiaria]) -> DaySchedule:
    """Construye un horario de día a partir de filas de BD."""

    intervals = [
        Interval(
            inicio_ahorro=datetime.combine(fecha, r.hora_inicio),
            final_ahorro=datetime.combine(fecha, r.hora_fin),
        )
        for r in rows
        if r.hora_inicio and r.hora_fin
    ]
    return DaySchedule(date=fecha, schedule=intervals)


@router.get(
    "/diaEstablecido",
    response_model=DaySchedule,
    summary="Planificación ESTABLECIDA de un día",
)
def get_establecida(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Devuelve la planificación establecida para un día concreto."""
    fecha = _parse_date(start_date)
    rows = _fetch_day(db, fecha, OrigenPlan.establecida)
    return _build_day_schedule(fecha, rows)


@router.get(
    "/dia",
    response_model=DaySchedule,
    summary="Planificación REAL de un día",
)
def get_real(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Devuelve la planificación real registrada para un día."""
    fecha = _parse_date(start_date)
    rows = _fetch_day(db, fecha, OrigenPlan.real)
    return _build_day_schedule(fecha, rows)


@router.get(
    "/optimizada",
    response_model=DaySchedule,
    summary="Planificación OPTIMIZADA de un día",
)
def get_opt(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Devuelve la planificación optimizada calculada para un día."""

    fecha = _parse_date(start_date)
    rows = _fetch_day(db, fecha, OrigenPlan.opt)
    return _build_day_schedule(fecha, rows)


# --------------------------------------------------------------------------- #
# Utilidad común: parsear fecha                                               #
# --------------------------------------------------------------------------- #
def _parse_date(s: str) -> date:
    """Parsea una fecha YYYY-MM-DD y devuelve un objeto ``date``."""

    try:
        return datetime.fromisoformat(s).date()
    except ValueError as exc:
        raise HTTPException(400, "Formato de fecha inválido; use YYYY-MM-DD") from exc




@router.get("/panel_control", summary="Devuelve el estado actual del panel de control")
def get_panel_control(db: Session = Depends(get_db)):
    """Construye la información necesaria para el panel de control del HMI."""
    # ---------- 1. origen activo ----------
    estado = (
        db.query(UltimoEstado)
          .order_by(UltimoEstado.actualizado_en.desc(), UltimoEstado.id.desc())
          .first()
    )
    if not estado:
        raise HTTPException(404, "No hay estado configurado")

    origen = estado.modo_planif                             # "Optimizado" | "Camara" | "Gemelo"
    hoy = date.today()

    # ---------- 2. parámetros generales ----------
    config = db.query(Config).first()
    if not config:
        raise HTTPException(404, "No hay configuración")

    modo_ahorro_activo = bool(config.ahorro_energia_habilitado)
    dias_ahorro        = config.dias_ahorro or {}           # dict { lunes: True/False, … }

    panel = {
        "origen": origen,
        "banda_seguridad_temperatura": config.banda_seguridad_temperatura,
        "banda_seguridad_humedad":     config.banda_seguridad_humedad,
        "modo_ahorro_activo":          modo_ahorro_activo,
        "dias": {d: [] for d in DAY_NAMES},
    }

    def formatea(itvs: list[list[str]]) -> list[list[str]]:
        return [itvs[i] if i < len(itvs) else ["0", "0"] for i in range(3)]

    def dia_apagado(idx: int) -> bool:
        return not dias_ahorro.get(DAY_NAMES[idx].lower(), False)

    # ---------- 3. modo ahorro global OFF ----------
    if not modo_ahorro_activo:
        for d in DAY_NAMES:
            panel["dias"][d] = [["0", "0"]] * 3
        return panel

    # ---------- 4. Origen Optimizado ----------
    if origen == "Optimizado":
        for offset in range(7):
            fecha     = hoy + timedelta(days=offset)
            idx       = fecha.weekday()
            day_name  = DAY_NAMES[idx]

            if dia_apagado(idx):
                panel["dias"][day_name] = [["0", "0"]] * 3
                continue

            rows = _fetch_day(db, fecha, OrigenPlan.establecida)
            if not rows and offset < 2:
                rows = _fetch_day(db, fecha, OrigenPlan.opt)

            if not rows or any(r.modo_ahorro is False for r in rows):
                panel["dias"][day_name] = [["0", "0"]] * 3
                continue

            intervalos = [
                [f"{r.hora_inicio:%H:%M}", f"{r.hora_fin:%H:%M}"]
                for r in rows if r.hora_inicio and r.hora_fin
            ]
            panel["dias"][day_name] = formatea(intervalos)
        return panel

    # ---------- 5. Origen Camara / Gemelo ----------
    if origen in ("Camara", "Gemelo"):
        for offset in range(7):
            fecha     = hoy + timedelta(days=offset)
            idx       = fecha.weekday()
            day_name  = DAY_NAMES[idx]

            if dia_apagado(idx):
                panel["dias"][day_name] = [["0", "0"]] * 3
                continue

            plan_rows = _fetch_day(db, fecha, OrigenPlan.establecida)
            if not plan_rows:
                plan_rows = (
                    db.query(PlanificacionSemanal)
                      .filter(PlanificacionSemanal.dia_semana == idx)
                      .order_by(PlanificacionSemanal.hora_inicio)
                      .all()
                )

            if not plan_rows or any(r.modo_ahorro is False for r in plan_rows):
                panel["dias"][day_name] = [["0", "0"]] * 3
                continue

            intervalos = [
                [f"{r.hora_inicio:%H:%M}", f"{r.hora_fin:%H:%M}"]
                for r in plan_rows if r.hora_inicio and r.hora_fin
            ]
            panel["dias"][day_name] = formatea(intervalos)
        return panel



def formatea_intervalos(intervalos):
    """Devuelve siempre tres intervalos, rellenando con ceros si faltan."""

    out = []
    for i in range(3):
        if i < len(intervalos):
            out.append(intervalos[i])
        else:
            out.append(["0", "0"])
    return out


