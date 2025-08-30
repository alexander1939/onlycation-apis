from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subscriptions.subscription import Subscription
from app.models.subscriptions.plan import Plan
from app.models.subscriptions.benefit import Benefit
from app.models.common.status import Status
from app.models.teachers.wallet import Wallet
from fastapi import HTTPException
import re

async def get_teacher_commission_rate(db: AsyncSession, teacher_id: int):
    """Obtiene el porcentaje de comisión desde la base de datos usando plan_benefit"""
    
    # Buscar TODAS las suscripciones activas del docente con sus beneficios
    subscription_result = await db.execute(
        select(Subscription, Plan, Benefit)
        .join(Plan, Subscription.plan_id == Plan.id)
        .join(Status, Subscription.status_id == Status.id)
        .join(Plan.benefits)  # Join con los beneficios del plan
        .where(
            Subscription.user_id == teacher_id,
            Status.name == "active",
            Benefit.name.like("%Comisión%")  # Solo beneficios de comisión
        )
        .order_by(Subscription.start_date.desc())
    )
    all_subscriptions = subscription_result.all()
    
    if not all_subscriptions:
        # Si no tiene suscripción, buscar el plan gratuito por defecto
        
        # Buscar beneficio de comisión del plan gratuito
        default_result = await db.execute(
            select(Plan, Benefit)
            .join(Plan.benefits)
            .where(
                Plan.name == "Plan Gratuito",
                Benefit.name.like("%Comisión%")
            )
        )
        default_plan_benefit = default_result.first()
        
        if default_plan_benefit:
            _, default_benefit = default_plan_benefit
            commission_rate = extract_commission_from_benefit(default_benefit.name)
            return commission_rate
        else:
            return 60.00
    
    # Mostrar todas las suscripciones encontradas
    
    best_commission_rate = None
    best_plan_name = None
    
    for i, (subscription, plan, benefit) in enumerate(all_subscriptions):
        commission_rate = extract_commission_from_benefit(benefit.name)
        
        # Seleccionar la menor comisión (mejor para el docente)
        if best_commission_rate is None or commission_rate < best_commission_rate:
            best_commission_rate = commission_rate
            best_plan_name = plan.name
    
    
    return best_commission_rate

def extract_commission_from_benefit(benefit_name: str) -> float:
    """Extrae el porcentaje de comisión del nombre del beneficio"""
    # Buscar patrones como "60% Comisión" o "0% Comisión"
    match = re.search(r'(\d+(?:\.\d+)?)%', benefit_name)
    if match:
        return float(match.group(1))
    
    # Si no encuentra número, asumir por defecto
    if "0%" in benefit_name or "Sin comisión" in benefit_name.lower():
        return 0.00
    else:
        return 60.00  # Por defecto

async def get_teacher_wallet(db: AsyncSession, teacher_id: int):
    """Obtiene la cartera Stripe del docente"""
    wallet_result = await db.execute(
        select(Wallet).where(Wallet.user_id == teacher_id)
    )
    wallet = wallet_result.scalar_one_or_none()
    
    if not wallet or not wallet.stripe_account_id:
        raise HTTPException(
            status_code=400, 
            detail="El docente no tiene configurada su cuenta de Stripe Connect"
        )
    
    if wallet.stripe_bank_status != "active":
        raise HTTPException(
            status_code=400,
            detail="La cuenta Stripe del docente no está activa"
        )
    
    return wallet

def calculate_commission_amounts(total_amount_cents: int, commission_rate: float):
    """Calcula los montos de comisión y para el docente"""
    commission_amount = int(total_amount_cents * (commission_rate / 100))
    teacher_amount = total_amount_cents - commission_amount
    
  
    
    return commission_amount, teacher_amount
