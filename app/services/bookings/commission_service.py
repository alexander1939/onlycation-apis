from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subscriptions.subscription import Subscription
from app.models.subscriptions.plan import Plan
from app.models.common.status import Status
from app.models.teachers.wallet import Wallet
from fastapi import HTTPException

async def get_teacher_commission_rate(db: AsyncSession, teacher_id: int):
    """Obtiene el porcentaje de comisión según el plan del docente"""
    print(f"🔍 DEBUG: Buscando comisión para teacher_id: {teacher_id}")
    
    # Buscar suscripción activa del docente con join explícito
    subscription_result = await db.execute(
        select(Subscription, Plan)
        .join(Plan, Subscription.plan_id == Plan.id)
        .join(Status, Subscription.status_id == Status.id)
        .where(
            Subscription.user_id == teacher_id,
            Status.name == "active"
        )
        .order_by(Subscription.start_date.desc())
    )
    result = subscription_result.first()
    
    if not result:
        # Si no tiene suscripción, usar plan gratuito por defecto
        print(f"⚠️ DEBUG: No se encontró suscripción activa para teacher_id {teacher_id}, usando plan gratuito (60%)")
        return 60.00
    
    subscription, plan = result
    print(f"📋 DEBUG: Suscripción encontrada - Plan: {plan.name}, ID: {plan.id}")
    
    # Plan gratuito = 60% comisión, Plan premium = 0% comisión
    if plan.name == "Plan Gratuito":
        print(f"💰 DEBUG: Plan Gratuito detectado - Comisión: 60%")
        return 60.00
    elif plan.name == "Plan Premium":
        print(f"⭐ DEBUG: Plan Premium detectado - Comisión: 0%")
        return 0.00
    else:
        print(f"❓ DEBUG: Plan desconocido '{plan.name}' - Usando comisión por defecto: 60%")
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
    
    print(f"🧮 DEBUG: Commission calculation:")
    print(f"   - Total: {total_amount_cents} centavos")
    print(f"   - Commission rate: {commission_rate}%")
    print(f"   - Commission amount: {commission_amount} centavos")
    print(f"   - Teacher amount: {teacher_amount} centavos")
    
    return commission_amount, teacher_amount
