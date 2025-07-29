import asyncio
from sqlalchemy import select
from app.cores.db import async_session
from app.models.common.status import Status
from app.models.common.role import Role
from app.models.subscriptions.plan import Plan
from app.external.stripe_config import stripe_config
import stripe
from datetime import datetime

async def create_premium_plan():
    async with async_session() as session:
        role_query = await session.execute(select(Role).where(Role.name == "teacher"))
        role = role_query.scalar_one_or_none()
        if not role:
            print("Rol 'teacher' no encontrado.")
            return

        status_query = await session.execute(select(Status).where(Status.name == "active"))
        status = status_query.scalar_one_or_none()
        if not status:
            print("Status 'active' no encontrado.")
            return

        existing_plan_query = await session.execute(
            select(Plan).where(
                Plan.name == "plan Premium",
                Plan.role_id == role.id
            )
        )
        existing_plan = existing_plan_query.scalar_one_or_none()

        if existing_plan:
            print("Ya existe un plan con ese nombre y rol. No se creará otro.")
            return

        product = stripe.Product.create(
            name="plan Premium",
            description="Plan mensual para docentes con acceso completo a las herramientas"
        )

        price = stripe.Price.create(
            unit_amount=19900, 
            currency="mxn",
            recurring={"interval": "month"},
            product=product.id
        )

        plan = Plan(
            guy="premium docente",
            name="plan Premium",
            description="Acceso completo a las herramientas premium para docentes.",
            price=199,  
            duration="1 mes",
            stripe_product_id=product.id,
            stripe_price_id=price.id,
            role_id=role.id,
            status_id=status.id
        )

        session.add(plan)
        await session.commit()
        print("Plan Premium Docente creado correctamente.")
