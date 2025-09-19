from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models import User, Document, Price, Preference, Booking, EducationalLevel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
            .where(User.role_id == 2)  # solo profesores
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