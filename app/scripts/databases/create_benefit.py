from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.cores.db import async_session
from app.models.subscriptions.benefit import Benefit
from app.models.common.role import Role
from app.models.common.status import Status

async def create_benefit():
    db: AsyncSession = async_session()
    
    try:
        result = await db.execute(select(Benefit))
        benefits = result.scalars().all()

        if not benefits:
            status_result = await db.execute(
                select(Status).filter(Status.name == "active")
            )
            active_status = status_result.scalars().first()

            if not active_status:
                print("Status 'active' not found. Create statuses first.")
                return
                
            benefits_list = [
                Benefit(
                    name="cero comisiones",
                    description="cero comisiones por transacciones",
                    status_id=active_status.id
                ),
                Benefit(
                    name="puntos extra",
                    description="Allows editing existing Benefits",
                    status_id=active_status.id
                )
            ]

            db.add_all(benefits_list)
            await db.commit()
            print("Benefits created successfully.")
        else:
            print("Benefits already exist.")

    except Exception as e:
        await db.rollback()
        print(f"Error creating benefits: {e}")

    finally:
        await db.close()
   
   