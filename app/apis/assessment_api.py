from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.apis.deps import auth_required, get_db, public_access
from app.schemas.bookings.assessment_schema import (
    AssessmentCreate, TeacherCommentsListResponse, TeacherCommentResponse
)
from app.services.bookings.assessment_service import (
    create_assessment,
    get_teacher_comments_service,
    get_public_comments_service,
    get_student_comments_service
)

router = APIRouter()

# Crear assessment (requiere auth)
@router.post("/create/{payment_booking_id}", response_model=AssessmentCreate, dependencies=[Depends(auth_required)])
async def add_assessment(
    payment_booking_id: int,
    request: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    return await create_assessment(db, user_data["user_id"], payment_booking_id, request)


# Comentarios privados (docente autenticado)
@router.get("/teacher/comments/", response_model=TeacherCommentsListResponse, dependencies=[Depends(auth_required)])
async def get_teacher_comments(
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    teacher_id = user_data["user_id"]
    comments = await get_teacher_comments_service(db, teacher_id)

    return TeacherCommentsListResponse(
        success=True,
        message="Comentarios obtenidos correctamente",
        data=[TeacherCommentResponse(**c) for c in comments]
    )


# Comentarios públicos por docente
@router.get(
    "/public/comments/{teacher_id}",
    response_model=TeacherCommentsListResponse,
    dependencies=[Depends(public_access)]
)
async def get_public_comments(
    teacher_id: int,
    db: AsyncSession = Depends(get_db),
):
    comments = await get_public_comments_service(db, teacher_id)

    return TeacherCommentsListResponse(
        success=True,
        message=f"Comentarios del docente {teacher_id} obtenidos correctamente (acceso público)",
        data=[TeacherCommentResponse(**c) for c in comments]
    )


# Comentarios de un estudiante autenticado
@router.get(
    "/student/comments/",
    response_model=TeacherCommentsListResponse,
    dependencies=[Depends(auth_required)]
)
async def get_student_comments(
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    student_id = user_data["user_id"]
    comments = await get_student_comments_service(db, student_id)

    return TeacherCommentsListResponse(
        success=True,
        message="Comentarios del estudiante obtenidos correctamente",
        data=[TeacherCommentResponse(**c) for c in comments]
    )
