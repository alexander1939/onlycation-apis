from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, Role, Status, Student, Teacher
from app.schemas.auths.register_shemas import RegisterUserRequest
from app.services.validation.validate_password import validate_password
from app.services.validation.exception import email_already_registered_exception, role_not_found_exception, status_not_found_exception
from app.cores.security import get_password_hash



async def create_student(user: User, status: Status, db: AsyncSession):
    """Crea un registro en la tabla Student"""
    new_student = Student(
        users_id=user.id,
        statuses_id=status.id
    )
    db.add(new_student)
    await db.commit()

async def create_teacher(user: User, status: Status, db: AsyncSession):
    """Crea un registro en la tabla Teacher"""
    new_teacher = Teacher(
        users_id=user.id,
        statuses_id=status.id
    )
    db.add(new_teacher)
    await db.commit()

async def register_user(request: RegisterUserRequest, role_name: str, status_name: str, db: AsyncSession) -> str:
    result = await db.execute(select(User).filter(User.email == request.email))
    if result.scalars().first():
        await email_already_registered_exception()

    result = await db.execute(select(Role).filter(Role.name == role_name))
    role = result.scalars().first()
    if not role:
        await role_not_found_exception(role_name)

    result = await db.execute(select(Status).filter(Status.name == status_name))
    status_obj = result.scalars().first()
    if not status_obj:
        await status_not_found_exception(status_name)

    await validate_password(request.password)

    new_user = User(
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        password=get_password_hash(request.password),
        roles_id=role.id
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    if role_name == "student":
        await create_student(new_user, status_obj, db)
    elif role_name == "teacher":
        await create_teacher(new_user, status_obj, db)
    else:
        raise ValueError(f"Rol no soportado: {role_name}")

    return {
        "success": f"User {new_user.first_name} {new_user.last_name} registered successfully.",
    }