from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, Role
from app.schemas.auths.register_shemas import RegisterUserRequest
from app.services.validation.validate_password import validate_password
from app.services.validation.exception import email_already_registered_exception, role_not_found_exception

async def register_user(request: RegisterUserRequest, role_name: str, db: AsyncSession) -> str:
    result = await db.execute(select(User).filter(User.email == request.email))
    existing_user = result.scalars().first()
    if existing_user:
        await email_already_registered_exception()

    result = await db.execute(select(Role).filter(Role.name == role_name))
    role = result.scalars().first()
    if not role:
        await role_not_found_exception(role_name)

    await validate_password(request.password)

    new_user = User(
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        password=request.password, 
        roles_id=role.id
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return f"User {new_user.first_name} {new_user.last_name} registered successfully as {role_name}."
