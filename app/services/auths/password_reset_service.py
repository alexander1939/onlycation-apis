from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.users.user import User
from app.models.common.verification_code import VerificationCode
from app.cores.token import generate_verification_code, get_verification_expiration
from app.services.externals.email_service import send_email
from app.schemas.externals.email_schema import EmailSchema
from app.schemas.auths.password_reset_schema import PasswordResetRequest, PasswordResetVerify
from fastapi import HTTPException
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def send_password_reset_email(request: PasswordResetRequest, db: AsyncSession):
    # Verificar si el usuario existe
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Email no registrado")
    
    # Generar código de verificación
    code = generate_verification_code()
    expires_at = get_verification_expiration()
    
    # Guardar código en la base de datos
    verification_code = VerificationCode(
        email=request.email,
        code=code,
        purpose="password_reset",
        expires_at=expires_at,
        used=False
    )
    
    db.add(verification_code)
    await db.commit()
    
    # Enviar correo electrónico
    subject = "Recuperación de contraseña"
    body = f"""
    <h1>Recuperación de contraseña</h1>
    <p>Hemos recibido una solicitud para restablecer tu contraseña.</p>
    <p>Tu código de verificación es: <strong>{code}</strong></p>
    <p>Este código expirará en 15 minutos.</p>
    """
    
    email_data = EmailSchema(
        email=request.email,
        subject=subject,
        body=body
    )
    
    await send_email(email_data)
    
    return {"success": True, "message": "Correo de recuperación enviado"}

async def verify_password_reset(request: PasswordResetVerify, db: AsyncSession):
    # Verificar si el código es válido
    result = await db.execute(
        select(VerificationCode).where(
            VerificationCode.email == request.email,
            VerificationCode.code == request.code,
            VerificationCode.purpose == "password_reset",
            VerificationCode.used == False,
            VerificationCode.expires_at > datetime.now(UTC)
        )
    )
    verification_code = result.scalars().first()
    
    if not verification_code:
        raise HTTPException(status_code=400, detail="Código inválido o expirado")
    
    # Verificar si el usuario existe
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Actualizar contraseña
    hashed_password = pwd_context.hash(request.new_password)
    user.password = hashed_password
    verification_code.used = True
    
    await db.commit()
    
    return {"success": True, "message": "Contraseña actualizada correctamente"}