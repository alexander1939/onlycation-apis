from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.schemas.common.educational_level_schema import (
    EducationalLevel, 
    EducationalLevelCreate, 
    EducationalLevelUpdate
)
from app.schemas.common.modality_schema import (
    Modality,
    ModalityCreate,
    ModalityUpdate
)
from app.services.common.educational_level_service import EducationalLevelService
from app.services.common.modality_service import ModalityService
from app.apis.deps import get_db

router = APIRouter()

# Educational Level Endpoints
@router.get("/educational-levels/", response_model=List[EducationalLevel])
async def read_educational_levels(
    skip: int = 0, 
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve educational levels with pagination.
    """
    return await EducationalLevelService.get_educational_levels(db, skip=skip, limit=limit)

@router.get("/educational-levels/{level_id}", response_model=EducationalLevel)
async def read_educational_level(
    level_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific educational level by ID.
    """
    db_level = await EducationalLevelService.get_educational_level(db, level_id=level_id)
    if db_level is None:
        raise HTTPException(status_code=404, detail="Educational level not found")
    return db_level

@router.post("/educational-levels/", response_model=EducationalLevel, status_code=status.HTTP_201_CREATED)
async def create_educational_level(
    level: EducationalLevelCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new educational level.
    """
    return await EducationalLevelService.create_educational_level(db=db, level=level)

@router.put("/educational-levels/{level_id}", response_model=EducationalLevel)
async def update_educational_level(
    level_id: int, 
    level: EducationalLevelUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Update an educational level.
    """
    db_level = await EducationalLevelService.update_educational_level(
        db=db, level_id=level_id, level=level
    )
    if db_level is None:
        raise HTTPException(status_code=404, detail="Educational level not found")
    return db_level

@router.delete("/educational-levels/{level_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_educational_level(
    level_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an educational level (soft delete).
    """
    success = await EducationalLevelService.delete_educational_level(db=db, level_id=level_id)
    if not success:
        raise HTTPException(status_code=404, detail="Educational level not found")
    return {"ok": True}

# Modality Endpoints
@router.get("/modalities/", response_model=List[Modality])
async def read_modalities(
    skip: int = 0, 
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve modalities with pagination.
    """
    return await ModalityService.get_modalities(db, skip=skip, limit=limit)

@router.get("/modalities/{modality_id}", response_model=Modality)
async def read_modality(
    modality_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific modality by ID.
    """
    db_modality = await ModalityService.get_modality(db, modality_id=modality_id)
    if db_modality is None:
        raise HTTPException(status_code=404, detail="Modality not found")
    return db_modality

@router.post("/modalities/", response_model=Modality, status_code=status.HTTP_201_CREATED)
async def create_modality(
    modality: ModalityCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new modality.
    """
    return await ModalityService.create_modality(db=db, modality=modality)

@router.put("/modalities/{modality_id}", response_model=Modality)
async def update_modality(
    modality_id: int, 
    modality: ModalityUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Update a modality.
    """
    db_modality = await ModalityService.update_modality(
        db=db, modality_id=modality_id, modality=modality
    )
    if db_modality is None:
        raise HTTPException(status_code=404, detail="Modality not found")
    return db_modality

@router.delete("/modalities/{modality_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_modality(
    modality_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a modality (soft delete).
    """
    success = await ModalityService.delete_modality(db=db, modality_id=modality_id)
    if not success:
        raise HTTPException(status_code=404, detail="Modality not found")
    return {"ok": True}
