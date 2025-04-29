from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.cores.db import async_session
from app.models.common.status import Status
from app.models.common.educational_level import EducationalLevel

async def create_educational_level():
    db: AsyncSession = async_session()
    
    try:
        result = await db.execute(select(EducationalLevel))
        levels = result.scalars().all()
        
        if not levels:
            status_result = await db.execute(
                select(Status).where(Status.name == "active")
            )
            active_statuses = status_result.scalars().first()
            
            if not active_statuses:
                print("Error: 'active' status not found. Please create statuses first.")
                return

            levels_list = [
                EducationalLevel(
                    name="Preparatoria",
                    statuses_id=active_statuses.id
                ),
                EducationalLevel(
                    name="Universidad",
                    statuses_id=active_statuses.id
                ),
                EducationalLevel(
                    name="Posgrado",
                    statuses_id=active_statuses.id
                )
            ]
            
            db.add_all(levels_list)
            await db.commit()
            print("Successfully created educational levels: Preparatoria, Universidad, Posgrado")
        else:
            print("Educational levels already exist in database.")
            
    except Exception as e:
        await db.rollback()
        print(f"Error creating educational levels: {str(e)}")
        
    finally:
        await db.close()