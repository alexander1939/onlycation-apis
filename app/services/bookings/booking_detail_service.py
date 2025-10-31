from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from typing import Dict

from app.models.booking.bookings import Booking
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.confirmation import Confirmation
from app.models.teachers.availability import Availability
from app.models.users.preference import Preference
from app.models.common.modality import Modality
from app.models.users.user import User
from app.models.common.status import Status
from app.models.teachers.document import Document


async def get_booking_detail_for_user(db: AsyncSession, booking_id: int, user_id: int) -> Dict:
    # Cargar la reserva con relaciones necesarias
    query = (
        select(Booking)
        .where(Booking.id == booking_id)
        .options(
            selectinload(Booking.user),  # estudiante
            selectinload(Booking.status),
            selectinload(Booking.availability)
                .selectinload(Availability.user),  # docente
            selectinload(Booking.availability)
                .selectinload(Availability.preference)
                .selectinload(Preference.modality),
            selectinload(Booking.payment_bookings),  # para llegar a confirmations
        )
    )
    result = await db.execute(query)
    booking = result.scalar_one_or_none()
    if not booking:
        raise ValueError("Reserva no encontrada")

    # Verificar que el usuario participa en la reserva (docente o alumno)
    teacher_id = booking.availability.user_id if booking.availability else None
    if not (booking.user_id == user_id or teacher_id == user_id):
        raise PermissionError("No tienes permisos para ver esta reserva")

    # Obtener datos básicos
    student: User = booking.user
    teacher: User = booking.availability.user if booking.availability else None
    modality_name = (
        booking.availability.preference.modality.name
        if booking.availability and booking.availability.preference and booking.availability.preference.modality
        else None
    )

    # Materia desde Document del docente
    materia = None
    if teacher:
        doc_q = await db.execute(select(Document).where(Document.user_id == teacher.id))
        doc = doc_q.scalar_one_or_none()
        if doc:
            materia = doc.expertise_area

    # Status legible
    status_name = booking.status.name if booking.status else None

    # Link de clase (si aplica)
    class_link = booking.class_space

    # Confirmaciones (buscamos PaymentBooking -> Confirmation)
    confirmation_teacher = None
    confirmation_student = None
    total_paid_value = None
    if booking.payment_bookings:
        pb_ids = [pb.id for pb in booking.payment_bookings]
        conf_q = await db.execute(select(Confirmation).where(Confirmation.payment_booking_id.in_(pb_ids)))
        conf = conf_q.scalar_one_or_none()
        if conf:
            confirmation_teacher = conf.confirmation_date_teacher
            confirmation_student = conf.confirmation_date_student

        # Tomar el primer PaymentBooking y usar su total_amount (en centavos)
        first_pb = booking.payment_bookings[0]
        if first_pb and first_pb.total_amount is not None:
            total_paid_value = round(first_pb.total_amount / 100.0, 2)
    else:
        # Fallback: buscar PaymentBooking por booking_id (por si la relación no cargó items)
        pb_q = await db.execute(select(PaymentBooking).where(PaymentBooking.booking_id == booking.id))
        first_pb = pb_q.scalar_one_or_none()
        if first_pb and first_pb.total_amount is not None:
            total_paid_value = round(first_pb.total_amount / 100.0, 2)

    return {
        "booking_id": booking.id,
        "created_at": booking.created_at,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "modality": modality_name,
        "class_link": class_link,
        "materia": materia,
        "status": status_name,
        "teacher": {
            "id": teacher.id if teacher else None,
            "first_name": teacher.first_name if teacher else None,
            "last_name": teacher.last_name if teacher else None,
        },
        "student": {
            "id": student.id if student else None,
            "first_name": student.first_name if student else None,
            "last_name": student.last_name if student else None,
        },
        "confirmation_teacher": confirmation_teacher,
        "confirmation_student": confirmation_student,
        "total_paid": total_paid_value,
    }
