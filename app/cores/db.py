"""
Configuración de SQLAlchemy para base de datos asíncrona.
Soporta SQLite (test/desarrollo) y MySQL/Postgres (producción).
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.configs.settings import settings

DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI

# --- Fix crítico para SQLite ---
# Si viene sqlite:///  lo transformamos a sqlite+aiosqlite:///
if DATABASE_URL.startswith("sqlite:///"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

elif DATABASE_URL.startswith("sqlite://"):
    DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")

# ---------------------------------------------------------------

engine = create_async_engine(
    DATABASE_URL,
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
