# app/db/schemas/auth.py
from pydantic import BaseModel, EmailStr, constr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email:        EmailStr
    code:         constr(min_length=6, max_length=6)
    new_password: constr(min_length=5)
