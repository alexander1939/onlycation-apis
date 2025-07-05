from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.privileges.privilege import Privilege
from app.models.common.status import Status
from app.schemas.privileges.privilege_shema import PrivilegeCreateRequest, PrivilegeUpdateRequest, PrivilegeStatusRequest, PrivilegeResponse
from datetime import datetime
from typing import Sequence

from app.services.validation.exception import unexpected_exception
from app.services.utils.pagination_service import PaginationService


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

        # Verificar si ya existe otro privilegio con el mismo nombre y acción
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

        # Actualizar todos los campos
        privilege.name = data.name # type: ignore
        privilege.action = data.action # type: ignore
        privilege.description = data.description # type: ignore

        await db.commit()
        await db.refresh(privilege)
        return privilege

    except HTTPException as e:
        raise e
    except Exception:
        await unexpected_exception()


async def get_privilege_service(db: AsyncSession, privilege_id: int) -> Privilege: # type: ignore
    try:
        result = await db.execute(
            select(Privilege).where(Privilege.id == privilege_id)
        )
        privilege = result.scalar_one_or_none()
        if not privilege:
            raise HTTPException(status_code=404, detail="Privilege not found.")
        
        return privilege

    except HTTPException as e:
        raise e
    except Exception:
        await unexpected_exception()


async def get_all_privileges_service(db: AsyncSession, offset: int = 0, limit: int = 6) -> dict: # type: ignore
    try:
        return await PaginationService.get_paginated_data(
            db=db,
            model=Privilege,
            offset=offset,
            limit=limit
        )
    except HTTPException as e:
        raise e
    except Exception:
        await unexpected_exception()


async def change_privilege_status_service(db: AsyncSession, privilege_id: int, data: PrivilegeStatusRequest) -> Privilege: # type: ignore
    try:
        # Buscar el privilegio
        result = await db.execute(
            select(Privilege).where(Privilege.id == privilege_id)
        )
        privilege = result.scalar_one_or_none()
        if not privilege:
            raise HTTPException(status_code=404, detail="Privilege not found.")

        # Verificar que el status existe
        result_status = await db.execute(
            select(Status).where(Status.id == data.status_id)
        )
        status = result_status.scalar_one_or_none()
        if not status:
            raise HTTPException(status_code=404, detail="Status not found.")

        # Cambiar el status del privilegio
        privilege.status_id = data.status_id # type: ignore

        await db.commit()
        await db.refresh(privilege)
        return privilege

    except HTTPException as e:
        raise e
    except Exception:
        await unexpected_exception()
