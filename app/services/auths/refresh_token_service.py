from datetime import datetime
from jose import JWTError
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.models.common.verification_code import VerificationCode
from app.cores.token import verify_token, create_access_token
from app.models import User
from app.models.users.preference import Preference

async def refresh_access_token(db: AsyncSession, refresh_token: str):
    """
    Verify refresh token, ensure it's valid in DB, fetch latest user role/status,
    rebuild access token, and return (access_token, user, preference_id).
    """
    try:
        payload = verify_token(refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    email = payload.get("email")
    user_id = payload.get("user_id")
    if not email or not user_id:
        raise HTTPException(status_code=400, detail="Error in token payload")

    # Validate refresh token record (not used, not expired)
    result = await db.execute(
        select(VerificationCode).where(
            VerificationCode.email == email,
            VerificationCode.purpose == "refresh_token",
            VerificationCode.used == False,
            VerificationCode.expires_at > datetime.utcnow()
        ).order_by(VerificationCode.expires_at.desc())
    )
    record = result.scalar_one_or_none()
    if not record or record.code != refresh_token:  # type: ignore
        raise HTTPException(status_code=401, detail="Update token invalid or not found")

    # Load user with current role/status
    user_result = await db.execute(
        select(User).options(joinedload(User.role), joinedload(User.status)).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token_data = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role.name if getattr(user, "role", None) else None,
        "statuses": user.status.name if getattr(user, "status", None) else None,
    }
    access_token = create_access_token(data=token_data)

    # Get preference_id for teachers
    preference_id = None
    try:
        if user.role and user.role.name == "teacher":
            pref_result = await db.execute(select(Preference).where(Preference.user_id == user.id))
            pref = pref_result.scalar_one_or_none()
            if pref:
                preference_id = pref.id
    except Exception:
        preference_id = None

    return access_token, user, preference_id
