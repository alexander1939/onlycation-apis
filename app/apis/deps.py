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
from app.models.subscriptions.subscription import Subscription
from app.models.subscriptions.plan import Plan
from app.models.subscriptions.payment_subscription import PaymentSubscription
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


def require_access(
    privilege_name: str = None, 
    action: str = None, 
    subscription_required: bool = False,
    plan_type: str = None,
    require_both: bool = False
):
    """
    Función unificada para verificar acceso con privilegios y/o suscripciones.
    
    Args:
        privilege_name: Nombre del privilegio requerido (opcional)
        action: Acción del privilegio requerida (opcional)
        subscription_required: Si se requiere suscripción (opcional)
        plan_type: Tipo específico de plan requerido (opcional)
        require_both: Si se requieren ambos (privilegio Y suscripción) o solo uno (privilegio O suscripción)
    """
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

        has_privilege = False
        has_subscription = False

        if privilege_name and action:
            result = await db.execute(
                select(Privilege).where(Privilege.name == privilege_name, Privilege.action == action)
            )
            privilege = result.scalar_one_or_none()
            
            if privilege:
                result = await db.execute(
                    select(PrivilegeUser).where(
                        PrivilegeUser.user_id == user_id,
                        PrivilegeUser.privilege_id == privilege.id,
                        PrivilegeUser.status.has(name="active")
                    )
                )
                privilege_user = result.scalar_one_or_none()

                if not privilege_user:
                    result = await db.execute(
                        select(PrivilegeRole).join(Role).where(
                            Role.name == role_name,
                            PrivilegeRole.privilege_id == privilege.id,
                            PrivilegeRole.status.has(name="active")
                        )
                    )
                    privilege_role = result.scalar_one_or_none()
                    has_privilege = privilege_role is not None
                else:
                    has_privilege = True

        if subscription_required:
            query = select(Subscription).join(Plan).where(
                Subscription.user_id == user_id,
                Subscription.status.has(name="active"),
                Subscription.end_date > datetime.utcnow()
            )
            
            if plan_type:
                query = query.where(Plan.guy == plan_type)
            
            result = await db.execute(query)
            subscription = result.scalar_one_or_none()
            has_subscription = subscription is not None

        if privilege_name and action and subscription_required:
            if require_both:
                if not has_privilege or not has_subscription:
                    error_msg = []
                    if not has_privilege:
                        error_msg.append(f"privilege '{privilege_name}:{action}'")
                    if not has_subscription:
                        error_msg.append(f"active subscription{f' for plan type: {plan_type}' if plan_type else ''}")
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Both {' and '.join(error_msg)} required"
                    )
            else:
                if not has_privilege and not has_subscription:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Either privilege '{privilege_name}:{action}' or active subscription{f' for plan type: {plan_type}' if plan_type else ''} required"
                    )
        elif privilege_name and action:
            if not has_privilege:
                raise HTTPException(status_code=403, detail="You don't have permission for this action")
        elif subscription_required:
            if not has_subscription:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Active subscription required{f' for plan type: {plan_type}' if plan_type else ''}"
                )
        
        return payload

    return checker


def require_privilege(privilege_name: str, action: str):
    """Verifica solo privilegio"""
    return require_access(privilege_name=privilege_name, action=action)

def require_subscription(plan_type: str = None):
    """Verifica solo suscripción"""
    return require_access(subscription_required=True, plan_type=plan_type)

def require_privilege_and_subscription(privilege_name: str, action: str, plan_type: str = None):
    """Verifica privilegio Y suscripción"""
    return require_access(
        privilege_name=privilege_name, 
        action=action, 
        subscription_required=True, 
        plan_type=plan_type, 
        require_both=True
    )

def require_privilege_or_subscription(privilege_name: str, action: str, plan_type: str = None):
    """Verifica privilegio O suscripción"""
    return require_access(
        privilege_name=privilege_name, 
        action=action, 
        subscription_required=True, 
        plan_type=plan_type, 
        require_both=False
    )

