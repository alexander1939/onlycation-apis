from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.apis.deps import get_db
from app.services.teachers.teachers_public_service import PublicService
from app.schemas.teachers.teachers_public_shema import PublicTeacherProfile

router = APIRouter()

@router.get("/teachers/", response_model=list[PublicTeacherProfile])
async def public_access(
    min_bookings: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        teachers_data = await PublicService.get_public_teachers(db, min_bookings)
        return teachers_data
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al obtener datos públicos: {str(e)}"
        )