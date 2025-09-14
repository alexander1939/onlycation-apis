from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from app.models.subscriptions.subscription import Subscription
from app.models.subscriptions.payment_subscription import PaymentSubscription
from app.models.subscriptions import Plan
from app.models.common import Status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

async def check_existing_payment_by_session(db: AsyncSession, session_id: str):
    """Verifica si ya existe un pago procesado con este session_id"""
    existing_payment_result = await db.execute(
        select(PaymentSubscription).where(
            PaymentSubscription.stripe_payment_intent_id == session_id
        )
    )
    return existing_payment_result.scalars().first()

async def check_active_subscription_for_plan(db: AsyncSession, user_id: int, plan_id: int):
    """Verifica si el usuario ya tiene una suscripción activa para este plan"""
    now = datetime.utcnow()
    
    existing_subscription_result = await db.execute(
        select(Subscription)
        .options(joinedload(Subscription.plan))
        .join(Status)
        .where(
            Subscription.user_id == user_id,
            Subscription.plan_id == plan_id,
            Status.name == "active",
            Subscription.end_date > now
        )
    )
    return existing_subscription_result.scalars().first()

async def validate_subscription_eligibility(db: AsyncSession, user_id: int, plan_guy: str):
    """Valida si el usuario puede suscribirse a un plan específico"""
    from datetime import datetime
    
    # Buscar el plan
    plan_result = await db.execute(
        select(Plan).where(Plan.guy == plan_guy, Plan.status.has(name="active"))
    )
    plan = plan_result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado o inactivo")

    # Verificar suscripción activa del usuario
    try:
        current_subscription_result = await db.execute(
            select(Subscription)
            .options(joinedload(Subscription.plan))
            .join(Status)
            .where(
                Subscription.user_id == user_id,
                Status.name == "active"
            )
            .order_by(Subscription.start_date.desc())
        )
        current_subscription = current_subscription_result.scalars().first()
        
        if current_subscription:
            # Verificar si la suscripción actual ha expirado
            now = datetime.utcnow()
            
            # Si ya tiene el mismo plan Y está activo Y no ha expirado, no permitir duplicado
            if (current_subscription.plan.guy == plan_guy and 
                current_subscription.end_date > now):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Ya tienes una suscripción activa al plan {current_subscription.plan.name} que expira el {current_subscription.end_date.strftime('%Y-%m-%d')}"
                )
            
            # Si tiene plan gratuito y quiere premium, permitir agregar nueva suscripción
            if current_subscription.plan.name == "Plan Gratuito" and plan.name != "Plan Gratuito":
                # Mantener plan gratuito activo, agregar nueva suscripción premium
                # Cuando expire el premium, automáticamente volverá al gratuito
                pass
                
    except Exception as e:
        # Si no hay suscripción activa, continuar normalmente
        pass
    
    return plan
