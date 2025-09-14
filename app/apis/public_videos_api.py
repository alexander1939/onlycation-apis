from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.apis.deps import get_db, public_access
from app.models.teachers.video import Video
from app.models.users.user import User
from app.schemas.teachers.video_schema import VideoResponse

router = APIRouter()


@router.get("/teacher/{teacher_id}", response_model=VideoResponse)
async def get_teacher_video_public(
    teacher_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(public_access)
):
    """
    Obtiene el video de presentación de un profesor de forma pública (sin autenticación).
    
    Este endpoint permite a cualquier persona (registrada o no) ver el video de 
    presentación de un profesor específico para motivar su registro y contratación.
    
    Args:
        teacher_id (int): ID del profesor
        db (AsyncSession): Sesión de base de datos
        _ (None): Dependencia de acceso público (sin autenticación)
    
    Returns:
        VideoResponse: Datos del video del profesor con metadatos completos
        
    Raises:
        HTTPException: Si el profesor no existe o no tiene video
        
    Example:
        GET /api/public/videos/teacher/123
        
        Response:
        {
            "id": 1,
            "youtube_video_id": "kKh2c_YZKDI",
            "title": "Presentación - Juan Pérez",
            "thumbnail_url": "https://i.ytimg.com/vi/kKh2c_YZKDI/mqdefault.jpg",
            "duration_seconds": 43,
            "embed_url": "https://www.youtube.com/embed/kKh2c_YZKDI",
            "privacy_status": "public",
            "embeddable": true,
            "original_url": "https://www.youtube.com/watch?v=kKh2c_YZKDI",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    """
    try:
        # Verificar que el profesor existe
        user_query = select(User).where(User.id == teacher_id)
        user_result = await db.execute(user_query)
        teacher = user_result.scalar_one_or_none()
        
        if not teacher:
            raise HTTPException(
                status_code=404,
                detail="Profesor no encontrado"
            )
        
        # Obtener el video del profesor
        video_query = select(Video).where(Video.user_id == teacher_id)
        video_result = await db.execute(video_query)
        video = video_result.scalar_one_or_none()
        
        if not video:
            raise HTTPException(
                status_code=404,
                detail="Este profesor no tiene un video de presentación disponible"
            )
        
        # Convertir a schema de respuesta
        return VideoResponse.model_validate(video)
        
    except HTTPException:
        # Re-lanzar HTTPExceptions tal como están
        raise
    except Exception as e:
        # Error interno
        raise HTTPException(
            status_code=500,
            detail="Error interno al obtener el video del profesor"
        )


@router.get("/teachers/with-videos")
async def get_teachers_with_videos_public(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(public_access)
):
    """
    Obtiene una lista de todos los profesores que tienen videos de presentación disponibles.
    
    Este endpoint público permite ver qué profesores tienen videos de presentación
    para facilitar la navegación y descubrimiento de profesores.
    
    Args:
        db (AsyncSession): Sesión de base de datos
        _ (None): Dependencia de acceso público (sin autenticación)
    
    Returns:
        dict: Lista de profesores con sus videos básicos
        
    Example:
        GET /api/public/videos/teachers/with-videos
        
        Response:
        {
            "success": true,
            "message": "Profesores con videos obtenidos exitosamente",
            "data": [
                {
                    "teacher_id": 123,
                    "teacher_name": "Juan Pérez",
                    "video": {
                        "id": 1,
                        "youtube_video_id": "kKh2c_YZKDI",
                        "title": "Presentación - Juan Pérez",
                        "thumbnail_url": "https://i.ytimg.com/vi/kKh2c_YZKDI/mqdefault.jpg",
                        "duration_seconds": 43,
                        "embed_url": "https://www.youtube.com/embed/kKh2c_YZKDI"
                    }
                }
            ],
            "total": 1
        }
    """
    try:
        # Query para obtener profesores con videos usando JOIN
        query = select(User, Video).join(Video, User.id == Video.user_id)
        result = await db.execute(query)
        teachers_with_videos = result.all()
        
        # Formatear respuesta
        teachers_data = []
        for teacher, video in teachers_with_videos:
            teacher_data = {
                "teacher_id": teacher.id,
                "teacher_name": f"{teacher.first_name} {teacher.last_name}",
                "video": {
                    "id": video.id,
                    "youtube_video_id": video.youtube_video_id,
                    "title": video.title,
                    "thumbnail_url": video.thumbnail_url,
                    "duration_seconds": video.duration_seconds,
                    "embed_url": video.embed_url,
                    "privacy_status": video.privacy_status,
                    "embeddable": video.embeddable,
                    "created_at": video.created_at.isoformat() if video.created_at else None
                }
            }
            teachers_data.append(teacher_data)
        
        return {
            "success": True,
            "message": "Profesores con videos obtenidos exitosamente",
            "data": teachers_data,
            "total": len(teachers_data)
        }
        
    except Exception as e:
        # Error interno
        raise HTTPException(
            status_code=500,
            detail="Error interno al obtener la lista de profesores con videos"
        )
