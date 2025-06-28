from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from app.models.users.user import User
from app.models.common.verification_code import VerificationCode
from app.cores.token import generate_verification_code, get_verification_expiration
from app.services.externals.email_service import send_email
from app.schemas.externals.email_schema import EmailSchema
from app.schemas.auths.password_reset_schema import PasswordResetRequest, PasswordResetVerify
from fastapi import HTTPException, status
from passlib.context import CryptContext
from app.services.validation.register_validater import validate_password

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def send_password_reset_email(request: PasswordResetRequest, db: AsyncSession):
    """Envía un código de verificación para restablecer contraseña"""
    # Verificar si el usuario existe
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Email no registrado")
    
    # Eliminar códigos anteriores para este email y propósito
    await db.execute(
        delete(VerificationCode).where(
            VerificationCode.email == request.email,
            VerificationCode.purpose == "password_reset"
        )
    )
    await db.commit()
    
    # Generar nuevo código de verificación
    code = generate_verification_code()
    expires_at = get_verification_expiration()
    
    # Guardar nuevo código en la base de datos
    verification_code = VerificationCode(
        email=request.email,
        role=user.role_id,
        code=code,
        purpose="password_reset",
        expires_at=expires_at,
        used=False,
        attempts=0,
        last_attempt=None
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
    """Verifica el código y cambia la contraseña con validaciones"""
    # Verificar si hay código activo
    result = await db.execute(
        select(VerificationCode).where(
            VerificationCode.email == request.email,
            VerificationCode.purpose == "password_reset",
            VerificationCode.used == False
        )
    )
    verification_code = result.scalars().first()
    
    if not verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay código de verificación activo. Solicita uno nuevo"
        )
    
    # Asegurar comparación correcta de timezones
    now = datetime.now(timezone.utc)
    expires_at = verification_code.expires_at.replace(tzinfo=timezone.utc) if verification_code.expires_at.tzinfo is None else verification_code.expires_at
    
    # 1. Verificar si el código ha expirado
    if expires_at < now:
        verification_code.used = True
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código expirado. Solicita uno nuevo"
        )
    
    # 2. Verificar tiempo de espera por intentos excedidos
    if verification_code.attempts >= 3 and verification_code.last_attempt:
        last_attempt = verification_code.last_attempt.replace(tzinfo=timezone.utc) if verification_code.last_attempt.tzinfo is None else verification_code.last_attempt
        wait_time = (now - last_attempt).total_seconds()
        
        if wait_time < 60:
            remaining_time = 60 - int(wait_time)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Demasiados intentos fallidos. Espera {remaining_time} segundos y solicita un nuevo código"
            )
        else:
            verification_code.attempts = 0
    
    # 3. Verificar si el código es correcto
    if verification_code.code != request.code:
        verification_code.attempts += 1
        verification_code.last_attempt = datetime.now(timezone.utc)
        await db.commit()
        
        remaining_attempts = 3 - verification_code.attempts
        if remaining_attempts > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Código incorrecto. Te quedan {remaining_attempts} intentos"
            )
        else:
            verification_code.used = True
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos fallidos. El código ha sido invalidado. Solicita uno nuevo"
            )
    
    # Validar la nueva contraseña
    try:
        await validate_password(request.new_password)
    except HTTPException as e:
        raise e
    
    # Verificar si el usuario existe
    user = await db.execute(select(User).where(User.email == request.email))
    user = user.scalars().first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    
    # Actualizar contraseña
    user.password = pwd_context.hash(request.new_password)
    verification_code.used = True
    await db.commit()
    
    return {"success": True, "message": "Contraseña actualizada correctamente"}