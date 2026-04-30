# File: app/db/schemas/planificacion.py
# ============================================================================
#  Esquema unificado de planificación
#  · Semanal  -> intervalos con bandas de seguridad
#  · Diaria   -> intervalos sin bandas
#  · Históricos y listados -> rangos datetime
# ============================================================================

from __future__ import annotations

from datetime import date, time, datetime
from typing import Dict, List
from pydantic import BaseModel, Field, RootModel

# --------------------------------------------------------------------------- #
# 1. Intervalos SEMANALES (plantilla)                                         #
# --------------------------------------------------------------------------- #
class IntervaloSemanalBase(BaseModel):
    hora_inicio:    time = Field(..., alias="hora_inicio")
    hora_fin:       time = Field(..., alias="hora_fin")
    modo_ahorro:    bool = Field(False, alias="modo_ahorro")

    model_config = {"populate_by_name": True}

class IntervaloSemanalIn(IntervaloSemanalBase):
    """Intervalo con bandas (entrada para POST /planificacion/semana)."""
    pass

class IntervaloSemanalOut(IntervaloSemanalBase):
    """Intervalo con bandas (salida GET /planificacion/semana)."""
    pass


class SemanaConOrigenIn(BaseModel):
    modo_planif: str  # 'Optimizado' | 'Camara' | 'Gemelo'
    dias: List[DiaDefaultIn]


# --------------------------------------------------------------------------- #
# 2. Intervalos DIARIOS (sin bandas)                                          #
# --------------------------------------------------------------------------- #
class IntervaloDiarioBase(BaseModel):
    hora_inicio: time = Field(..., alias="hora_inicio")
    hora_fin:    time = Field(..., alias="hora_fin")
    modo_ahorro: bool = Field(False, alias="modo_ahorro")

    model_config = {"populate_by_name": True}

class IntervaloDiarioIn(IntervaloDiarioBase):
    """Intervalo de entrada para POST /planificacion/dia."""
    pass

class IntervaloDiarioOut(IntervaloDiarioBase):
    """Intervalo de salida en la plantilla semanal fusionada."""
    pass


# --------------------------------------------------------------------------- #
# 3. Plantilla semanal completa                                               #
# --------------------------------------------------------------------------- #
class DiaDefaultIn(BaseModel):
    day_name:    str                 # 'Lunes' … 'Domingo'
    modo_ahorro: bool = False
    intervalos:  List[IntervaloSemanalIn]

class DiaDefaultOut(BaseModel):
    day_name:    str
    modo_ahorro: bool
    intervalos:  List[IntervaloSemanalOut]

class WeekSchema(RootModel):
    """Respuesta de GET /planificacion/semana (dict día → lista intervalos)."""
    root: Dict[str, List[IntervaloDiarioOut]]


# --------------------------------------------------------------------------- #
# 4. Planificación diaria (POST / GET)                                        #
# --------------------------------------------------------------------------- #
class DiaPlanificacionIn(BaseModel):
    fecha:       date
    modo_ahorro: bool = False
    intervalos:  List[IntervaloDiarioIn]

class DiaPlanificacionOut(BaseModel):
    fecha:      date
    intervalos: List[IntervaloDiarioOut]


# --------------------------------------------------------------------------- #
# 5. Históricos y listados (rangos datetime)                                  #
# --------------------------------------------------------------------------- #
class Interval(BaseModel):
    inicio_ahorro: datetime
    final_ahorro:  datetime

class DaySchedule(BaseModel):
    date:     date
    schedule: List[Interval]

class DiaPlanificacionListOut(BaseModel):
    fecha:       date
    modo_ahorro: bool
    schedule:    List[Interval]


# --------------------------------------------------------------------------- #
# 6. Estado global (tabla ultimo_estado)                                      #
# --------------------------------------------------------------------------- #
class EstadoPlanificacionOut(BaseModel):
    modo_planif:    str     # 'Optimizado' | 'Camara' | 'Gemelo'
    actualizado_en: datetime
