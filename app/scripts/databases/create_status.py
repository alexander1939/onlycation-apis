from app.cores.db import async_session
from app.models.common.status import Status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


async def create_status():
    db: AsyncSession = async_session()
    try:
        result = await db.execute(select(Status))
        statuses = result.scalars().all()
        
        if not statuses:
            status_list = [
                Status(name="active"),
                Status(name="inactive"),
                Status(name="cancelled"),
                Status(name="paid"),
                Status(name="pending")
            ]
            db.add_all(status_list)
            await db.commit()
            print("Estados creados correctamente")
        else:
            print("Los estados ya existen")
    except Exception as e:
        await db.rollback()
        print(f"Error al crear estados: {e}")
    finally:
        await db.close()