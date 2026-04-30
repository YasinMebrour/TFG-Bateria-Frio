from datetime import date
from typing import Literal, List, Optional
from pydantic import BaseModel, Field


class PeajeSchema(BaseModel):
    nombre: str
    peaje: float

    model_config = {"from_attributes": True}


class BloqueTarifa(BaseModel):
    month: Optional[int] = Field(
        ..., ge=1, le=12,
        description="Mes (1-12) o None para todos los meses"
    )
    day_type: Literal["weekday", "weekend", "holiday"] = Field(
        ..., description="Tipo de día"
    )
    hour: int = Field(
        ..., ge=0, le=23,
        description="Hora de inicio del tramo (0–23)"
    )
    tarifa: Literal["P1", "P2", "P3", "P4", "P5", "P6"] = Field(
        ..., description="Código de tarifa"
    )

    model_config = {"from_attributes": True}


class DiaTarifa(BaseModel):
    date: date
    tarifas: List[Literal["P1", "P2", "P3", "P4", "P5", "P6"]]

    model_config = {"from_attributes": True}


class TarifasFestivos(BaseModel):
    tarifas: List[BloqueTarifa]
    festivos: List[date]
    peajes: Optional[List[PeajeSchema]] = []

    model_config = {"from_attributes": True}
