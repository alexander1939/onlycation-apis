"""
Configuración de SQLAlchemy para trabajar con una base de datos SQLite de forma asincrónica.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base


""" 
Crear el motor de la base de datos asincrónico.
    - Usa SQLite como base de datos local.
    - Se desactiva 'check_same_thread' porque SQLite no es thread-safe por defecto.
    - 'echo=False' evita mostrar las consultas SQL en consola.
"""
engine = create_async_engine(
    "sqlite+aiosqlite:///task.db",
    connect_args={"check_same_thread": False},  
    echo=False
)



""" 
Crear un generador de sesiones asincrónicas para interactuar con la base de datos.
    - Usa AsyncSession como clase base para la sesión.
    - autocommit=False: se debe confirmar manualmente cada transacción.
    - autoflush=False: evita que los cambios se envíen automáticamente antes de consultar.
    - expire_on_commit=False: los objetos no se invalidan después del commit.
"""
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

Base = declarative_base()