from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict
from datetime import time

class ConfigBandaBase(BaseModel):
    banda_seguridad_temperatura: Optional[float]
    banda_seguridad_humedad: Optional[float]
    banda_condiciones_optimas: Optional[float]
    ahorro_energia_habilitado: Optional[bool]
    rangos_ahorro: Optional[int]
    horas_modo_ahorro: Optional[float]
    horas_max_ahorro: Optional[int]
    horas_max_entre_ahorro: Optional[float]
    hora_envio_planificacion: Optional[time]
    # Nuevo campo: diccionario de lunes a domingo con True/False
    dias_ahorro: Optional[Dict[str, bool]]

class ConfigBandaCreate(ConfigBandaBase):
    pass

class ConfigBandaRead(ConfigBandaBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class ConfigBandaUpdate(BaseModel):
    banda_seguridad_temperatura: Optional[float]
    banda_seguridad_humedad: Optional[float]
    banda_condiciones_optimas: Optional[float]
    ahorro_energia_habilitado: Optional[bool]
    rangos_ahorro: Optional[int]
    horas_modo_ahorro: Optional[float]
    horas_max_ahorro: Optional[int]
    horas_max_entre_ahorro: Optional[float]
    hora_envio_planificacion: Optional[time]
    dias_ahorro: Optional[Dict[str, bool]]
