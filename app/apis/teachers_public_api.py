from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.apis.deps import get_db
from app.services.teachers.teachers_public_service import PublicService
from app.schemas.teachers.teachers_public_shema import PublicTeacherProfile, TeacherSearchResponse, TeacherSearchResult
from pydantic import BaseModel

router = APIRouter()

class PaginationResponse(BaseModel):
    success: bool
    message: str
    data: list[PublicTeacherProfile]
    total: int
    page: int
    page_size: int
    total_pages: int

@router.get("/teachers/", response_model=PaginationResponse)
async def public_access(
    min_bookings: Optional[int] = None,
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(10, ge=1, le=100, description="Resultados por página"),
    db: AsyncSession = Depends(get_db)
):
    try:
        teachers_data = await PublicService.get_public_teachers(db, min_bookings)
        total = len(teachers_data)
        total_pages = total // page_size + (1 if total % page_size else 0)
        start = (page - 1) * page_size
        end = start + page_size
        data = teachers_data[start:end]
        
        return PaginationResponse(
            success=True,
            message=f"Se encontraron {total} docente(s). Página {page} de {total_pages}",
            data=data,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al obtener datos públicos: {str(e)}"
        )

@router.get("/search-teachers/", response_model=TeacherSearchResponse)
async def search_teachers_catalog(
    name: Optional[str] = Query(None, description="Buscar por nombre o apellido del docente"),
    subject: Optional[str] = Query(None, description="Buscar por materia o área de especialidad"),
    educational_level_id: Optional[int] = Query(None, description="Filtrar por nivel educativo (ID)"),
    min_price: Optional[float] = Query(None, ge=0, description="Precio mínimo por hora"),
    max_price: Optional[float] = Query(None, ge=0, description="Precio máximo por hora"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Calificación mínima (0-5 estrellas)"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(10, ge=1, le=100, description="Resultados por página (máx: 100)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Búsqueda pública de docentes con filtros múltiples y paginación.
    
    **Sin filtros:** Retorna TODOS los docentes ordenados por calificación (mayor a menor)
    
    **Filtros disponibles:**
    - `name`: Busca en nombre y apellido
    - `subject`: Materia o área de especialidad
    - `educational_level_id`: Nivel educativo del docente
    - `min_price` / `max_price`: Rango de precio por hora
    - `min_rating`: Calificación mínima en estrellas (0-5)
    - `page`: Número de página (default: 1)
    - `page_size`: Resultados por página (default: 10, max: 100)
    
    **Ordenamiento:** Por calificación descendente (⭐ más calificados primero)
    """
    try:
        result = await PublicService.search_teachers_catalog(
            db=db,
            name=name,
            subject=subject,
            educational_level_id=educational_level_id,
            min_price=min_price,
            max_price=max_price,
            min_rating=min_rating,
            page=page,
            page_size=page_size
        )
        
        # Calcular total de páginas
        import math
        total_pages = math.ceil(result["total"] / page_size) if result["total"] > 0 else 0
        
        return TeacherSearchResponse(
            success=True,
            message=f"Se encontraron {result['total']} docente(s). Página {page} de {total_pages}",
            data=[TeacherSearchResult(**t) for t in result["teachers"]],
            total=result["total"],
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al buscar docentes: {str(e)}"
        )