from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.cores.db import async_session
from app.models.common.role import Role
from app.models.common.status import Status

async def create_role():
    db: AsyncSession = async_session()
    
    try:
        result = await db.execute(select(Role))
        roles = result.scalars().all()
        
        if not roles:
            status_result = await db.execute(
                select(Status).filter(Status.name == "active")
            )
            active_status = status_result.scalars().first()
            
            if not active_status:
                print("Status 'active' not found. Create statuses first.")
                return
                
            roles_list = [
                Role(
                    name="teacher",
                    description="Professional responsible for tutoring...",
                    status_id=active_status.id
                ),
                Role(
                    name="student",
                    description="Primary beneficiary of the system...",
                    status_id=active_status.id
                ),
                Role(
                    name="admin",
                    description="Manages system operations...",
                    status_id=active_status.id
                )
            ]
            
            db.add_all(roles_list)
            await db.commit()
            print("Roles created successfully.")
        else:
            print("Roles already exist.")
            
    except Exception as e:
        await db.rollback()
        print(f"Error creating roles: {e}")
        
    finally:
        await db.close()