# schemas/evento_critico.py
from pydantic import BaseModel, ConfigDict
from datetime import date

class EventoCriticoBase(BaseModel):
    fecha: date
    tipo: str
    descripcion: str | None = None

class EventoCriticoCreate(EventoCriticoBase):
    pass

class EventoCriticoRead(EventoCriticoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
