from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from app.models.subscriptions import Plan
from app.models.common import Status
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.validation.exception import unexpected_exception
from app.schemas.suscripcion.plan_schema import CreatePlanRequest, UpdatePlanRequest

async def create_plan(db: AsyncSession, plan_data: CreatePlanRequest):
    try:
        # Verificar que no existe un plan con el mismo nombre
        existing_plan_result = await db.execute(
            select(Plan).where(Plan.name == plan_data.name)
        )
        existing_plan = existing_plan_result.scalar_one_or_none()
        if existing_plan:
            raise HTTPException(status_code=400, detail="A plan with this name already exists")

        # Verificar que el rol existe
        from app.models.common import Role
        role_result = await db.execute(select(Role).where(Role.id == plan_data.role_id))
        role = role_result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Obtener el status "active"
        status_result = await db.execute(select(Status).where(Status.name == "active"))
        status = status_result.scalar_one_or_none()
        if not status:
            raise HTTPException(status_code=404, detail="Active status not found")

        # Crear el plan
        new_plan = Plan(
            guy=plan_data.guy,
            name=plan_data.name,
            description=plan_data.description,
            price=plan_data.price,
            duration=plan_data.duration,
            role_id=plan_data.role_id,
            status_id=status.id
        )

        db.add(new_plan)
        await db.commit()
        
        return new_plan

    except HTTPException as e:
        # Re-lanzar HTTPException para que llegue al usuario
        raise e
    except Exception as e:
        # Para errores internos del servidor, usar unexpected_exception
        await unexpected_exception()

async def update_plan(db: AsyncSession, plan_id: int, plan_data: UpdatePlanRequest):
    try:
        # Buscar el plan
        result = await db.execute(
            select(Plan)
            .where(Plan.id == plan_id)
            .options(joinedload(Plan.status))
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Verificar que el plan esté activo
        if plan.status.name != "active":
            # Si el plan está inactivo, solo permitir cambiar el status
            if (plan_data.guy != plan.guy or 
                plan_data.name != plan.name or 
                plan_data.description != plan.description or 
                plan_data.price != plan.price or 
                plan_data.duration != plan.duration or 
                plan_data.role_id != plan.role_id):
                raise HTTPException(status_code=400, detail="Cannot edit inactive plan fields. Only status can be changed")

        # Verificar que no existe otro plan con el mismo nombre (si se está cambiando el nombre)
        if plan_data.name != plan.name:
            existing_plan_result = await db.execute(
                select(Plan).where(Plan.name == plan_data.name)
            )
            existing_plan = existing_plan_result.scalar_one_or_none()
            if existing_plan:
                raise HTTPException(status_code=400, detail="A plan with this name already exists")

        # Verificar que el rol existe
        from app.models.common import Role
        role_result = await db.execute(select(Role).where(Role.id == plan_data.role_id))
        role = role_result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Verificar que el status existe
        status_result = await db.execute(select(Status).where(Status.id == plan_data.status_id))
        status = status_result.scalar_one_or_none()
        if not status:
            raise HTTPException(status_code=404, detail="Status not found")

        # Actualizar todos los campos
        plan.guy = plan_data.guy # type: ignore
        plan.name = plan_data.name # type: ignore
        plan.description = plan_data.description # type: ignore
        plan.price = plan_data.price # type: ignore
        plan.duration = plan_data.duration # type: ignore
        plan.role_id = plan_data.role_id # type: ignore
        plan.status_id = plan_data.status_id # type: ignore

        await db.commit()
        await db.refresh(plan)
        
        return plan

    except HTTPException as e:
        # Re-lanzar HTTPException para que llegue al usuario
        raise e
    except Exception as e:
        # Para errores internos del servidor, usar unexpected_exception
        await unexpected_exception()

async def get_all_plans(db: AsyncSession, skip: int = 0, limit: int = 100):
    try:
        result = await db.execute(
            select(Plan)
            .options(joinedload(Plan.role))
            .offset(skip)
            .limit(limit)
        )
        plans = result.scalars().all()
        
        return plans

    except Exception as e:
        # Para errores internos del servidor, usar unexpected_exception
        await unexpected_exception()

async def get_plan_by_id(db: AsyncSession, plan_id: int):
    try:
        result = await db.execute(
            select(Plan)
            .where(Plan.id == plan_id)
            .options(joinedload(Plan.role), joinedload(Plan.status))
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        return plan

    except HTTPException as e:
        # Re-lanzar HTTPException para que llegue al usuario
        raise e
    except Exception as e:
        # Para errores internos del servidor, usar unexpected_exception
        await unexpected_exception() 