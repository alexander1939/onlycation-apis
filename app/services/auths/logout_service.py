from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from datetime import datetime
from app.models.common.verification_code import VerificationCode


'''
Propósito: Invalidar refresh token en logout.
Acción: Borra el token activo del usuario (no usado/no expirado).
Retorno: True (éxito) o False (no había token).
'''

async def logout_user(db: AsyncSession, email: str):
    try:
        result = await db.execute(
            select(VerificationCode).where(
                VerificationCode.email == email,
                VerificationCode.purpose == "refresh_token",
                VerificationCode.used == False,
                VerificationCode.expires_at > datetime.utcnow()
            ).order_by(VerificationCode.expires_at.desc())
        )

        refresh_token = result.scalar_one_or_none()

        if not refresh_token:
            return False  # No hay sesión activa

        await db.execute(
            delete(VerificationCode).where(VerificationCode.id == refresh_token.id)
        )
        await db.commit()
        return True

    except Exception as e:
        import traceback
        print("ERROR:", e)
        traceback.print_exc()
        raise e