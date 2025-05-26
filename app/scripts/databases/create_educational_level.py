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
            active_status = status_result.scalars().first()
            
            if not active_status:
                print("Error: 'active' status not found. Please create statuses first.")
                return

            levels_list = [
                EducationalLevel(
                    name="Preparatoria",
                    status_id=active_status.id
                ),
                EducationalLevel(
                    name="Universidad",
                    status_id=active_status.id
                ),
                EducationalLevel(
                    name="Posgrado",
                    status_id=active_status.id
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