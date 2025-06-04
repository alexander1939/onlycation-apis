from jose import ExpiredSignatureError, JWTError
from app.cores.token import verify_token, create_access_token
from app.models.common.verification_code import VerificationCode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

async def get_new_access_token_if_expired(db: AsyncSession, token: str) -> str | None:
    try:
        verify_token(token)  
        return None

    except ExpiredSignatureError:
        from jose import jwt
        payload = jwt.get_unverified_claims(token)
        email = payload.get("email")

        if not email:
            return None

        result = await db.execute(
            select(VerificationCode).where(
                VerificationCode.email == email,
                VerificationCode.purpose == "refresh_token",
                VerificationCode.used == False,
                VerificationCode.expires_at > datetime.utcnow()
            ).order_by(VerificationCode.expires_at.desc())
        )
        record = result.scalar_one_or_none()
        if not record:
            return None

        try:
            refresh_payload = verify_token(record.code)
        except JWTError:
            return None

        new_access_token = create_access_token(data={
            "user_id": refresh_payload["user_id"],
            "email": refresh_payload["email"],
            "role": refresh_payload["role"],
            "statuses": refresh_payload["statuses"]
        })

        return new_access_token

    except JWTError:
        return None
