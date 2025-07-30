from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from app.configs import settings
from app.models.subscriptions import Benefit, Plan
from app.models.subscriptions.payment_subscription import PaymentSubscription
from app.models.subscriptions.subscription import Subscription
from app.models.users import User
from app.models.common import Status
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.validation.exception import unexpected_exception
from app.schemas.suscripcion.benefit_schema import CreateBenefitRequest, UpdateBenefitRequest
from datetime import datetime, timedelta
from app.external.stripe_config import stripe
from app.services.notifications import create_welcome_notification, create_subscription_notification

async def get_active_status(db: AsyncSession):
    """Obtiene el status activo"""
    result = await db.execute(select(Status).where(Status.name == "active"))
    return result.scalar_one_or_none()

async def create_subscription_session(db: AsyncSession, user: User, plan_id: int):
    """
    Crea una sesión de checkout de Stripe para suscripción
    """
    try:
        # Buscar el plan por ID
        plan_result = await db.execute(
            select(Plan).where(Plan.id == plan_id, Plan.status.has(name="active"))
        )
        plan = plan_result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan no encontrado o inactivo")

        # Verificar que el plan tiene stripe_price_id configurado
        if not plan.stripe_price_id:
            raise HTTPException(status_code=400, detail="Plan no tiene configuración de Stripe")

        # Validar que el usuario tiene el rol correcto para este plan
        if user.role_id != plan.role_id:
            raise HTTPException(
                status_code=403, 
                detail=f"No puedes suscribirte a este plan. Este plan está destinado para usuarios con rol '{plan.role.name}' y tu rol es '{user.role.name}'"
            )

        # Crear sesión de checkout de Stripe
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=user.email,
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            success_url="http://localhost:5173/?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://localhost:5173/",
            metadata={
                "user_id": str(user.id),
                "plan_id": str(plan.id)
            }
        )

        return {
            "url": session.url,
            "session_id": session.id,
            "plan_name": plan.name,
            "plan_price": plan.price
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        await unexpected_exception()

async def verify_payment_and_create_subscription(db: AsyncSession, session_id: str, user_id: int):
    """
    Verifica el pago con Stripe y crea la suscripción en la base de datos
    """
    try:
        # Verificar que el session_id tenga el formato correcto de Stripe
        if not session_id.startswith('cs_'):
            raise HTTPException(status_code=400, detail="Session ID inválido")

        # Obtener la sesión de Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Verificar que la sesión pertenece al usuario autenticado
        if session.metadata.get("user_id") != str(user_id):
            raise HTTPException(status_code=403, detail="No tienes permisos para verificar esta sesión")
        
        # Verificar que el pago fue exitoso
        if session.payment_status != "paid":
            return {
                "success": False,
                "message": "Pago no completado",
                "payment_status": session.payment_status
            }

        # Verificar si ya se procesó esta sesión
        existing_payment = await db.execute(
            select(PaymentSubscription).where(
                PaymentSubscription.user_id == user_id,
                PaymentSubscription.created_at >= session.created
            )
        )
        existing_payment = existing_payment.scalar_one_or_none()
        
        if existing_payment:
            return {
                "success": True,
                "message": "Pago ya fue procesado anteriormente",
                "payment_status": session.payment_status
            }
        
        # Obtener el usuario y el plan para validar roles
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        plan_id = int(session.metadata.get("plan_id"))
        plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = plan_result.scalar_one_or_none()
        
        if not user or not plan:
            raise HTTPException(status_code=404, detail="Usuario o plan no encontrado")
        
        # Validar que el usuario tiene el rol correcto para este plan
        if user.role_id != plan.role_id:
            raise HTTPException(
                status_code=403, 
                detail=f"No puedes suscribirte a este plan. Este plan está destinado para usuarios con rol '{plan.role.name}' y tu rol es '{user.role.name}'"
            )
        
        # El pago fue exitoso, guardar en la base de datos
        await process_successful_payment(db, session)
        
        return {
            "success": True,
            "message": "Pago verificado y suscripción creada",
            "payment_status": session.payment_status
        }

    except stripe.error.InvalidRequestError:
        raise HTTPException(status_code=400, detail="Session ID no encontrado en Stripe")
    except HTTPException as e:
        raise e
    except Exception as e:
        await unexpected_exception()

async def process_successful_payment(db: AsyncSession, session):
    """Procesa un pago exitoso y guarda en la base de datos"""
    try:
        user_id = int(session["metadata"]["user_id"])
        plan_id = int(session["metadata"]["plan_id"])
        
        # Obtener el usuario y el plan para las notificaciones
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = plan_result.scalar_one_or_none()
        
        if not user or not plan:
            raise HTTPException(status_code=404, detail="Usuario o plan no encontrado")
        
        # Obtener status activo
        active_status = await get_active_status(db)
        if not active_status:
            raise HTTPException(status_code=500, detail="Status activo no encontrado")

        # Crear payment_subscription en la base de datos
        payment_subscription = PaymentSubscription(
            plan_id=plan_id,
            user_id=user_id,
            status_id=active_status.id,
            Payment_date=datetime.utcnow()
        )
        
        db.add(payment_subscription)
        await db.commit()
        await db.refresh(payment_subscription)

        # Crear subscription en la base de datos
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            payment_suscription_id=payment_subscription.id,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),  # Fecha tentativa
            status_id=active_status.id
        )
        
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)

        # Crear notificaciones automáticas
        try:
            # Notificación de bienvenida
            await create_welcome_notification(db, user)
            
            # Notificación específica de suscripción
            await create_subscription_notification(db, user, plan.name)
            
            print(f"✅ Notificaciones creadas para usuario {user_id}")
        except Exception as e:
            print(f"⚠️ Error creando notificaciones: {str(e)}")
            # No fallamos la suscripción si las notificaciones fallan

        print(f"Suscripción creada para usuario {user_id}, plan {plan_id}")

    except HTTPException as e:
        raise e
    except Exception as e:
        await unexpected_exception()

