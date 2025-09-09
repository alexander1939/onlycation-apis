from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, Role, Status
from app.models.subscriptions.plan import Plan
from app.models.subscriptions.payment_subscription import PaymentSubscription
from app.models.subscriptions.subscription import Subscription
from app.schemas.auths.register_shema import RegisterUserRequest
from app.services.validation.register_validater import validate_password,validate_privacy_policy_accepted,validate_first_name, validate_last_name
from app.services.validation.exception import email_already_registered_exception, role_not_found_exception, status_not_found_exception, unexpected_exception
from app.cores.security import get_password_hash
from fastapi import HTTPException
from datetime import datetime



async def register_user(request: RegisterUserRequest, role_name: str, status_name: str, db: AsyncSession) -> User:# type: ignore
    try:
        async with db.begin():  

            result = await db.execute(select(User).filter(User.email == request.email))
            if result.scalars().first():
                await email_already_registered_exception()

            result = await db.execute(select(Role).filter(Role.name == role_name))
            role = result.scalars().first()
            if not role:
                await role_not_found_exception(role_name)

            result = await db.execute(select(Status).filter(Status.name == status_name))
            status = result.scalars().first()
            if not status:
                await status_not_found_exception(status_name)

            await validate_password(request.password)
            await validate_first_name(request.first_name)
            await validate_last_name(request.last_name)
            await validate_privacy_policy_accepted(request.privacy_policy_accepted)

            new_user = User(
                first_name=request.first_name,
                last_name=request.last_name,
                email=request.email,
                password=get_password_hash(request.password),
                role_id=role.id,# type: ignore
                status_id=status.id# type: ignore
            )

            db.add(new_user)
            await db.flush()  

            # Si es un docente, asignar plan gratuito por defecto
            if role_name == "teacher":
                # Buscar el plan gratuito
                free_plan_result = await db.execute(
                    select(Plan).where(
                        Plan.name == "Plan Gratuito",
                        Plan.role_id == role.id
                    )
                )
                free_plan = free_plan_result.scalar_one_or_none()
                
                if free_plan:
                    # Obtener status activo para la suscripción (diferente del usuario)
                    active_status_result = await db.execute(
                        select(Status).where(Status.name == "active")
                    )
                    active_status = active_status_result.scalar_one_or_none()
                    
                    if active_status:
                        # Crear PaymentSubscription con status activo
                        payment_subscription = PaymentSubscription(
                            user_id=new_user.id,
                            plan_id=free_plan.id,
                            status_id=active_status.id,  # Suscripción siempre activa
                            stripe_payment_intent_id=None  # No hay Stripe para plan gratuito
                        )
                        db.add(payment_subscription)
                        await db.flush()
                        
                        # Crear Subscription con status activo
                        subscription = Subscription(
                            user_id=new_user.id,
                            plan_id=free_plan.id,
                            payment_suscription_id=payment_subscription.id,
                            start_date=datetime.utcnow(),
                            end_date=None,  # Plan gratuito ilimitado
                            status_id=active_status.id  # Suscripción siempre activa
                        )
                        db.add(subscription)
                        await db.flush()
                        print(f"Plan gratuito asignado al docente {new_user.email}")

            await db.refresh(new_user)

            return new_user

    # except HTTPException as e:
    #     raise e
    # except Exception:
    #     await unexpected_exception()

    except Exception as e:
        import traceback
        print("ERROR:", e)
        traceback.print_exc()
        raise e  