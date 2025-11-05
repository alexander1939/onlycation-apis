from fastapi import APIRouter, Depends, HTTPException
from app.services.teachers.teacher_agenda_service import (
    get_teacher_weekly_agenda, 
    get_public_teacher_weekly_agenda, 
    create_teacher_availability, 
    update_teacher_availability, 
    delete_teacher_availability,
    get_teacher_availability_list
)
from app.schemas.availability.availability_schema import (
    TeacherAgendaResponse, AvailabilitySummaryResponse
)
from app.apis.deps import auth_required, get_db, public_access
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/agenda/", dependencies=[Depends(auth_required)])
async def get_teacher_agenda(
    week: str = None,
    start_date: str = None,
    end_date: str = None,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Obtener la agenda del docente autenticado
    
    Parámetros:
    - week: Fecha de inicio de semana (formato YYYY-MM-DD) - retorna lunes a domingo
    - start_date: Fecha de inicio personalizada (formato YYYY-MM-DD)
    - end_date: Fecha de fin personalizada (formato YYYY-MM-DD)
    
    Si se proporciona start_date y end_date, se usa ese rango.
    Si solo se proporciona week, se retorna la semana completa (lunes a domingo).
    Si no se proporciona nada, se retorna la semana actual.
    """
    teacher_id = user_data.get("user_id")
    
    # Si se proporcionan fechas personalizadas, usar esas
    week_param = week
    if start_date and end_date:
        week_param = f"{start_date},{end_date}"
    
    result = await get_public_teacher_weekly_agenda(
        db=db,
        teacher_id=teacher_id,
        week_start_date=week_param
    )
    
    return {
        "success": True,
        "message": "Agenda obtenida exitosamente",
        "data": result
    }

@router.get("/docente/{teacher_id}/agenda/", dependencies=[Depends(public_access)])
async def get_public_teacher_agenda(
    teacher_id: int,
    week: str = None,
    start_date: str = None,
    end_date: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener la agenda pública de cualquier docente
    
    Parámetros:
    - week: Fecha de inicio de semana (formato YYYY-MM-DD) - retorna lunes a domingo
    - start_date: Fecha de inicio personalizada (formato YYYY-MM-DD)
    - end_date: Fecha de fin personalizada (formato YYYY-MM-DD)
    
    Si se proporciona start_date y end_date, se usa ese rango.
    Si solo se proporciona week, se retorna la semana completa (lunes a domingo).
    Si no se proporciona nada, se retorna la semana actual.
    """
    # Si se proporcionan fechas personalizadas, usar esas
    week_param = week
    if start_date and end_date:
        week_param = f"{start_date},{end_date}"
    
    result = await get_public_teacher_weekly_agenda(
        db=db,
        teacher_id=teacher_id,
        week_start_date=week_param
    )
    
    return {
        "success": True,
        "message": "Agenda pública del docente obtenida exitosamente",
        "data": result
    }

@router.get("/list/", dependencies=[Depends(auth_required)])
async def list_teacher_availabilities(
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Obtener lista de disponibilidades del docente
    Muestra día de la semana, hora de inicio y hora de fin
    """
    result = await get_teacher_availability_list(
        db=db,
        user_data=user_data
    )
    
    return {
        "success": True,
        "message": "Disponibilidades obtenidas exitosamente",
        "data": result
    }

@router.post("/create/", dependencies=[Depends(auth_required)])
async def create_availability(
    availability_data: dict,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Crear nueva disponibilidad para el docente autenticado
    """
    result = await create_teacher_availability(
        db=db,
        user_data=user_data,
        availability_data=availability_data
    )
    
    return {
        "success": True,
        "message": "Disponibilidad creada exitosamente",
        "data": result
    }

@router.put("/update/{availability_id}/", dependencies=[Depends(auth_required)])
async def update_availability(
    availability_id: int,
    availability_data: dict,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Actualizar disponibilidad del docente autenticado
    """
    result = await update_teacher_availability(
        db=db,
        user_data=user_data,
        availability_id=availability_id,
        availability_data=availability_data
    )
    
    return {
        "success": True,
        "message": "Disponibilidad actualizada exitosamente",
        "data": result
    }

@router.delete("/delete/{availability_id}/", dependencies=[Depends(auth_required)])
async def delete_availability(
    availability_id: int,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Eliminar disponibilidad del docente autenticado
    """
    await delete_teacher_availability(
        db=db,
        user_data=user_data,
        availability_id=availability_id
    )
    
    return {
        "success": True,
        "message": "Disponibilidad eliminada exitosamente"
    }
