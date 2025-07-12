from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.subscriptions import Benefit
from app.models.common import Status
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.validation.exception import unexpected_exception
from app.schemas.suscripcion.benefit_schema import CreateBenefitRequest

async def create_benefit(db: AsyncSession, benefit_data: CreateBenefitRequest):
    try:
        # Verificar que no existe un beneficio con el mismo nombre
        existing_benefit_result = await db.execute(
            select(Benefit).where(Benefit.name == benefit_data.name)
        )
        existing_benefit = existing_benefit_result.scalar_one_or_none()
        if existing_benefit:
            raise HTTPException(status_code=400, detail="A benefit with this name already exists")

        # Obtener el status "active"
        status_result = await db.execute(select(Status).where(Status.name == "active"))
        status = status_result.scalar_one_or_none()
        if not status:
            raise HTTPException(status_code=404, detail="Active status not found")

        # Crear el beneficio
        new_benefit = Benefit(
            name=benefit_data.name,
            description=benefit_data.description,
            status_id=status.id
        )

        db.add(new_benefit)
        await db.commit()
        
        return new_benefit

    except HTTPException as e:
        # Re-lanzar HTTPException para que llegue al usuario
        raise e
    except Exception as e:
        # Para errores internos del servidor, usar unexpected_exception
        await unexpected_exception() 