import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.cores.db import async_session
from app.models.users import User
from app.models.common.role import Role
from app.models.common.status import Status
from app.cores.security import get_password_hash  
from dotenv import load_dotenv
import os

load_dotenv()

async def create_admin_user():
    async with async_session() as db:
        admin_email = os.getenv("ADMIN_EMAIL")
        password = os.getenv("ADMIN_PASSWORD")
        first_name = os.getenv("ADMIN_FIRST_NAME")
        last_name = os.getenv("ADMIN_LAST_NAME")
        role_name = os.getenv("ADMIN_ROLE")

        if not admin_email or not password:
            print("ADMIN_EMAIL or ADMIN_PASSWORD not defined in .env file.")
            return

        result = await db.execute(select(User).where(User.email == admin_email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            print("The administrator user already exists.")
            return

        role_result = await db.execute(select(Role).where(Role.name == role_name))
        role = role_result.scalar_one_or_none()

        status_result = await db.execute(select(Status).where(Status.name == "active"))
        status = status_result.scalar_one_or_none()

        if not role or not status:
            print("Role or status not found. Make sure you've created it.")
            return

        new_user = User(
            email=admin_email,
            password=get_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            role_id=role.id,
            status_id=status.id,
            privacy_policy_accepted=True  
        )

        db.add(new_user)
        await db.commit()
        print(" Administrator user created successfully.")
