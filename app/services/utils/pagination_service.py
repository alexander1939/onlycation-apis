from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import TypeVar, Generic, Type, Sequence, Optional, Dict, Any
from fastapi import HTTPException

T = TypeVar('T')

class PaginationService:
    @staticmethod
    async def get_paginated_data(
        db: AsyncSession,
        model: Type[T],
        offset: int = 0,
        limit: int = 6,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Función genérica para obtener datos paginados de cualquier modelo
        
        Args:
            db: Sesión de base de datos
            model: Modelo SQLAlchemy
            offset: Posición desde donde empezar
            limit: Cantidad de elementos a traer
            filters: Filtros opcionales para aplicar
        
        Returns:
            dict con datos paginados

        ejemplo de uso:
        // Primera carga
        fetch('/?limit=6')  // offset=0 automático

        // Usuario hace scroll → cargar más
        fetch('/?offset=6&limit=6')

        // Usuario hace scroll → cargar más  
        fetch('/?offset=12&limit=6')

        // Y así sucesivamente...
        """
        try:
            # Construir la consulta base
            query = select(model)
            
            # Aplicar filtros si existen
            if filters:
                for field, value in filters.items():
                    if hasattr(model, field) and value is not None:
                        query = query.where(getattr(model, field) == value)
            
            # Obtener el total de registros
            total_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(total_query)
            total_count = total_result.scalar() or 0
            
            # Obtener datos con paginación
            paginated_query = query.limit(limit).offset(offset)
            result = await db.execute(paginated_query)
            items = result.scalars().all()
            
            # Calcular si hay más datos
            has_more = (offset + limit) < total_count
            
            return {
                "items": items,
                "total": total_count,
                "offset": offset,
                "limit": limit,
                "has_more": has_more
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in pagination: {str(e)}") 