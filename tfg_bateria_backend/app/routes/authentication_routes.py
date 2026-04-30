# app/routes/auth.py
"""Rutas de autenticación y utilidades relacionadas.

Contiene endpoints para iniciar sesión, obtener el usuario actual y
gestionar el proceso de restablecimiento de contraseña.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.db.database import get_db
from app.db.models import Usuario, PasswordResetToken
from app.db.schemas.token import Token
from app.core.security import (
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)
from app.db.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from app.core.security import hash_password  
from app.core.email import send_reset_email
import secrets
from datetime import datetime, timedelta


router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> dict:
    """Autentica al usuario y devuelve un token JWT."""
    user: Usuario | None = (
        db.query(Usuario).filter_by(nombre=form_data.username).first()
    )
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token = create_access_token(subject=user.nombre)
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Devuelve el usuario autenticado a partir del token proporcionado."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token no válido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user: Usuario | None = db.query(Usuario).filter_by(nombre=username).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_admin(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Usuario:
    """Comprueba que el usuario actual sea editor/administrador."""
    # Asumimos que el modelo Usuario tiene un campo Boolean is_admin
    if not current_user.is_editor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes: se requiere rol administrador",
        )
    return current_user


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Genera un código de recuperación y lo envía por correo."""
    user = db.query(Usuario).filter_by(email=request.email).first()
    if not user:
        return {"msg": "Si ese correo está registrado, recibirás un código."}

    # borramos viejos tokens
    db.query(PasswordResetToken).filter_by(user_id=user.id).delete()

    # generamos un token aleatorio de 6 dígitos
    code = secrets.token_hex(3)  
    expires = datetime.utcnow() + timedelta(hours=1)

    reset = PasswordResetToken(
        user_id=user.id,
        token=code,
        expires_at=expires,
    )
    db.add(reset)
    db.commit()

    # enviamos email en segundo plano
    background_tasks.add_task(send_reset_email, to_email=user.email, code=code)

    return {"msg": "Si ese correo está registrado, recibirás un código."}


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Valida el código de recuperación y cambia la contraseña."""
    user = db.query(Usuario).filter_by(email=request.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Correo o código inválido")

    token_row = (
        db.query(PasswordResetToken)
        .filter_by(user_id=user.id, token=request.code)
        .first()
    )
    if not token_row or token_row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Correo o código inválido")

    # actualizamos contraseña
    user.password_hash = hash_password(request.new_password)
    # borramos todos los tokens de este usuario
    db.query(PasswordResetToken).filter_by(user_id=user.id).delete()

    db.commit()
    return {"msg": "Contraseña actualizada con éxito."}
