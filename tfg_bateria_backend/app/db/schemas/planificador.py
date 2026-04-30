# schemas.py
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Literal
from datetime import date, time

# -------- Tramo seman­al --------
class ModoAhorroSemanal(BaseModel):
    hora_inicio: time
    hora_fin: time

class ModoAhorroSemanalCreate(ModoAhorroSemanal):
    pass

class ModoAhorroSemanalRead(ModoAhorroSemanal):
    id: int
    model_config = ConfigDict(from_attributes=True)

# -------- Planificador seman­al --------
class PlanificadorBase(BaseModel):
    dia_semana: Literal[0, 1, 2, 3, 4, 5, 6]   # 0 = lunes … 6 = domingo

class PlanificadorCreate(PlanificadorBase):
    tramos_ahorro: List[ModoAhorroSemanalCreate]

class PlanificadorRead(PlanificadorBase):
    id: int
    tramos_ahorro: List[ModoAhorroSemanalRead]
    model_config = ConfigDict(from_attributes=True)


# ——— ModoAhorroHistorico (diario) ——————————————————————————————————————————————————————————————————————————————

class ModoAhorroHistoricoBase(BaseModel):
    hora_inicio: time
    hora_fin: time

class ModoAhorroHistoricoCreate(ModoAhorroHistoricoBase):
    """Para crear tramos en tabla `modo_ahorro_historico`"""
    pass

class ModoAhorroHistoricoRead(ModoAhorroHistoricoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ——— PlanificadorHistorico (diario) ——————————————————————————————————————————————————————————————————————————————

class PlanificadorHistoricoBase(BaseModel):
    fecha: date
    banda_seguridad_temperatura: Optional[float]
    banda_seguridad_humedad:      Optional[float]
    banda_condiciones_optimas:    Optional[float]
    ahorro_energia_habilitado:    bool = True

class PlanificadorHistoricoCreate(PlanificadorHistoricoBase):
    tramos_ahorro: List[ModoAhorroHistoricoCreate]

class PlanificadorHistoricoRead(PlanificadorHistoricoBase):
    id: int
    tramos_ahorro: List[ModoAhorroHistoricoRead]

    model_config = ConfigDict(from_attributes=True)
