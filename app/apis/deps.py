from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.cores.db import async_session 
from fastapi import Depends, HTTPException, status, Header
from typing import Optional
from app.cores.token import verify_token

from app.models.users import User
from sqlalchemy.future import select
from jose import JWTError, jwt
from app.cores.token import SECRET_KEY, ALGORITHM
from app.models.common.verification_code import VerificationCode
from app.models.common.role import Role
from app.models.common.status import Status
from app.models.privileges.privilege import Privilege
from app.models.privileges.privilege_role import PrivilegeRole
from app.models.privileges.privilege_user import PrivilegeUser
from datetime import datetime
"""
Este archivo define la función `get_db`, que proporciona una sesión de base de datos asincrónica.
Se usa como dependencia en rutas de FastAPI para interactuar con la base de datos sin preocuparse
por abrir o cerrar la conexión manualmente.
"""
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = async_session()
    try:
        yield session
    finally:
        await session.close()

async def public_access():
    pass

async def auth_required(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token not provided")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid token format")

        payload = verify_token(token)
        return payload
    except (ValueError, JWTError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_privilege(privilege_name: str, action: str):
    async def checker(
        authorization: Optional[str] = Header(None),
        db: AsyncSession = Depends(get_db)
    ):
        if not authorization:
            raise HTTPException(status_code=401, detail="Token not provided")
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise HTTPException(status_code=401, detail="Invalid token format")

            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except (ValueError, JWTError):
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = payload.get("user_id")
        role_name = payload.get("role")

        if not user_id or not role_name:
            raise HTTPException(status_code=403, detail="Invalid data in token")

        result = await db.execute(
            select(Privilege).where(Privilege.name == privilege_name, Privilege.action == action)
        )
        privilege = result.scalar_one_or_none()
        if not privilege:
            raise HTTPException(status_code=403, detail="Privilege not defined")

        result = await db.execute(
            select(PrivilegeUser).where(
                PrivilegeUser.user_id == user_id,
                PrivilegeUser.privilege_id == privilege.id,
                PrivilegeUser.status.has(name="active")
            )
        )
        privilege_user = result.scalar_one_or_none()

        if privilege_user:
            return payload 

        result = await db.execute(
            select(PrivilegeRole).join(Role).where(
                Role.name == role_name,
                PrivilegeRole.privilege_id == privilege.id,
                PrivilegeRole.status.has(name="active")
            )
        )
        privilege_role = result.scalar_one_or_none()

        if not privilege_role:
            raise HTTPException(status_code=403, detail="You don't have permission for this action")
        
        return payload 

    return checker

