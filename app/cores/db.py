"""
Configuración de SQLAlchemy para trabajar con una base de datos MySQL de forma asincrónica.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

engine = create_async_engine(
    "mysql+aiomysql://onlycation:OnlyCation2025@database-onlycationdb-1rcvau:3306/onlycation_db",
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
