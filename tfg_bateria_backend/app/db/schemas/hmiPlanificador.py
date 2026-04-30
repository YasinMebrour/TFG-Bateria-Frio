from datetime import time, datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator, ConfigDict

# ─── Enum para validar origen ────────────────────────────────────────────
class OrigenPlan(str, Enum):
    optimizado = "optimizado"
    manual     = "manual"
    gemelo     = "gemelo"

# ─── Intervalo horario ──────────────────────────────────────────────────
class Intervalo(BaseModel):
    hora_inicio: time
    hora_fin:    time

# ─── Cuerpo completo recibido desde Node-RED ────────────────────────────
class PayloadHmi(BaseModel):
    origen:           OrigenPlan
    banda_seg_temp:   int
    banda_seg_hum:    int
    ahorro_habil:     bool
    planificacion:    Dict[str, List[Intervalo]]

    @validator("planificacion")
    def _validar_dias(cls, v):
        dias_requeridos = {
            "lunes", "martes", "miercoles", "jueves",
            "viernes", "sabado", "domingo"
        }
        faltan = dias_requeridos - v.keys()
        if faltan:
            raise ValueError(f"Faltan días: {', '.join(sorted(faltan))}")
        return v

# ─── Esquema de salida (lectura) ────────────────────────────────────────
class DiaHmiOut(BaseModel):
    id: int
    dia_semana: int
    inicio_1: Optional[time]
    fin_1:    Optional[time]
    inicio_2: Optional[time]
    fin_2:    Optional[time]
    inicio_3: Optional[time]
    fin_3:    Optional[time]
    banda_seg_temp: int
    banda_seg_hum:  int
    ahorro_habil:   bool
    modo_planif:    str
    actualizado_en: datetime

    model_config = ConfigDict(from_attributes=True)