async def subscribe_user_to_plan(db: AsyncSession, user: User, plan_guy: str):
    """
    Función mejorada para suscribir usuario a un plan
    """
    try:
        # Buscar el plan
        plan_result = await db.execute(
            select(Plan).where(Plan.guy == plan_guy, Plan.status.has(name="active"))
        )
        plan = plan_result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan no encontrado o inactivo")

        # Verificar que el plan tiene stripe_price_id configurado
        if not plan.stripe_price_id:
            raise HTTPException(status_code=400, detail="Plan no tiene configuración de Stripe")

        # Obtener status activo
        active_status = await get_active_status(db)
        if not active_status:
            raise HTTPException(status_code=500, detail="Status activo no encontrado")

        # Crear customer en Stripe
        stripe_customer = stripe.Customer.create(
            email=user.email, 
            name=f"{user.first_name} {user.last_name}",
            metadata={"user_id": str(user.id)}
        )

        # Crear sesión de checkout
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer=stripe_customer.id,
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_SUCCESS_URL}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=settings.FRONTEND_CANCEL_URL,
            metadata={
                "user_id": str(user.id),
                "plan_id": str(plan.id),
                "plan_guy": plan_guy
            }
        )

        # Crear payment_subscription en la base de datos
        payment_subscription = PaymentSubscription(
            plan_id=plan.id,
            user_id=user.id,
            status_id=active_status.id,
            Payment_date=datetime.utcnow()
        )
        
        db.add(payment_subscription)
        await db.commit()
        await db.refresh(payment_subscription)

        # Crear subscription en la base de datos
        subscription = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            payment_suscription_id=payment_subscription.id,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),  # Fecha tentativa
            status_id=active_status.id
        )
        
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)

        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "payment_subscription_id": payment_subscription.id,
            "subscription_id": subscription.id,
            "plan_name": plan.name,
            "plan_price": plan.price
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        await unexpected_exception()

async def get_user_subscription(db: AsyncSession, user_id: int):
    """
    Obtiene la suscripción activa de un usuario
    """
    try:
        subscription_result = await db.execute(
            select(Subscription)
            .join(Plan)
            .where(
                Subscription.user_id == user_id,
                Subscription.status.has(name="active"),
                Subscription.end_date > datetime.utcnow()
            )
        )
        return subscription_result.scalar_one_or_none()

    except Exception as e:
        await unexpected_exception()

async def cancel_user_subscription(db: AsyncSession, user_id: int):
    """
    Cancela la suscripción de un usuario
    """
    try:
        # Buscar suscripción activa
        subscription_result = await db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status.has(name="active")
            )
        )
        subscription = subscription_result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="No tienes suscripción activa")

        # Obtener status cancelado
        canceled_status_result = await db.execute(select(Status).where(Status.name == "canceled"))
        canceled_status = canceled_status_result.scalar_one_or_none()
        
        if not canceled_status:
            raise HTTPException(status_code=500, detail="Status cancelado no encontrado")

        # Actualizar suscripción
        subscription.status_id = canceled_status.id
        await db.commit()
        await db.refresh(subscription)

        return subscription

    except HTTPException as e:
        raise e
    except Exception as e:
        await unexpected_exception()



async def get_user_by_token(db: AsyncSession, user_id: int):
    """
    Obtiene el usuario por ID
    """
    try:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
        return user
    except HTTPException as e:
        raise e
    except Exception as e:
        await unexpected_exception()
