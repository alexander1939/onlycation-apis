from sqlalchemy.future import select  
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from app.models import User
from app.cores.token import create_access_token
from app.cores.security import verify_password
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.validation.exception import unexpected_exception



async def authenticate_user(db: AsyncSession, email: str, password: str):
    result = await db.execute(
        select(User)
        .where(User.email == email)
        .options(joinedload(User.roles), joinedload(User.statuses))  
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    return user

async def login_user(db: AsyncSession, email: str, password: str):
    try:
        user = await authenticate_user(db, email, password)
        token = create_access_token(data={
            "user_id": user.id,
            "email": user.email,
            "role": user.roles.name,  
            "statuses": user.statuses.name  
        })
        return token, user
    
    except HTTPException as e:
        raise e
    except Exception:
        await unexpected_exception()

    '''except Exception as e:
        import traceback
        print("ERROR:", e)
        traceback.print_exc()
        raise e  '''
