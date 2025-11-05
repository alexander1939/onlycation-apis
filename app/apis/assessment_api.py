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
from app.models.booking.assessment import Assessment
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.bookings import Booking
from app.models.teachers.availability import Availability
from sqlalchemy import select, func

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

@router.get("/my-rating/", dependencies=[Depends(auth_required)])
async def get_my_teacher_rating(
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Obtener el promedio de calificaciones (estrellas) del docente autenticado.
    Calcula el promedio de todas las calificaciones recibidas (1-5 estrellas).
    """
    teacher_id = user_data["user_id"]
    
    # Consultar el promedio de calificaciones del docente
    query = (
        select(func.avg(Assessment.qualification).label("average_rating"))
        .join(PaymentBooking, Assessment.payment_booking_id == PaymentBooking.id)
        .join(Booking, PaymentBooking.booking_id == Booking.id)
        .join(Availability, Booking.availability_id == Availability.id)
        .where(Availability.user_id == teacher_id)
        .where(Assessment.qualification.isnot(None))
    )
    
    result = await db.execute(query)
    average = result.scalar_one_or_none()
    
    # Si no hay calificaciones, retornar 0
    if average is None:
        average = 0.0
    else:
        # Redondear a 2 decimales
        average = round(float(average), 2)
    
    return {
        "success": True,
        "message": "Promedio de calificación obtenido exitosamente",
        "data": {
            "average_rating": average
        }
    }
