# app/db/schemas/usuarios.py

from typing import Optional
from pydantic import BaseModel, EmailStr, constr, ConfigDict


class UsuarioBase(BaseModel):
    nombre: constr(min_length=3, max_length=150)
    email: EmailStr
    is_editor: bool = False
    telegram_chat_id: Optional[str] = None
    telegram_notify: bool = False
    telegram_bot_token: Optional[str] = None


class UsuarioCreate(UsuarioBase):
    password: constr(min_length=5)


class UsuarioLogin(BaseModel):
    nombre: str
    password: str


class UsuarioRead(UsuarioBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class UsuarioUpdate(BaseModel):
    nombre: Optional[constr(min_length=3, max_length=150)] = None
    email: Optional[EmailStr] = None
    is_editor: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    telegram_notify: Optional[bool] = None
    telegram_bot_token: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: constr(min_length=5)


class UpdateEditorFlag(BaseModel):
    is_editor: bool


class UsuarioTelegramUpdate(BaseModel):
    telegram_chat_id: Optional[str] = None
    telegram_notify: bool = False
    telegram_bot_token: Optional[str] = None
