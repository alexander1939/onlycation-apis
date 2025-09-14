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
from app.models.common.stripe_price import StripePrice

from app.models.users.user import User
from app.models.users.preference import Preference


from app.models.teachers.document import Document
from app.models.teachers.price import Price
from app.models.teachers.video import Video
from app.models.teachers.availability import Availability
from app.models.teachers.wallet import Wallet


from app.models.privileges.privilege import Privilege
from app.models.privileges.privilege_role import PrivilegeRole
from app.models.privileges.privilege_user import PrivilegeUser

from app.models.subscriptions.benefit import Benefit
from app.models.subscriptions.plan import Plan
from app.models.subscriptions.subscription import Subscription
from app.models.subscriptions.payment_subscription import PaymentSubscription

from  app.models.notifications.notifications import Notification
from  app.models.notifications.user_notifications import User_notification

from app.models.booking.bookings import Booking
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.confirmation import Confirmation
from app.models.booking.reschedule_request import RescheduleRequest

from app.models.refunds.refund_request import RefundRequest

from app.scripts.databases.create_status import create_status
from app.scripts.databases.create_user_admin import create_admin_user
from app.scripts.databases.create_role import create_role
from app.scripts.databases.create_educational_level import create_educational_level
from app.scripts.databases.create_modality import create_modality
from app.scripts.databases.create_privilege import create_privileges
from app.scripts.databases.create_privilege_role import create_privileges_role
from app.scripts.databases.create_price_ranges import create_prices_range
from app.scripts.databases.create_plan import create_premium_plan, create_free_plan
from app.scripts.databases.create_benefit import create_benefit
from app.scripts.databases.create_price_ranges import create_prices_range
from app.scripts.databases.create_docente import crear_docente

from app.schemas.auths.register_shema import RegisterUserRequest
from app.services.auths.register_service import RegisterUserRequest
from app.apis.auth_api import register_student_route
from app.apis.auth_api import register_teacher_route

from app.apis.auth_api import router as auth_router
from app.apis.privileges_api import router as privileges_router
from app.apis.profile_api import router as profile_router
from app.apis.price_api import router as price_router
from app.apis.suscripcion_api import router as suscripcion_router
from app.apis.notifications_api import router as notifications_router
from app.apis.document_api import router as document_router
from app.apis.booking_api import router as booking_router
from app.apis.wallet_api import router as wallet_router
from app.apis.refund_api import router as refund_router
from app.apis.availability_api import router as availability_router


from fastapi.middleware.cors import CORSMiddleware

from app.apis.videos_api import router as videos_router
from app.apis.chat_api import router as chat_router


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
    await create_admin_user()
    await create_prices_range()
    await create_premium_plan()
    await create_free_plan()
    await create_benefit()
    await create_prices_range()
    await crear_docente()

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

    origins = [
        "http://localhost:8080",
        "http://localhost:8080/",  
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    # Agrega el router de autenticación con un prefijo y una etiqueta
    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(privileges_router, prefix="/api/privileges", tags=["Privileges"])
    app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])
    app.include_router(price_router, prefix="/api/prices", tags=["Prices"])
    app.include_router(suscripcion_router, prefix="/api/suscripcion", tags=["suscripcion"])
    app.include_router(notifications_router, prefix="/api/notifications", tags=["Notifications"])
    app.include_router(document_router, prefix="/api/documents", tags=["Documents"])
    app.include_router(booking_router, prefix="/api/bookings", tags=["Bookings"])
    app.include_router(wallet_router, prefix="/api/wallet", tags=["Wallet"])
    app.include_router(refund_router, prefix="/api/refunds", tags=["Refunds"])
    app.include_router(availability_router, prefix="/api/availability", tags=["Availability"])
    app.include_router(videos_router, prefix="/api/videos", tags=["Videos"])
    app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])

    return app