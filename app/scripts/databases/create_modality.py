from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.cores.db import async_session
from app.models.common.status import Status
from app.models.common.modality import Modality

async def create_modality():
    db: AsyncSession = async_session()
    
    try:
        result = await db.execute(select(Modality))
        modalities = result.scalars().all()
        
        if not modalities:
            status_result = await db.execute(
                select(Status).where(Status.name == "active")
            )
            active_status = status_result.scalars().first()
            
            if not active_status:
                print("Error: 'active' status not found. Create statuses first.")
                return

            # Crear modalidades
            modalities_list = [
                Modality(
                    name="In-person",
                    status_id=active_status.id
                ),
                Modality(
                    name="online",
                    status_id=active_status.id
                )
            ]
            
            db.add_all(modalities_list)
            await db.commit()
            print("Successfully created modalities: In-person, online")
        else:
            print("Modalities already exist.")
            
    except Exception as e:
        await db.rollback()
        print(f"Error creating modalities: {str(e)}")
        
    finally:
        await db.close()