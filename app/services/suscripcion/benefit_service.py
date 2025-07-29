from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from app.models.subscriptions import Benefit
from app.models.common import Status
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.validation.exception import unexpected_exception
from app.schemas.suscripcion.benefit_schema import CreateBenefitRequest, UpdateBenefitRequest

async def create_benefit(db: AsyncSession, benefit_data: CreateBenefitRequest):
    try:
        existing_benefit_result = await db.execute(
            select(Benefit).where(Benefit.name == benefit_data.name)
        )
        existing_benefit = existing_benefit_result.scalar_one_or_none()
        if existing_benefit:
            raise HTTPException(status_code=400, detail="A benefit with this name already exists")

        status_result = await db.execute(select(Status).where(Status.name == "active"))
        status = status_result.scalar_one_or_none()
        if not status:
            raise HTTPException(status_code=404, detail="Active status not found")

        new_benefit = Benefit(
            name=benefit_data.name,
            description=benefit_data.description,
            status_id=status.id
        )

        db.add(new_benefit)
        await db.commit()
        
        return new_benefit

    except HTTPException as e:
        raise e
    except Exception as e:
        await unexpected_exception()

async def update_benefit(db: AsyncSession, benefit_id: int, benefit_data: UpdateBenefitRequest):
    try:
        result = await db.execute(
            select(Benefit)
            .where(Benefit.id == benefit_id)
            .options(joinedload(Benefit.status))
        )
        benefit = result.scalar_one_or_none()
        
        if not benefit:
            raise HTTPException(status_code=404, detail="Benefit not found")

        # Verificar que el beneficio esté activo
        if benefit.status.name != "active":
            # Si el beneficio está inactivo, solo permitir cambiar el status
            if (benefit_data.name != benefit.name or 
                benefit_data.description != benefit.description):
                raise HTTPException(status_code=400, detail="Cannot edit inactive benefit fields. Only status can be changed")

        # Verificar que no existe otro beneficio con el mismo nombre (si se está cambiando el nombre)
        if benefit_data.name != benefit.name:
            existing_benefit_result = await db.execute(
                select(Benefit).where(Benefit.name == benefit_data.name)
            )
            existing_benefit = existing_benefit_result.scalar_one_or_none()
            if existing_benefit:
                raise HTTPException(status_code=400, detail="A benefit with this name already exists")

        # Verificar que el status existe
        status_result = await db.execute(select(Status).where(Status.id == benefit_data.status_id))
        status = status_result.scalar_one_or_none()
        if not status:
            raise HTTPException(status_code=404, detail="Status not found")

        # Actualizar todos los campos
        benefit.name = benefit_data.name # type: ignore
        benefit.description = benefit_data.description # type: ignore
        benefit.status_id = benefit_data.status_id # type: ignore

        await db.commit()
        await db.refresh(benefit)
        
        return benefit

    except HTTPException as e:
        # Re-lanzar HTTPException para que llegue al usuario
        raise e
    except Exception as e:
        # Para errores internos del servidor, usar unexpected_exception
        await unexpected_exception()

async def get_all_benefits(db: AsyncSession, skip: int = 0, limit: int = 100):
    try:
        result = await db.execute(
            select(Benefit)
            .options(joinedload(Benefit.status))
            .offset(skip)
            .limit(limit)
        )
        benefits = result.scalars().all()
        
        return benefits

    except Exception as e:
        # Para errores internos del servidor, usar unexpected_exception
        await unexpected_exception()

async def get_benefit_by_id(db: AsyncSession, benefit_id: int):
    try:
        result = await db.execute(
            select(Benefit)
            .where(Benefit.id == benefit_id)
            .options(joinedload(Benefit.status))
        )
        benefit = result.scalar_one_or_none()
        
        if not benefit:
            raise HTTPException(status_code=404, detail="Benefit not found")
        
        return benefit

    except HTTPException as e:
        # Re-lanzar HTTPException para que llegue al usuario
        raise e
    except Exception as e:
        # Para errores internos del servidor, usar unexpected_exception
        await unexpected_exception() 