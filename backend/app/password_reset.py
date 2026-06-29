import hashlib
import secrets
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import PasswordResetToken, User


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_reset_token(token),
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )
    )
    return token


def reset_url(token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"


def send_password_reset_email(email: str, token: str) -> None:
    if not settings.smtp_host:
        return

    message = EmailMessage()
    message["Subject"] = "Reimposta la password di Cassa Campo"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content(
        "Hai richiesto di reimpostare la password di Cassa Campo.\n\n"
        f"Apri questo link entro 2 ore:\n{reset_url(token)}\n\n"
        "Se non hai richiesto tu il reset, ignora questa email."
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
