"""Email utilities for password reset notifications."""
import smtplib
from email.message import EmailMessage
from app.config import (
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASS,
)

def send_reset_email(to_email: str, code: str):
    """Send a password reset code via email."""
    msg = EmailMessage()
    msg["Subject"] = "Código de recuperación de contraseña"
    msg["From"]    = SMTP_USER
    msg["To"]      = to_email
    msg.set_content(
        f"Has solicitado restablecer tu contraseña.\n\n"
        f"Tu código de verificación es: {code}\n\n"
        "Este código expirará en 1 hora."
    )

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)
