from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.common.modality import Modality
from app.schemas.common.modality_schema import ModalityCreate, ModalityUpdate

class ModalityService:
    @staticmethod
    async def get_modalities(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Modality]:
        """
        Retrieve a list of modalities with pagination.
        """
        result = await db.execute(
            select(Modality)
            .where(Modality.status_id == 1)  # Assuming 1 is active status
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_modality(db: AsyncSession, modality_id: int) -> Optional[Modality]:
        """
        Get a single modality by ID.
        """
        result = await db.execute(
            select(Modality)
            .where(Modality.id == modality_id)
        )
        return result.scalars().first()

    @staticmethod
    async def create_modality(db: AsyncSession, modality: ModalityCreate) -> Modality:
        """
        Create a new modality.
        """
        db_modality = Modality(**modality.model_dump())
        db.add(db_modality)
        await db.commit()
        await db.refresh(db_modality)
        return db_modality

    @staticmethod
    async def update_modality(
        db: AsyncSession, 
        modality_id: int, 
        modality: ModalityUpdate
    ) -> Optional[Modality]:
        """
        Update an existing modality.
        """
        db_modality = await ModalityService.get_modality(db, modality_id)
        if not db_modality:
            return None
            
        update_data = modality.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_modality, field, value)
            
        await db.commit()
        await db.refresh(db_modality)
        return db_modality

    @staticmethod
    async def delete_modality(db: AsyncSession, modality_id: int) -> bool:
        """
        Delete a modality (soft delete by setting status_id to inactive).
        """
        db_modality = await ModalityService.get_modality(db, modality_id)
        if not db_modality:
            return False
            
        db_modality.status_id = 2  # Assuming 2 is inactive status
        await db.commit()
        return True
