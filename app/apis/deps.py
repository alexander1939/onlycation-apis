from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.cores.db import async_session 


''' Abre y cierra automáticamente la sesión de BD para cada petición HTTP para evitar conexiones colgadas o memory leaks'''
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session