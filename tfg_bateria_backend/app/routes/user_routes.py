"""Rutas relacionadas con la gestión de usuarios."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.db.database import get_db
from app.db.models import Usuario
from app.db.schemas.usuarios import (
    UsuarioCreate,
    UsuarioRead,
    UpdateEditorFlag,
    UsuarioTelegramUpdate,
)
from app.routes.authentication_routes import get_current_user, get_current_admin


router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Genera el hash de la contraseña utilizando bcrypt."""

    return pwd_context.hash(password)

@router.post("/", response_model=UsuarioRead, status_code=201)
def create_user(
    user_in: UsuarioCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
) -> Usuario:
    """Crea un nuevo usuario (requiere rol de administrador)."""

    if db.query(Usuario).filter_by(nombre=user_in.nombre).first():
        raise HTTPException(400, "El nombre ya existe")
    if db.query(Usuario).filter_by(email=user_in.email).first():
        raise HTTPException(400, "El correo ya existe")

    user = Usuario(
        nombre=user_in.nombre,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        is_editor=user_in.is_editor,
        telegram_chat_id=user_in.telegram_chat_id,
        telegram_notify=user_in.telegram_notify,
        telegram_bot_token=user_in.telegram_bot_token,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user  # SQLAlchemy -> UsuarioRead gracias a from_attributes

@router.get(
    "/",
    response_model=List[UsuarioRead],
    summary="Listar usuarios",
)
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
) -> List[Usuario]:
    """Devuelve una lista paginada de usuarios."""

    return db.query(Usuario).offset(skip).limit(limit).all()

@router.put("/{user_id}/role", response_model=UsuarioRead)
def update_user_role(
    user_id: int,
    data: UpdateEditorFlag,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
) -> Usuario:
    """Actualiza el rol de editor de un usuario."""

    user = db.query(Usuario).get(user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    user.is_editor = data.is_editor
    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar un usuario",
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
) -> None:
    """Elimina un usuario de la base de datos."""

    user = db.query(Usuario).get(user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    db.delete(user)
    db.commit()


@router.get("/me", response_model=UsuarioRead)
def read_current_user(user: Usuario = Depends(get_current_user)) -> Usuario:
    """Devuelve el usuario autenticado actual."""

    return user


@router.put("/me/telegram", response_model=UsuarioRead)
def update_telegram_settings(
    data: UsuarioTelegramUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """Actualiza la configuración de Telegram del usuario actual."""

    current_user.telegram_chat_id = data.telegram_chat_id
    current_user.telegram_notify = data.telegram_notify
    current_user.telegram_bot_token = data.telegram_bot_token
    db.commit()
    db.refresh(current_user)
    return current_user
