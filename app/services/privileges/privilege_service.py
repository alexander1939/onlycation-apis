from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.privileges.privilege import Privilege
from app.models.common.status import Status
from app.schemas.privileges.privilege_shema import PrivilegeCreateRequest, PrivilegeResponse
from datetime import datetime

from app.services.validation.exception import unexpected_exception


async def create_privilege_service(db: AsyncSession, data: PrivilegeCreateRequest) -> Privilege: # type: ignore
    try:
        # Verificar que no exista un privilegio con el mismo nombre y acción
        result = await db.execute(
            select(Privilege).where(
                Privilege.name == data.name,
                Privilege.action == data.action
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Privilege already exists.")

        # Buscar el status activo
        result_status = await db.execute(
            select(Status).where(Status.name == "active")
        )
        status = result_status.scalar_one_or_none()
        if not status:
            raise HTTPException(status_code=404, detail="Status 'active' not found.")

        # Crear el nuevo privilegio
        new_privilege = Privilege(
            name=data.name,
            action=data.action,
            description=data.description,
            status_id=status.id
        )

        db.add(new_privilege)
        await db.commit()
        await db.refresh(new_privilege)
        return new_privilege

    except HTTPException as e:
        raise e
    except Exception:
        await unexpected_exception()
