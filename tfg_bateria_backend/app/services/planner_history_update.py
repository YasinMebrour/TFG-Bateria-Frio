# app/services/actualizar_planificador.py

from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.db.models import (
    Planificador,
    PlanificadorHistorico,
    ModoAhorroHistorico,
)
from app.db.database import get_db


def actualizar_planificador_historico(db: Session, fecha_obj: date) -> PlanificadorHistorico:
    """
    Sincroniza la tabla planificador_historico con la planificación semanal (`planificador`) para la fecha dada.

    - Para fechas futuras: borra y copia tramos íntegros.
    - Para el día actual, si ya existe histórico prev: sólo actualiza de ahora en adelante; mantiene tramos pasados.
    - Nunca modifica días pasados en esta función.
    """
    ahora_dt = datetime.now()
    hoy = ahora_dt.date()
    ahora_hora = ahora_dt.time()

    # Obtener plan base semanal
    dia_semana = fecha_obj.weekday()
    plan_base = db.query(Planificador).filter(Planificador.dia_semana == dia_semana).first()
    if not plan_base:
        return None

    # Cargar o crear histórico
    hist = db.query(PlanificadorHistorico).filter(PlanificadorHistorico.fecha == fecha_obj).first()
    is_today = (fecha_obj == hoy)

    if fecha_obj > hoy or not is_today or not hist:
        # Futuro o primer sync de hoy: reconstruir todo
        if hist:
            db.delete(hist)
            db.flush()
        hist = PlanificadorHistorico(
            fecha=fecha_obj
        )
        # Copiar tramos según regla
        for tramo in plan_base.tramos_ahorro:
            # Si es hoy, incluir con ajuste en curso
            if is_today and tramo.hora_inicio < ahora_hora < tramo.hora_fin:
                inicio = ahora_hora
            else:
                inicio = tramo.hora_inicio
            hist.tramos_ahorro.append(
                ModoAhorroHistorico(hora_inicio=inicio, hora_fin=tramo.hora_fin)
            )
        db.add(hist)
        db.commit()
        db.refresh(hist)
        return hist

    # Caso: fecha_obj == hoy y hist ya existía -> solo actualizar desde ahora
    # 1) Ajustar tramos en curso en histórico existente: si un tramo inicia antes y termina después de ahora, recortar fin a ahora
    for tramo in hist.tramos_ahorro:
        if tramo.hora_inicio < ahora_hora < tramo.hora_fin:
            tramo.hora_fin = ahora_hora
    # 2) Eliminar tramos futuros (los que comienzan en o después de ahora)
    for tramo in list(hist.tramos_ahorro):
        if tramo.hora_inicio >= ahora_hora:
            db.delete(tramo)
    db.flush()
    # 3) Añadir tramos nuevos del plan base para hoy: in-progress y futuros
    for tramo in plan_base.tramos_ahorro:
        # si el tramo base termina antes o al iniciar hoy, omitir
        if tramo.hora_fin <= ahora_hora:
            continue
        inicio_nuevo = tramo.hora_inicio
        if inicio_nuevo < ahora_hora:
            inicio_nuevo = ahora_hora
        hist.tramos_ahorro.append(
            ModoAhorroHistorico(hora_inicio=inicio_nuevo, hora_fin=tramo.hora_fin)
        )
    # 4) Actualizar bandas y flags

    db.commit()
    db.refresh(hist)
    return hist



########################

def generar_historico_rango(db: Session, fecha_inicio: date, fecha_fin: date,
                             laboral_conf: dict, festivo_conf: dict) -> list[PlanificadorHistorico]:
    """
    Genera registros en planificador_historico para el rango [fecha_inicio, fecha_fin].
    Para cada fecha:
      - Si weekday < 5: usa laboral_conf
      - Si weekday >=5: usa festivo_conf
    Sobreescribe cualquier histórico existente.
    """
    resultados = []
    dia = fecha_inicio
    while dia <= fecha_fin:
        conf = laboral_conf if dia.weekday() < 5 else festivo_conf
        # Borrar existente
        existe = db.query(PlanificadorHistorico).filter(PlanificadorHistorico.fecha == dia).first()
        if existe:
            db.delete(existe)
            db.flush()
        # Crear histórico con config
        nuevo = PlanificadorHistorico(
            fecha=dia,
            banda_seguridad_temperatura=conf["banda_seguridad_temperatura"],
            banda_seguridad_humedad=conf["banda_seguridad_humedad"],
            banda_condiciones_optimas=conf["banda_condiciones_optimas"],
            ahorro_energia_habilitado=conf["ahorro_energia_habilitado"],
        )
        for tramo in conf.get("tramos_ahorro", []):
            nuevo.tramos_ahorro.append(
                ModoAhorroHistorico(
                    hora_inicio=tramo["hora_inicio"],
                    hora_fin=tramo["hora_fin"]
                )
            )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        resultados.append(nuevo)
        dia += timedelta(days=1)
    return resultados


def generar_historico_intervalo_predefinido(db: Session, fecha_inicio: date, fecha_fin: date) -> list[PlanificadorHistorico]:
    """
    Función provisional: genera histórico de planificaciones para el rango dado.

    - Lunes a Viernes:
      banda_seguridad_temperatura = 3.0,
      banda_seguridad_humedad = 12.0,
      banda_condiciones_optimas = 0.0,
      ahorro_energia_habilitado = True,
      tramos_ahorro = [(08:00,10:00),(18:00,22:00)]

    - Sábado y Domingo:
      banda_seguridad_temperatura = 3.0,
      banda_seguridad_humedad = 12.0,
      banda_condiciones_optimas = 0.0,
      ahorro_energia_habilitado = False,
      tramos_ahorro = []
    """
    laboral_conf = {
        "banda_seguridad_temperatura": 3.0,
        "banda_seguridad_humedad": 12.0,
        "banda_condiciones_optimas": 0.0,
        "ahorro_energia_habilitado": True,
        "tramos_ahorro": [
            {"hora_inicio": datetime.strptime("08:00","%H:%M").time(), "hora_fin": datetime.strptime("10:00","%H:%M").time()},
            {"hora_inicio": datetime.strptime("18:00","%H:%M").time(), "hora_fin": datetime.strptime("22:00","%H:%M").time()},
        ]
    }
    festivo_conf = {
        "banda_seguridad_temperatura": 3.0,
        "banda_seguridad_humedad": 12.0,
        "banda_condiciones_optimas": 0.0,
        "ahorro_energia_habilitado": False,
        "tramos_ahorro": []
    }
    return generar_historico_rango(db, fecha_inicio, fecha_fin, laboral_conf, festivo_conf)
