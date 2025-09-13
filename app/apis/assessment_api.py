from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.apis.deps import auth_required, get_db, public_access
from app.schemas.bookings.assessment_schema import (
    AssessmentCreate, TeacherCommentsListResponse, TeacherCommentResponse
)
from app.services.bookings.assessment_service import (
    create_assessment
)
from app.models.booking.assessment import Assessment
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.bookings import Booking
from app.models.teachers.availability import Availability
from app.models.users import User 

router = APIRouter()

# Crear assessment (requiere auth)
@router.post("/create/", response_model=TeacherCommentsListResponse, dependencies=[Depends(auth_required)])
async def add_assessment(
    request: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    return await create_assessment(db, user_data["user_id"], request)



@router.get("/teacher/comments/", response_model=TeacherCommentsListResponse, dependencies=[Depends(auth_required)])
async def get_teacher_comments(
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    teacher_id = user_data["user_id"]

    query = (
        select(
            Assessment.id,
            Assessment.comment,
            Assessment.qualification,
            User.id.label("student_id"),
            func.concat(User.first_name, " ", User.last_name).label("student_name"),
        )
        .join(PaymentBooking, PaymentBooking.id == Assessment.payment_booking_id)
        .join(Booking, Booking.id == PaymentBooking.booking_id)
        .join(Availability, Availability.id == Booking.availability_id)
        .join(User, User.id == Assessment.user_id)  
        .where(Availability.user_id == teacher_id) 
    )

    result = await db.execute(query)
    comments = result.mappings().all()

    if not comments:
        raise HTTPException(status_code=404, detail="No se encontraron comentarios para este docente")

    # Envolver la lista de comentarios en el objeto esperado
    return TeacherCommentsListResponse(
        success=True,
        message="Comentarios obtenidos correctamente",
        data=[TeacherCommentResponse(**c) for c in comments]
    )



@router.get("/public/comments/", response_model=TeacherCommentsListResponse, dependencies=[Depends(public_access)])
async def get_all_comments(
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            Assessment.id,
            Assessment.comment,
            Assessment.qualification,
            User.id.label("student_id"),
            func.concat(User.first_name, " ", User.last_name).label("student_name"),
        )
        .join(User, User.id == Assessment.user_id) 
    )

    result = await db.execute(query)
    comments = result.mappings().all()

    if not comments:
        raise HTTPException(status_code=404, detail="No se encontraron comentarios")

    return TeacherCommentsListResponse(
        success=True,
        message="Comentarios obtenidos correctamente (acceso público)",
        data=[TeacherCommentResponse(**c) for c in comments]
    )
