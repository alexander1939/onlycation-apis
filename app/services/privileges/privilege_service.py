from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.privileges.privilege import Privilege
from app.models.common.status import Status
from app.schemas.privileges.privilege_shema import PrivilegeCreateRequest, PrivilegeUpdateRequest, PrivilegeResponse
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


async def update_privilege_service(db: AsyncSession, privilege_id: int, data: PrivilegeUpdateRequest) -> Privilege: # type: ignore
    try:
        # Buscar el privilegio a actualizar
        result = await db.execute(
            select(Privilege).where(Privilege.id == privilege_id)
        )
        privilege = result.scalar_one_or_none()
        if not privilege:
            raise HTTPException(status_code=404, detail="Privilege not found.")

        # Verificar si se está cambiando nombre y acción, y si ya existe otro con esos valores
        if data.name is not None and data.action is not None:
            result = await db.execute(
                select(Privilege).where(
                    Privilege.name == data.name,
                    Privilege.action == data.action,
                    Privilege.id != privilege_id
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=400, detail="Privilege with this name and action already exists.")

        # Verificar si el status existe (si se está actualizando)
        if data.status_id is not None:
            result_status = await db.execute(
                select(Status).where(Status.id == data.status_id)
            )
            status = result_status.scalar_one_or_none()
            if not status:
                raise HTTPException(status_code=404, detail="Status not found.")

        # Actualizar los campos proporcionados
        if data.name is not None:
            privilege.name = data.name # type: ignore
        if data.action is not None:
            privilege.action = data.action # type: ignore
        if data.description is not None:
            privilege.description = data.description # type: ignore
        if data.status_id is not None:
            privilege.status_id = data.status_id # type: ignore

        await db.commit()
        await db.refresh(privilege)
        return privilege

    except HTTPException as e:
        raise e
    except Exception:
        await unexpected_exception()
