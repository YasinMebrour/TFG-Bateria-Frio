from typing import Optional
from pydantic import BaseModel, ConfigDict

class EventRuleBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    measurement: str
    field: str
    operador: str
    valor_derecho: str
    tipo_condicion: str
    ventana_segundos: int
    frecuencia_segundos: int
    habilitada: bool = True

class EventRuleCreate(EventRuleBase):
    pass

class EventRuleRead(EventRuleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class EventRuleUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    measurement: Optional[str] = None
    field: Optional[str] = None
    operador: Optional[str] = None
    valor_derecho: Optional[str] = None
    tipo_condicion: Optional[str] = None
    ventana_segundos: Optional[int] = None
    frecuencia_segundos: Optional[int] = None
    habilitada: Optional[bool] = None
