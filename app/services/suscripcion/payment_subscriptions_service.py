from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from app.configs import settings
from app.models.subscriptions import Benefit, Plan
from app.models.subscriptions.payment_subscription import PaymentSubscription
from app.models.users import User
from app.models.common import Status
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.validation.exception import unexpected_exception
from app.schemas.suscripcion.benefit_schema import CreateBenefitRequest, UpdateBenefitRequest

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import stripe
import os

async def subscribe_user_to_plan(db: AsyncSession, user: User, plan_guy: str):
    plan = await db.execute(select(Plan).where(Plan.guy == plan_guy, Plan.status.has(name="active")))
    plan = plan.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Plan no encontrado o inactivo")

    stripe_customer = stripe.Customer.create(email=user.email, name=f"{user.first_name} {user.last_name}")

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=stripe_customer.id,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        success_url=settings.FRONTEND_SUCCESS_URL,
        cancel_url=settings.FRONTEND_CANCEL_URL,
    )

    sub = PaymentSubscription(
        plan_id=plan.id,
        user_id=user.id,
        status_id=(await get_active_status(db)).id
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)

    return {"checkout_url": session.url, "subscription_id": session.subscription}
