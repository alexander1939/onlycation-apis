"""
Este bloque define la configuración de inicio (lifespan) y creación de la aplicación FastAPI.
Incluye tareas que deben ejecutarse al arrancar la aplicación, como la creación de tablas y datos iniciales.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.cores.db import Base, engine
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.common.status import Status
from app.models.common.role import Role
from app.models.common.modality import Modality
from app.models.common.educational_level import EducationalLevel

from app.models.users.user import User
from app.models.users.preference import Preference


from app.models.teachers.teacher import Teacher
from app.models.teachers.teacher_document import TeacherDocument
from app.models.teachers.teacher_price import TeacherPrice
from app.models.teachers.teacher_video import TeacherVideo


from app.models.students.student import Student

from app.scripts.databases.create_status import create_status
from app.scripts.databases.create_role import create_role
from app.scripts.databases.create_educational_level import create_educational_level
from app.scripts.databases.create_modality import create_modality

from app.schemas.auths.register_shema import RegisterUserRequest
from app.services.auths.register_service import RegisterUserRequest
from app.apis.auth_api import register_student_route
from app.apis.auth_api import register_teacher_route

from app.apis.auth_api import router as auth_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Función que se ejecuta al iniciar la aplicación.
    - Crea todas las tablas en la base de datos si no existen.
    - Inserta datos iniciales requeridos como estados, roles, modalidades, niveles educativos.
    - Al finalizar, continúa con la ejecución normal de la app (con `yield`).
    """
    async with engine.begin() as conn:
        # Crea las tablas en la base de datos
        await conn.run_sync(Base.metadata.create_all)
    #Crean o ejecutan los script para los datos(roles,status, etc..)
    await create_status()
    await create_modality()
    await create_role()
    await create_educational_level()

    yield

"""
    Función que construye y retorna la instancia principal de la aplicación FastAPI.
    - Establece el título de la app.
    - Aplica la función `lifespan` para la inicialización.
    - Carga las rutas necesarias (por ahora, solo las de autenticación).
"""
def create_app() -> FastAPI:
    app = FastAPI(
        title="onlyCation", 
        lifespan=lifespan  
    )
    # Agrega el router de autenticación con un prefijo y una etiqueta
    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    ##app.include_router()

    return app