from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.cores.db import async_session
from app.models.privileges.privilege import Privilege
from app.models.common.role import Role
from app.models.common.status import Status

async def create_privileges():
    db: AsyncSession = async_session()
    
    try:
        result = await db.execute(select(Privilege))
        privileges = result.scalars().all()

        if not privileges:
            status_result = await db.execute(
                select(Status).filter(Status.name == "active")
            )
            active_status = status_result.scalars().first()

            if not active_status:
                print("Status 'active' not found. Create statuses first.")
                return
                
            privileges_list = [
                Privilege(
                    name="privilege",
                    action="create",
                    description="Allows creating new Privileges",
                    status_id=active_status.id
                ),
                Privilege(
                    name="privilege",
                    action="edit",
                    description="Allows editing existing Privileges",
                    status_id=active_status.id
                ),
                Privilege(
                    name="privilege",
                    action="desactivate",
                    description="Allows deactivating Privileges",
                    status_id=active_status.id
                ),
                Privilege(
                    name="privilege",
                    action="read",
                    description="Allows reading existing Privileges",
                    status_id=active_status.id
                )
            ]

            db.add_all(privileges_list)
            await db.commit()
            print("Privileges created successfully.")
        else:
            print("Privileges already exist.")

    except Exception as e:
        await db.rollback()
        print(f"Error creating privileges: {e}")

    finally:
        await db.close()
   