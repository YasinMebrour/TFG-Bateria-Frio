"""Rutas relacionadas con las fechas disponibles de datos."""

from datetime import date, timedelta
from fastapi import APIRouter, Depends

from app.routes.authentication_routes import get_current_user

router = APIRouter(
    prefix="/fechas", tags=["fechas"], dependencies=[Depends(get_current_user)]
)


@router.get("/disponibles")
async def fechas_disponibles():
    """Devuelve el rango de fechas que aceptan los endpoints."""

    # Fecha mínima disponible en el sistema
    start = date(2025, 1, 27)

    # Fecha máxima: mañana respecto al día de hoy
    today = date.today()
    end = today + timedelta(days=1)

    return [{"start": start, "end": end}]
