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
from app.models.common.verification_code import VerificationCode
from app.models.common.price_range import PriceRange

from app.models.users.user import User
from app.models.users.preference import Preference


from app.models.teachers.document import Document
from app.models.teachers.price import Price
from app.models.teachers.video import Video


from app.models.privileges.privilege import Privilege
from app.models.privileges.privilege_role import PrivilegeRole
from app.models.privileges.privilege_user import PrivilegeUser

from app.models.subscriptions.benefit import Benefit
from app.models.subscriptions.plan import Plan
from app.models.subscriptions.subscription import Subscription
from app.models.subscriptions.payment_subscription import PaymentSubscription

from app.scripts.databases.create_status import create_status
from app.scripts.databases.create_role import create_role
from app.scripts.databases.create_educational_level import create_educational_level
from app.scripts.databases.create_modality import create_modality
from app.scripts.databases.create_privilege import create_privileges
from app.scripts.databases.create_privilege_role import create_privileges_role

from app.schemas.auths.register_shema import RegisterUserRequest
from app.services.auths.register_service import RegisterUserRequest
from app.apis.auth_api import register_student_route
from app.apis.auth_api import register_teacher_route

from app.apis.auth_api import router as auth_router
from app.apis.privileges_api import router as privileges_router



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
    await create_privileges()
    await create_privileges_role()

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
    app.include_router(privileges_router, prefix="/api/privileges", tags=["Privileges"])
    ##app.include_router()

    return app