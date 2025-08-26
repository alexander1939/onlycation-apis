import asyncio
from sqlalchemy import select
from app.cores.db import async_session
from app.models.common.status import Status
from app.models.common.role import Role
from app.models.subscriptions.plan import Plan
from app.models.subscriptions.benefit import Benefit
from app.models.subscriptions.plan_benefit import plan_benefits
from app.external.stripe_config import stripe_config
import stripe
from datetime import datetime

async def create_premium_plan():
    """Crear plan premium para docentes con beneficios incluidos"""
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
        await session.flush()  # Para obtener el ID del plan
        
        # Crear beneficios del plan premium
        benefits_data = [
            {
                "name": "Perfil Prioritario",
                "description": "Tu perfil aparecerá primero en las búsquedas de estudiantes"
            },
            {
                "name": "0% Comisión",
                "description": "No pagas comisión por las clases que impartas"
            },
            {
                "name": "Soporte Premium",
                "description": "Acceso prioritario al soporte técnico y pedagógico"
            },
            {
                "name": "Estadísticas Avanzadas",
                "description": "Acceso a métricas detalladas de tus clases y estudiantes"
            }
        ]
        
        created_benefits = []
        for benefit_data in benefits_data:
            # Verificar si el beneficio ya existe
            existing_benefit_query = await session.execute(
                select(Benefit).where(Benefit.name == benefit_data["name"])
            )
            existing_benefit = existing_benefit_query.scalar_one_or_none()
            
            if not existing_benefit:
                benefit = Benefit(
                    name=benefit_data["name"],
                    description=benefit_data["description"],
                    status_id=status.id
                )
                session.add(benefit)
                await session.flush()
                created_benefits.append(benefit)
                print(f"Beneficio '{benefit_data['name']}' creado.")
            else:
                created_benefits.append(existing_benefit)
                print(f"Beneficio '{benefit_data['name']}' ya existe.")
        
        # Asociar beneficios al plan
        for benefit in created_benefits:
            # Verificar si la relación ya existe
            existing_relation_query = await session.execute(
                select(plan_benefits).where(
                    plan_benefits.c.plan_id == plan.id,
                    plan_benefits.c.benefit_id == benefit.id
                )
            )
            existing_relation = existing_relation_query.first()
            
            if not existing_relation:
                # Insertar en la tabla intermedia
                await session.execute(
                    plan_benefits.insert().values(
                        plan_id=plan.id,
                        benefit_id=benefit.id
                    )
                )
                print(f"Beneficio '{benefit.name}' asociado al plan.")
            else:
                print(f"Beneficio '{benefit.name}' ya está asociado al plan.")
        
        await session.commit()
        print("Plan Premium Docente creado correctamente con todos sus beneficios.")


async def create_free_plan():
    """Crear plan gratuito para docentes (plan por defecto)"""
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
                Plan.name == "Plan Gratuito",
                Plan.role_id == role.id
            )
        )
        existing_plan = existing_plan_query.scalar_one_or_none()

        if existing_plan:
            print("Ya existe un plan gratuito. No se creará otro.")
            return

        # No necesita producto/precio de Stripe porque es gratuito
        plan = Plan(
            guy="gratuito docente",
            name="Plan Gratuito",
            description="Plan básico gratuito para docentes que se registran por primera vez.",
            price=0,  
            duration="ilimitado",
            stripe_product_id=None,  # No hay producto Stripe para plan gratuito
            stripe_price_id=None,    # No hay precio Stripe para plan gratuito
            role_id=role.id,
            status_id=status.id
        )

        session.add(plan)
        await session.flush()  # Para obtener el ID del plan
        
        # Crear beneficios del plan gratuito (básicos)
        benefits_data = [
            {
                "name": "Perfil Básico",
                "description": "Tu perfil aparece en las búsquedas de estudiantes"
            },
            {
                "name": "5% Comisión",
                "description": "Comisión estándar del 5% por las clases que impartas"
            },
            {
                "name": "Soporte Básico",
                "description": "Acceso al soporte técnico estándar"
            }
        ]
        
        created_benefits = []
        for benefit_data in benefits_data:
            # Verificar si el beneficio ya existe
            existing_benefit_query = await session.execute(
                select(Benefit).where(Benefit.name == benefit_data["name"])
            )
            existing_benefit = existing_benefit_query.scalar_one_or_none()
            
            if not existing_benefit:
                benefit = Benefit(
                    name=benefit_data["name"],
                    description=benefit_data["description"],
                    status_id=status.id
                )
                session.add(benefit)
                await session.flush()
                created_benefits.append(benefit)
                print(f"Beneficio '{benefit_data['name']}' creado.")
            else:
                created_benefits.append(existing_benefit)
                print(f"Beneficio '{benefit_data['name']}' ya existe.")
        
        # Asociar beneficios al plan
        for benefit in created_benefits:
            # Verificar si la relación ya existe
            existing_relation_query = await session.execute(
                select(plan_benefits).where(
                    plan_benefits.c.plan_id == plan.id,
                    plan_benefits.c.benefit_id == benefit.id
                )
            )
            existing_relation = existing_relation_query.first()
            
            if not existing_relation:
                # Insertar en la tabla intermedia
                await session.execute(
                    plan_benefits.insert().values(
                        plan_id=plan.id,
                        benefit_id=benefit.id
                    )
                )
                print(f"Beneficio '{benefit.name}' asociado al plan gratuito.")
            else:
                print(f"Beneficio '{benefit.name}' ya está asociado al plan gratuito.")
        
        await session.commit()
        print("Plan Gratuito Docente creado correctamente con todos sus beneficios.")


async def create_all_plans():
    """Crear todos los planes (gratuito y premium)"""
    await create_free_plan()
    await create_premium_plan()


if __name__ == "__main__":
    asyncio.run(create_all_plans())
