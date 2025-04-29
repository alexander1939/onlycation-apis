
from fastapi import APIRouter, Depends
from app.services.auths.register_service import register_user
from app.schemas.auths.register_shemas import RegisterUserRequest
from app.apis.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/register/student/")
async def register_student_route(request: RegisterUserRequest, db: AsyncSession = Depends(get_db)):
    return await register_user(request, "student", db)

@router.post("/register/teacher/")
async def register_teacher_route(request: RegisterUserRequest, db: AsyncSession = Depends(get_db)):
    return await register_user(request, "teacher", db)