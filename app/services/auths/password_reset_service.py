from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.users.user import User
from app.schemas.auths.password_reset_schema import PasswordResetRequest, PasswordResetConfirm
from app.services.externals.email_service import send_email
from app.cores.token import create_reset_token, verify_reset_token
from app.schemas.externals.email_schema import EmailSchema
from datetime import datetime, UTC
import html

async def request_password_reset(email: str, db: AsyncSession):
    # Verificar si el usuario existe
    user = await db.get(User, email)
    if not user:
        # Por seguridad, no revelamos si el email existe o no
        return
    
    # Crear token de recuperación
    reset_token = create_reset_token(email)
    
    # Crear enlace de recuperación (en producción usarías tu URL frontend)
    reset_link = f"http://tuapp.com/reset-password?token={reset_token}"
    
    # Crear y enviar el email
    subject = "Recuperación de contraseña"
    body = f"""
    <h2>Recuperación de contraseña</h2>
    <p>Hemos recibido una solicitud para restablecer tu contraseña. Si no fuiste tú, ignora este correo.</p>
    <p>Para restablecer tu contraseña, haz clic en el siguiente enlace:</p>
    <a href="{reset_link}">Restablecer contraseña</a>
    <p>Este enlace expirará en 30 minutos.</p>
    """
    
    email_data = EmailSchema(
        email=email,
        subject=subject,
        body=body
    )
    
    await send_email(email_data)

async def reset_password(token: str, new_password: str, db: AsyncSession):
    # Verificar el token
    email = verify_reset_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")
    
    # Buscar al usuario
    user = await db.get(User, email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Actualizar la contraseña
    user.password = new_password  # Deberías hashear la contraseña aquí
    user.updated_at = datetime.now(UTC)
    
    await db.commit()
    await db.refresh(user)
    
    return user