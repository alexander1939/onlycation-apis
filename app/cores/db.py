"""
Configuración de SQLAlchemy para trabajar con base de datos de forma asincrónica.
Soporta SQLite (desarrollo) y MySQL (producción) según variable de entorno.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.configs.settings import settings

# Obtener la URL de la base de datos desde settings (.env)
DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI

# Configurar argumentos según el tipo de base de datos
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    # SQLite requiere check_same_thread=False para async
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

Base = declarative_base()
