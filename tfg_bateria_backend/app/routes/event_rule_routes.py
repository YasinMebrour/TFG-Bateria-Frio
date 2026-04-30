"""Rutas CRUD para las reglas de eventos automáticos."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import EventRule, Usuario
from app.db.schemas.event_rule import (
    EventRuleCreate,
    EventRuleRead,
    EventRuleUpdate,
)
from app.routes.authentication_routes import get_current_user, get_current_admin

router = APIRouter(
    prefix="/reglas",
    tags=["reglas"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=List[EventRuleRead])
def list_rules(db: Session = Depends(get_db)):
    """Devuelve todas las reglas configuradas."""

    return db.query(EventRule).all()


@router.post("/", response_model=EventRuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: EventRuleCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    """Crea una nueva regla de evento."""

    rule = EventRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=EventRuleRead)
def update_rule(
    rule_id: int,
    payload: EventRuleUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    """Actualiza una regla existente."""

    rule = db.query(EventRule).get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    """Elimina una regla de evento."""

    rule = db.query(EventRule).get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    db.delete(rule)
    db.commit()

