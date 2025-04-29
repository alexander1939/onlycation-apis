from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Role,Status,students,Teacher,EducationalLevel,Preference,Modality,TeacherDocument,TeacherPrice,TeacherVideo,PriceRange
from app.cores.db import Base

# Base de datos de prueba (en memoria)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(bind=engine_test, class_=AsyncSession, expire_on_commit=False)

# Crea todas las tablas en memoria
async def init_test_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Devuelve una sesión de prueba (para override)
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session
