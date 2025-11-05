from sqlalchemy.orm import Session
from sqlalchemy import func, desc, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Document, Price, Preference, Booking, EducationalLevel
from app.models.users.profile import Profile
from app.models.teachers.availability import Availability
from app.models.teachers.video import Video
from app.models.booking.assessment import Assessment
from app.models.booking.payment_bookings import PaymentBooking
from typing import Optional
import json

class PublicService:
    @staticmethod
    async def get_public_teachers(db: AsyncSession, min_bookings: Optional[int] = None):
        # Construimos la consulta
        stmt = (
            select(
                User.id.label('teacher_id'),
                User.first_name,
                User.last_name,
                Document.description,
                Document.expertise_area,
                Price.extra_hour_price.label('price_per_class'),
                EducationalLevel.name.label('educational_level'),
                func.count(Booking.id).label('total_bookings')
            )
            .outerjoin(Document, User.id == Document.user_id)
            .outerjoin(Price, User.id == Price.user_id)
            .outerjoin(Preference, User.id == Preference.user_id)
            .outerjoin(EducationalLevel, Preference.educational_level_id == EducationalLevel.id)
            .outerjoin(Booking, User.id == Booking.user_id)
            .where(User.role_id == 1)  # solo profesores
            .where(User.status_id == 1)  # activos
            .group_by(
                User.id,
                User.first_name,
                User.last_name,
                Document.description,
                Document.expertise_area,
                Price.selected_prices,
                EducationalLevel.name
            )
            .order_by(desc(func.count(Booking.id)))
        )
        
        # Ejecutamos la consulta
        result = await db.execute(stmt)
        results = result.all()
        
        # Aplicar filtro por cantidad mínima de reservas
        filtered_results = []
        for row in results:
            if min_bookings is not None and row.total_bookings < min_bookings:
                continue
            filtered_results.append(row)
        
        return [
    {
        'teacher_id': row.teacher_id,
        'first_name': row.first_name,
        'last_name': row.last_name,
        'description': row.description or "Sin descripción",
        'subject': row.expertise_area or "Sin materia",
        'price_per_class': (
            float(json.loads(row.price_per_class)[0])
            if row.price_per_class and isinstance(row.price_per_class, str)
            else 0.0
        ),
        'educational_level': row.educational_level or "No definido",
        'total_bookings': row.total_bookings
    }
    for row in filtered_results
]

    @staticmethod
    async def search_teachers_catalog(
        db: AsyncSession,
        name: Optional[str] = None,
        subject: Optional[str] = None,
        educational_level_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        page: int = 1,
        page_size: int = 10
    ):
        """
        Búsqueda de docentes con filtros múltiples.
        
        Filtros:
        - name: Busca en nombre y apellido
        - subject: Área de especialidad (expertise_area)
        - educational_level_id: Nivel educativo del docente
        - min_price/max_price: Rango de precio por hora
        - min_rating: Calificación mínima (promedio de estrellas)
        - page: Número de página (default: 1)
        - page_size: Resultados por página (default: 10)
        
        Ordenamiento: Por calificación descendente (más calificados primero)
        """
        
        # Subconsulta para calcular el promedio de calificaciones por docente
        rating_subquery = (
            select(
                Availability.user_id,
                func.coalesce(func.avg(Assessment.qualification), 0).label("avg_rating")
            )
            .select_from(Availability)
            .outerjoin(Booking, Booking.availability_id == Availability.id)
            .outerjoin(PaymentBooking, PaymentBooking.booking_id == Booking.id)
            .outerjoin(Assessment, Assessment.payment_booking_id == PaymentBooking.id)
            .group_by(Availability.user_id)
            .subquery()
        )
        
        # Query principal
        query = (
            select(
                User.id.label("user_id"),
                User.first_name,
                User.last_name,
                EducationalLevel.name.label("educational_level"),
                Document.expertise_area,
                Price.selected_prices.label("price_per_hour"),
                rating_subquery.c.avg_rating.label("average_rating"),
                Video.embed_url.label("video_embed_url"),
                Video.thumbnail_url.label("video_thumbnail_url")
            )
            .select_from(User)
            .outerjoin(Profile, Profile.user_id == User.id)
            .outerjoin(Preference, Preference.user_id == User.id)
            .outerjoin(EducationalLevel, EducationalLevel.id == Preference.educational_level_id)
            .outerjoin(Document, Document.user_id == User.id)
            .outerjoin(Price, Price.user_id == User.id)
            .outerjoin(Video, Video.user_id == User.id)
            .outerjoin(rating_subquery, rating_subquery.c.user_id == User.id)
            .where(User.role_id == 1)  # Solo docentes (teacher)
            .where(User.status_id == 1)  # Solo activos
        )
        
        # Aplicar filtros
        filters = []
        
        # Filtro por nombre
        if name:
            name_filter = or_(
                User.first_name.ilike(f"%{name}%"),
                User.last_name.ilike(f"%{name}%")
            )
            filters.append(name_filter)
        
        # Filtro por materia/área de especialidad
        if subject:
            filters.append(Document.expertise_area.ilike(f"%{subject}%"))
        
        # Filtro por nivel educativo
        if educational_level_id:
            filters.append(Preference.educational_level_id == educational_level_id)
        
        # Filtro por rango de precio
        if min_price is not None:
            filters.append(Price.selected_prices >= min_price)
        if max_price is not None:
            filters.append(Price.selected_prices <= max_price)
        
        # Aplicar todos los filtros
        if filters:
            query = query.where(and_(*filters))
        
        # Ordenar por calificación descendente (más calificados primero)
        query = query.order_by(desc(rating_subquery.c.avg_rating))
        
        # Ejecutar query
        result = await db.execute(query)
        teachers = result.all()
        
        # Filtrar por calificación mínima (después de la query porque es calculado)
        if min_rating is not None:
            teachers = [t for t in teachers if (t.average_rating or 0) >= min_rating]
        
        # Total de resultados
        total = len(teachers)
        
        # Aplicar paginación
        offset = (page - 1) * page_size
        teachers_paginated = teachers[offset:offset + page_size]
        
        # Convertir a diccionarios
        teachers_list = []
        for t in teachers_paginated:
            teachers_list.append({
                "user_id": t.user_id,
                "first_name": t.first_name,
                "last_name": t.last_name,
                "educational_level": t.educational_level,
                "expertise_area": t.expertise_area,
                "price_per_hour": float(t.price_per_hour) if t.price_per_hour else None,
                "average_rating": round(float(t.average_rating or 0), 2),
                "video_embed_url": t.video_embed_url,
                "video_thumbnail_url": t.video_thumbnail_url
            })
        
        return {
            "teachers": teachers_list,
            "total": total,
            "page": page,
            "page_size": page_size
        }