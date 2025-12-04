from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.users.user import User
from app.models.users.profile import Profile
from app.cores.security import get_password_hash


async def _ensure_alumno_user(db: AsyncSession) -> User:
    res = await db.execute(select(User).where(User.email == "alumno_prueba@example.com"))
    alumno = res.scalar_one_or_none()
    if not alumno:
        alumno = User(
            first_name="Luis",
            last_name="García",
            email="alumno_prueba@example.com",
            password=get_password_hash("12345678"),
            role_id=2,
            status_id=1,
        )
        db.add(alumno)
        await db.flush()
        print("Alumno de prueba creado.")
    else:
        print("El alumno de prueba ya existe.")
    return alumno


async def _ensure_alumno_profile(db: AsyncSession, alumno: User) -> None:
    prof_res = await db.execute(select(Profile).where(Profile.user_id == alumno.id))
    profile = prof_res.scalar_one_or_none()
    if not profile:
        db.add(Profile(user_id=alumno.id, credential="Estudiante", gender="Masculino", sex="M"))
        print("Perfil del alumno de prueba creado.")


async def crear_alumno(db: AsyncSession) -> User:
    """
    Crea o recupera al alumno de prueba (alumno_prueba@example.com) y su perfil.
    No realiza commit; solo flush en nuevas inserciones para permitir que el caller
    controle la transacción.
    """
    alumno = await _ensure_alumno_user(db)
    await _ensure_alumno_profile(db, alumno)
    return alumno
