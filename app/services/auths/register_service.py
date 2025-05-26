from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, Role, Status
from app.schemas.auths.register_shema import RegisterUserRequest
from app.services.validation.register_validater import validate_password,validate_privacy_policy_accepted,validate_first_name, validate_last_name
from app.services.validation.exception import email_already_registered_exception, role_not_found_exception, status_not_found_exception, unexpected_exception
from app.cores.security import get_password_hash
from fastapi import HTTPException



async def register_user(request: RegisterUserRequest, role_name: str, status_name: str, db: AsyncSession) -> User:
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
                role_id=role.id,
                status_id=status.id
            )

            db.add(new_user)
            await db.flush()  


            await db.refresh(new_user)

            return new_user

    except HTTPException as e:
        raise e
    except Exception:
        await unexpected_exception()

    '''except Exception as e:
        import traceback
        print("ERROR:", e)
        traceback.print_exc()
        raise e  '''