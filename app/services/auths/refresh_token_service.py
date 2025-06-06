from datetime import datetime
from jose import JWTError
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.common.verification_code import VerificationCode
from app.cores.token import verify_token, create_access_token

async def refresh_access_token(db: AsyncSession, refresh_token: str):
    try:
        payload = verify_token(refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Token sin email")

    result = await db.execute(
        select(VerificationCode).where(
            VerificationCode.email == email,
            VerificationCode.purpose == "refresh_token",
            VerificationCode.used == False,
            VerificationCode.expires_at > datetime.utcnow()
        ).order_by(VerificationCode.expires_at.desc())
    )

    record = result.scalar_one_or_none()

    if not record or record.code != refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token no válido o no encontrado")

    access_token = create_access_token(data={
        "user_id": payload["user_id"],
        "email": payload["email"],
        "role": payload["role"],
        "statuses": payload["statuses"]
    })

    return access_token, payload
