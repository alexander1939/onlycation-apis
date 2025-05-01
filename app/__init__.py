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


''' Manejador del ciclo de vida de la aplicación FastAPI 
    Lo que ase es separa la parte de la configuracion de la base de datos
'''
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await create_status()
    await create_modality()
    await create_role()
    await create_educational_level()

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="onlyCation", 
        lifespan=lifespan  
    )

    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

    return app