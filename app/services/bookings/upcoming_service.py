from datetime import datetime, timedelta, timezone
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, exists
from sqlalchemy.orm import selectinload

from app.models.booking.bookings import Booking
from app.models.teachers.availability import Availability
from app.models.users.preference import Preference
from app.models.common.status import Status
from app.models.teachers.document import Document
from app.models.booking.payment_bookings import PaymentBooking


async def get_upcoming_bookings_for_user(
    db: AsyncSession,
    user_id: int,
    offset: int = 0,
    limit: int = 6,
) -> Dict:
    """
    Lista reservas futuras del usuario autenticado (funciona para docente y alumno) con paginación.
    - Si el usuario es docente: reservas donde Availability.user_id == user_id
    - Si el usuario es alumno: reservas donde Booking.user_id == user_id
    - Considera ambos casos (OR), así funciona igual para cualquiera de los roles
    - Sólo reservas con start_time > ahora (zona MX: UTC-6)
    - Excluye reservas con status 'cancelled'
    - Incluye: materia (Document.expertise_area del docente) y modalidad (Preference.modality.name)
    - participant_role: "teacher" o "student" respecto al usuario autenticado
    """
    current_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)

    # Status cancelado
    cancelled_status_id = None
    cancelled_q = await db.execute(select(Status).where(Status.name == "cancelled"))
    cancelled = cancelled_q.scalar_one_or_none()
    if cancelled:
        cancelled_status_id = cancelled.id

    # Base query: unimos Availability para poder distinguir rol y filtrar por docente
    base_query = (
        select(Booking)
        .join(Availability, Booking.availability_id == Availability.id)
        .where(
            Booking.start_time > current_time,
            or_(
                Availability.user_id == user_id,  # docente
                Booking.user_id == user_id        # alumno
            )
        )
    )
    if cancelled_status_id is not None:
        base_query = base_query.where(Booking.status_id != cancelled_status_id)

    # Total
    total_q = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    # Datos paginados con relaciones necesarias
    data_q = (
        base_query
        .order_by(Booking.start_time.asc())
        .limit(limit)
        .offset(offset)
        .options(
            selectinload(Booking.availability).selectinload(Availability.preference).selectinload(Preference.modality),
            selectinload(Booking.status),
        )
    )
    result = await db.execute(data_q)
    bookings: List[Booking] = result.scalars().all()

    # Pre-cargar documentos de posibles docentes involucrados en estos bookings
    teacher_ids = {b.availability.user_id for b in bookings if b.availability is not None}
    docs_map: Dict[int, Document] = {}
    if teacher_ids:
        docs_q = await db.execute(select(Document).where(Document.user_id.in_(teacher_ids)))
        for d in docs_q.scalars().all():
            docs_map[d.user_id] = d

    items = []
    for b in bookings:
        teacher_id = b.availability.user_id if b.availability else None
        participant_role = "teacher" if teacher_id == user_id else "student"

        # materia desde el docente de la clase
        doc = docs_map.get(teacher_id) if teacher_id else None
        materia = doc.expertise_area if doc else None

        modality_name = None
        if b.availability and b.availability.preference and b.availability.preference.modality:
            modality_name = b.availability.preference.modality.name

        status_name = b.status.name if getattr(b, 'status', None) else None

        items.append({
            "booking_id": b.id,
            "availability_id": b.availability_id,
            "start_time": b.start_time,
            "end_time": b.end_time,
            "materia": materia,
            "modality": modality_name,
            "participant_role": participant_role,
            "status": status_name,
        })

    has_more = (offset + limit) < total

    return {
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
    }


async def get_bookings_by_status_for_user(
    db: AsyncSession,
    user_id: int,
    status: str = "upcoming",  # upcoming | past | cancelled | all
    offset: int = 0,
    limit: int = 6,
) -> Dict:
    """
    Lista reservas del usuario autenticado por estado solicitado.
    - upcoming: futuras (start_time > ahora) excluyendo canceladas
    - past: finalizadas (end_time <= ahora)
    - cancelled: con status 'cancelled'
    - all: todas en las que participa
    """
    current_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)

    # Status cancelado
    cancelled_status = (await db.execute(select(Status).where(Status.name == "cancelled"))).scalar_one_or_none()
    cancelled_status_id = cancelled_status.id if cancelled_status else None

    # Base query: participación como docente o alumno
    teacher_avail_subq = select(Availability.id).where(Availability.user_id == user_id)
    base = select(Booking).where(
        or_(
            Booking.user_id == user_id,
            Booking.availability_id.in_(teacher_avail_subq)
        )
    )

    if status == "upcoming":
        base = base.where(Booking.start_time > current_time)
        if cancelled_status_id is not None:
            base = base.where(Booking.status_id != cancelled_status_id)
    elif status == "past":
        base = base.where(Booking.end_time <= current_time)
    elif status == "cancelled":
        if cancelled_status_id is not None:
            base = base.where(Booking.status_id == cancelled_status_id)
        else:
            # Si no existe el status en BD, devolver vacío
            return {"items": [], "total": 0, "offset": offset, "limit": limit, "has_more": False}
    elif status == "all":
        pass
    else:
        # valor inválido, devolver vacío
        return {"items": [], "total": 0, "offset": offset, "limit": limit, "has_more": False}

    # Total
    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    # Datos paginados + relaciones
    data_q = (
        base.order_by(Booking.start_time.asc())
        .limit(limit).offset(offset)
        .options(
            selectinload(Booking.availability)
                .selectinload(Availability.preference)
                .selectinload(Preference.modality),
            selectinload(Booking.status),
        )
    )
    result = await db.execute(data_q)
    bookings: List[Booking] = result.scalars().all()

    # Pre-cargar documentos de docentes
    teacher_ids = {b.availability.user_id for b in bookings if b.availability is not None}
    docs_map: Dict[int, Document] = {}
    if teacher_ids:
        docs_q = await db.execute(select(Document).where(Document.user_id.in_(teacher_ids)))
        for d in docs_q.scalars().all():
            docs_map[d.user_id] = d

    items = []
    for b in bookings:
        teacher_id = b.availability.user_id if b.availability else None
        participant_role = "teacher" if teacher_id == user_id else "student"
        doc = docs_map.get(teacher_id) if teacher_id else None
        materia = doc.expertise_area if doc else None
        modality_name = None
        if b.availability and b.availability.preference and b.availability.preference.modality:
            modality_name = b.availability.preference.modality.name

        status_name = b.status.name if getattr(b, 'status', None) else None

        items.append({
            "booking_id": b.id,
            "availability_id": b.availability_id,
            "start_time": b.start_time,
            "end_time": b.end_time,
            "materia": materia,
            "modality": modality_name,
            "participant_role": participant_role,
            "status": status_name,
        })

    has_more = (offset + limit) < total
    return {"items": items, "total": total, "offset": offset, "limit": limit, "has_more": has_more}


