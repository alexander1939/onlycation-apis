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
        existing_subscription_result = await db.execute(
            select(Subscription)
            .where(
                Subscription.user_id == user.id,
                Subscription.status.has(name="active"),
                Subscription.end_date > datetime.utcnow()
            )
        )
        existing_subscription = existing_subscription_result.scalar_one_or_none()
        if existing_subscription:
            raise HTTPException(
                status_code=400,
                detail="Ya tienes una suscripción activa. No puedes suscribirte a otro plan hasta que expire o canceles la actual."
            )

        plan_result = await db.execute(
            select(Plan).where(Plan.id == plan_id, Plan.status.has(name="active"))
        )
        plan = plan_result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan no encontrado o inactivo")

        if not plan.stripe_price_id:
            raise HTTPException(status_code=400, detail="Plan no tiene configuración de Stripe")

        if user.role_id != plan.role_id:
            raise HTTPException(
                status_code=403, 
                detail=f"No puedes suscribirte a este plan. Este plan está destinado para usuarios con rol '{plan.role.name}' y tu rol es '{user.role.name}'"
            )

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
        print(f"🔍 DEBUG: Iniciando verify_payment_and_create_subscription")
        print(f"   - session_id: {session_id}")
        print(f"   - user_id: {user_id}")
        
        # Verificar que el session_id tenga el formato correcto de Stripe
        if not session_id.startswith('cs_'):
            raise HTTPException(status_code=400, detail="Session ID inválido")

        # Obtener la sesión de Stripe
        print(f"📡 DEBUG: Obteniendo sesión de Stripe...")
        session = stripe.checkout.Session.retrieve(session_id)
        print(f"✅ DEBUG: Sesión obtenida exitosamente")
        
        # Verificar que la sesión pertenece al usuario autenticado
        if session.metadata.get("user_id") != str(user_id):
            raise HTTPException(status_code=403, detail="No tienes permisos para verificar esta sesión")
        
        # Para suscripciones, verificar el status de la sesión en lugar de payment_status
        print(f"🔍 DEBUG: Verificando estado del pago...")
        print(f"   - session.status: {session.status}")
        print(f"   - session.payment_status: {session.payment_status}")
        print(f"   - session.subscription: {session.subscription}")
        
        # Para suscripciones, el payment_status puede ser 'unpaid' pero el status debe ser 'complete'
        if session.status == "open":
            return {
                "success": False,
                "message": "El pago aún no se ha completado. Por favor completa el proceso de pago en Stripe.",
                "payment_status": session.status,
                "redirect_url": session.url  # URL para completar el pago
            }
        elif session.status != "complete":
            return {
                "success": False,
                "message": "Sesión de pago no completada",
                "payment_status": session.status
            }
        
        # DEBUG: Verificar el estado de la sesión
        print(f"🔍 DEBUG Session info:")
        print(f"   - payment_status: {session.payment_status}")
        print(f"   - status: {session.status}")
        print(f"   - subscription: {session.subscription}")
        print(f"   - metadata: {session.metadata}")

        # TEMPORALMENTE DESHABILITADO - Permitir reprocesar para debug
        # existing_payment = await db.execute(
        #     select(PaymentSubscription).where(
        #         PaymentSubscription.user_id == user_id,
        #         PaymentSubscription.created_at >= session.created
        #     )
        # )
        # existing_payment = existing_payment.scalar_one_or_none()
        
        # if existing_payment:
        #     print(f"⚠️ DEBUG: Pago ya procesado")
        #     return {"success": True, "message": "Pago ya procesado"}
        
        print(f"🚀 DEBUG: Continuando con procesamiento de pago...")
        
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        plan_id = int(session.metadata.get("plan_id"))
        plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = plan_result.scalar_one_or_none()
        
        if not user or not plan:
            raise HTTPException(status_code=404, detail="Usuario o plan no encontrado")
        
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
            "payment_status": "active"
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
        session_id = session["id"]  # Obtener el session_id del objeto session

        print(f"💾 DEBUG: Procesando pago para user_id: {user_id}, plan_id: {plan_id}")
        print(f"💾 DEBUG: session_id: {session_id}")

        # VERIFICAR SI YA EXISTE UNA SUSCRIPCIÓN CON ESTE SESSION_ID
        existing_payment_result = await db.execute(
            select(PaymentSubscription).where(
                PaymentSubscription.stripe_payment_intent_id == session_id
            )
        )
        existing_payment = existing_payment_result.scalars().first()
        
        if existing_payment:
            print(f"⚠️ DEBUG: Ya existe un PaymentSubscription con session_id: {session_id}")
            return {
                "success": True,
                "message": "Pago ya procesado anteriormente",
                "payment_status": "active"
            }

        # VERIFICAR SI YA TIENE UNA SUSCRIPCIÓN ACTIVA AL MISMO PLAN
        from datetime import datetime
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
        existing_subscription = existing_subscription_result.scalars().first()
        
        if existing_subscription:
            print(f"⚠️ DEBUG: Usuario {user_id} ya tiene suscripción activa al plan {plan_id}")
            return {
                "success": True,
                "message": f"Ya tienes una suscripción activa a este plan que expira el {existing_subscription.end_date.strftime('%Y-%m-%d')}",
                "payment_status": "active"
            }

        stripe_subscription_id = session.get("subscription")
        payment_intent_id = None
        if stripe_subscription_id:
            stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            latest_invoice_id = stripe_subscription.get("latest_invoice")
            if latest_invoice_id:
                invoice = stripe.Invoice.retrieve(latest_invoice_id)
                payment_intent_id = invoice.get("payment_intent")
                
        print(f"💳 DEBUG: stripe_subscription_id: {stripe_subscription_id}")
        print(f"💳 DEBUG: payment_intent_id: {payment_intent_id}")

        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = plan_result.scalar_one_or_none()
        
        if not user or not plan:
            raise HTTPException(status_code=404, detail="Usuario o plan no encontrado")
        
        active_status = await get_active_status(db)
        if not active_status:
            raise HTTPException(status_code=500, detail="Status activo no encontrado")

        print(f"📊 DEBUG: active_status encontrado: {active_status.id} - {active_status.name}")

        payment_subscription = PaymentSubscription(
            plan_id=plan_id,
            user_id=user_id,
            status_id=active_status.id,
            payment_date=datetime.utcnow(), 
            stripe_payment_intent_id=session_id  # Guardar el session_id aquí
        )

        print(f"💾 DEBUG: Creando PaymentSubscription...")
        db.add(payment_subscription)
        await db.commit()
        await db.refresh(payment_subscription)
        print(f"✅ DEBUG: PaymentSubscription creado con ID: {payment_subscription.id}")

        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            payment_suscription_id=payment_subscription.id,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30), 
            status_id=active_status.id
        )
        
        print(f"💾 DEBUG: Creando Subscription...")
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
        print(f"✅ DEBUG: Subscription creado con ID: {subscription.id}")

        try:
            await create_welcome_notification(db, user)
            
            await create_subscription_notification(db, user, plan.name)
            
            print(f"✅ Notificaciones creadas para usuario {user_id}")
        except Exception as e:
            print(f"⚠️ Error creando notificaciones: {str(e)}")

        print(f"Suscripción creada para usuario {user_id}, plan {plan_id}")
    except Exception as e:
        import traceback
        print("ERROR:", e)
        traceback.print_exc()
        raise e
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

        # Verificar suscripción activa del usuario
        try:
            current_subscription_result = await db.execute(
                select(Subscription)
                .options(joinedload(Subscription.plan))
                .join(Status)
                .where(
                    Subscription.user_id == user.id,
                    Status.name == "active"
                )
                .order_by(Subscription.start_date.desc())
            )
            current_subscription = current_subscription_result.scalars().first()
            
            if current_subscription:
                # Verificar si la suscripción actual ha expirado
                from datetime import datetime
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





async def get_user_active_subscription(db, user_id: int):
    result = await db.execute(
        select(Subscription)
        .options(joinedload(Subscription.plan), joinedload(Subscription.status))
        .join(Status)
        .where(
            Subscription.user_id == user_id,
            Status.name == "active"
        )
        .order_by(Subscription.start_date.desc())
    )
    
    subscription = result.scalars().first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No tienes suscripción activa")

    days_left = None
    if subscription.end_date:
        days_left = (subscription.end_date - datetime.utcnow()).days

    return {
        "subscription_id": subscription.id,
        "plan_id": subscription.plan.id,
        "plan_name": subscription.plan.name,
        "plan_description": subscription.plan.description,
        "price": subscription.plan.price,
        "start_date": subscription.start_date,
        "end_date": subscription.end_date,
        "status": subscription.status.name,
        "days_left": days_left
    }