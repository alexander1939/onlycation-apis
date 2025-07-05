from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.cores.db import async_session
from app.models.privileges.privilege import Privilege
from app.models.common.role import Role
from app.models.common.status import Status
from app.models.privileges.privilege_role import PrivilegeRole

async def create_privileges_role():
    db: AsyncSession = async_session()

    try:
        result = await db.execute(select(Privilege))
        privileges = result.scalars().all()

        status_result = await db.execute(
            select(Status).filter(Status.name == "active")
        )
        active_status = status_result.scalars().first()

        if not active_status:
            print("Status 'active' not found. Create statuses first.")
            return

        role_result = await db.execute(
            select(Role).filter(Role.name == "admin")
        )
        role = role_result.scalars().first()

        if not role:
            print("Role 'admin' not found. Create roles first.")
            return

        if not privileges:
            actions = ["create", "edit", "desactivate", "read"]
            privileges_list = []

            for action in actions:
                privilege = Privilege(
                    name="privilege",
                    action=action,
                    description=f"Allows {action} privileges",
                    status_id=active_status.id
                )
                privileges_list.append(privilege)

            db.add_all(privileges_list)
            await db.commit()

            result = await db.execute(select(Privilege))
            privileges = result.scalars().all()

        for privilege in privileges:
            exists_result = await db.execute(
                select(PrivilegeRole).where(
                    PrivilegeRole.privilege_id == privilege.id,
                    PrivilegeRole.role_id == role.id
                )
            )
            existing = exists_result.scalar_one_or_none()

            if not existing:
                db.add(PrivilegeRole(
                    privilege_id=privilege.id,
                    role_id=role.id,
                    status_id=active_status.id
                ))

        await db.commit()
        print("Privileges and privilege-role relations created successfully.")

    except Exception as e:
        await db.rollback()
        print(f"Error creating privileges: {e}")

    finally:
        await db.close()
