from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.common.educational_level import EducationalLevel
from app.schemas.common.educational_level_schema import EducationalLevelCreate, EducationalLevelUpdate

class EducationalLevelService:
    @staticmethod
    async def get_educational_levels(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[EducationalLevel]:
        """
        Retrieve a list of educational levels with pagination.
        """
        result = await db.execute(
            select(EducationalLevel)
            .where(EducationalLevel.status_id == 1)  # Assuming 1 is active status
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_educational_level(db: AsyncSession, level_id: int) -> Optional[EducationalLevel]:
        """
        Get a single educational level by ID.
        """
        result = await db.execute(
            select(EducationalLevel)
            .where(EducationalLevel.id == level_id)
        )
        return result.scalars().first()

    @staticmethod
    async def create_educational_level(db: AsyncSession, level: EducationalLevelCreate) -> EducationalLevel:
        """
        Create a new educational level.
        """
        db_level = EducationalLevel(**level.model_dump())
        db.add(db_level)
        await db.commit()
        await db.refresh(db_level)
        return db_level

    @staticmethod
    async def update_educational_level(
        db: AsyncSession, 
        level_id: int, 
        level: EducationalLevelUpdate
    ) -> Optional[EducationalLevel]:
        """
        Update an existing educational level.
        """
        db_level = await EducationalLevelService.get_educational_level(db, level_id)
        if not db_level:
            return None
            
        update_data = level.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_level, field, value)
            
        await db.commit()
        await db.refresh(db_level)
        return db_level

    @staticmethod
    async def delete_educational_level(db: AsyncSession, level_id: int) -> bool:
        """
        Delete an educational level (soft delete by setting status_id to inactive).
        """
        db_level = await EducationalLevelService.get_educational_level(db, level_id)
        if not db_level:
            return False
            
        db_level.status_id = 2  # Assuming 2 is inactive status
        await db.commit()
        return True
