
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.cores.db import async_session 

"""
Este archivo define la función `get_db`, que proporciona una sesión de base de datos asincrónica.
Se usa como dependencia en rutas de FastAPI para interactuar con la base de datos sin preocuparse
por abrir o cerrar la conexión manualmente.
"""
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session