async def search_bookings_for_user(
    db: AsyncSession,
    user_id: int,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    status: str | None = None,  # status name
    min_price: float | None = None,  # currency units (e.g., MXN)
    max_price: float | None = None,
    offset: int = 0,
    limit: int = 6,
) -> Dict:
    """
    Búsqueda de reservas por filtros combinables: rango de fechas (start_time),
    estado (por nombre) y rango de precio (PaymentBooking.total_amount).
    Funciona para docente y alumno (usuario participa como teacher o student).
    """
    # Base participación
    teacher_avail_subq = select(Availability.id).where(Availability.user_id == user_id)
    base = select(Booking).where(
        or_(
            Booking.user_id == user_id,
            Booking.availability_id.in_(teacher_avail_subq),
        )
    )

    # Filtro por rango de fechas (start_time)
    if date_from is not None:
        base = base.where(Booking.start_time >= date_from)
    if date_to is not None:
        base = base.where(Booking.start_time <= date_to)

    # Filtro por status por nombre
    if status:
        status_row = (await db.execute(select(Status).where(Status.name == status))).scalar_one_or_none()
        if status_row:
            base = base.where(Booking.status_id == status_row.id)
        else:
            # si no existe, no habrá resultados
            return {"items": [], "total": 0, "offset": offset, "limit": limit, "has_more": False}

    # Filtro por rango de precio usando subconsulta a PaymentBooking (en centavos)
    price_min_cents = int(min_price * 100) if min_price is not None else None
    price_max_cents = int(max_price * 100) if max_price is not None else None
    if price_min_cents is not None or price_max_cents is not None:
        price_cond = []
        if price_min_cents is not None:
            price_cond.append(PaymentBooking.total_amount >= price_min_cents)
        if price_max_cents is not None:
            price_cond.append(PaymentBooking.total_amount <= price_max_cents)

        pb_subq = select(PaymentBooking.id).where(
            PaymentBooking.booking_id == Booking.id,
            and_(True, *price_cond) if price_cond else True,
        )
        base = base.where(exists(pb_subq))

    # Total
    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    # Datos paginados con relaciones
    data_q = (
        base.order_by(Booking.start_time.asc())
        .limit(limit).offset(offset)
        .options(
            selectinload(Booking.availability)
                .selectinload(Availability.preference)
                .selectinload(Preference.modality),
            selectinload(Booking.status),
        )
    )
    result = await db.execute(data_q)
    bookings: List[Booking] = result.scalars().all()

    # Pre-cargar documentos
    teacher_ids = {b.availability.user_id for b in bookings if b.availability is not None}
    docs_map: Dict[int, Document] = {}
    if teacher_ids:
        docs_q = await db.execute(select(Document).where(Document.user_id.in_(teacher_ids)))
        for d in docs_q.scalars().all():
            docs_map[d.user_id] = d

    items = []
    for b in bookings:
        teacher_id = b.availability.user_id if b.availability else None
        participant_role = "teacher" if teacher_id == user_id else "student"
        doc = docs_map.get(teacher_id) if teacher_id else None
        materia = doc.expertise_area if doc else None
        modality_name = None
        if b.availability and b.availability.preference and b.availability.preference.modality:
            modality_name = b.availability.preference.modality.name
        status_name = b.status.name if getattr(b, 'status', None) else None

        items.append({
            "booking_id": b.id,
            "availability_id": b.availability_id,
            "start_time": b.start_time,
            "end_time": b.end_time,
            "materia": materia,
            "modality": modality_name,
            "participant_role": participant_role,
            "status": status_name,
        })

    has_more = (offset + limit) < total
    return {"items": items, "total": total, "offset": offset, "limit": limit, "has_more": has_more}
