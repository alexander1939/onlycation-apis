from sqlalchemy.future import select  
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from app.models import User
from app.cores.token import create_access_token, create_refresh_token
from app.cores.security import verify_password
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.validation.exception import unexpected_exception
from app.models.common.verification_code import VerificationCode
from datetime import datetime, timedelta



async def authenticate_user(db: AsyncSession, email: str, password: str):
    result = await db.execute(
        select(User)
        .where(User.email == email)
        .options(joinedload(User.role), joinedload(User.status))  
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    return user

async def login_user(db: AsyncSession, email: str, password: str):
    try:
        user = await authenticate_user(db, email, password)

        token_data = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role.name,
            "statuses": user.status.name
        }

        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)

        code_entry = VerificationCode(
        email=user.email,
        role=user.role.name,
        purpose="refresh_token",
        code=refresh_token,
        used=False,
        expires_at=datetime.utcnow() + timedelta(days=7)
        )

        db.add(code_entry)
        await db.commit()

        return access_token, refresh_token, user

    except Exception as e:
        import traceback
        print("ERROR:", e)
        traceback.print_exc()
        raise e

    '''except HTTPException as e:
        raise e
    except Exception:
        await unexpected_exception()'''

    
