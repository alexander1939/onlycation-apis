from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.apis.deps import get_db, auth_required
from app.schemas.teachers.video_schema import (
    VideoValidationRequest,
    VideoValidationResponse,
    VideoSaveRequest,
    VideoSaveResponse,
    VideoUpdateRequest,
    VideoUpdateResponse,
    VideoListResponse,
    VideoResponse,
)
from app.services.externals.youtube_service import (
    validate_youtube_video_for_teacher,
    save_validated_video,
    update_user_video,
    get_user_videos,
)
from app.models.teachers.video import Video
from sqlalchemy import select

router = APIRouter()


@router.post("/validate/youtube", response_model=VideoValidationResponse)
async def validate_youtube_video(
    request: VideoValidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Valida un video de YouTube para un docente.
    
    Esta función verifica que el video cumpla con los requisitos de la aplicación:
    - El título debe contener el nombre completo del docente
    - La duración debe estar entre 30 segundos y 1 minuto
    - No debe tener restricciones de edad o región
    - Debe ser embebible y público o no listado
    
    Args:
        request (VideoValidationRequest): Contiene la URL o ID del video de YouTube
        db (AsyncSession): Sesión de base de datos
        current_user (dict): Usuario autenticado (obtenido del token JWT)
    
    Returns:
        VideoValidationResponse: Metadatos del video validado o mensaje de error
        
    Raises:
        HTTPException: Si el video no cumple con los requisitos o hay un error en la API de YouTube
        
    Example:
        POST /api/videos/validate/youtube
        {
            "url_or_id": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }
        
        Response exitoso:
        {
            "success": true,
            "message": "Video validado exitosamente",
            "data": {
                "video_id": "dQw4w9WgXcQ",
                "title": "Presentación del Profesor Juan Pérez",
                "thumbnails": {...},
                "duration_seconds": 45,
                "embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                "privacy_status": "public",
                "embeddable": true,
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            }
        }
        
        Response de error:
        {
            "success": false,
            "message": "El título del video debe contener tu nombre completo",
            "data": null
        }
    """
    try:
        # Validar el video usando el servicio de YouTube
        video_metadata = await validate_youtube_video_for_teacher(
            db=db,
            user_id=current_user["user_id"],
            url_or_id=request.url_or_id
        )
        
        return VideoValidationResponse(
            success=True,
            message="¡Excelente! Tu video cumple con todos los requisitos. Ahora puedes guardarlo en tu perfil.",
            data=video_metadata
        )
        
    except ValueError as e:
        # Error de validación (título, duración, restricciones, etc.)
        raise HTTPException(
            status_code=400,
            detail=f"❌ {str(e)}"
        )
    except Exception as e:
        # Error interno o de la API de YouTube
        raise HTTPException(
            status_code=500,
            detail=f"❌ Error interno al validar el video. Por favor, intenta nuevamente o contacta soporte si el problema persiste."
        )


@router.post("/create/my", response_model=VideoSaveResponse)
async def save_my_video(
    request: VideoSaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Guarda un video de YouTube validado en la base de datos del usuario.
    
    Este endpoint valida automáticamente el video antes de guardarlo,
    verificando que cumpla con todos los requisitos de la aplicación.
    
    Args:
        request (VideoSaveRequest): Contiene la URL o ID del video de YouTube
        db (AsyncSession): Sesión de base de datos
        current_user (dict): Usuario autenticado (obtenido del token JWT)
    
    Returns:
        VideoSaveResponse: Información del video guardado o mensaje de error
        
    Raises:
        HTTPException: Si el video no es válido, ya existe, o hay un error interno
        
    Example:
        POST /api/videos/create/my
        {
            "url_or_id": "https://www.youtube.com/watch?v=kKh2c_YZKDI"
        }
        
        Response exitoso:
        {
            "success": true,
            "message": "Video guardado exitosamente",
            "data": {
                "id": 1,
                "youtube_video_id": "kKh2c_YZKDI",
                "title": "Juan Pérez",
                "thumbnail_url": "https://i.ytimg.com/vi/kKh2c_YZKDI/mqdefault.jpg",
                "duration_seconds": 43,
                "embed_url": "https://www.youtube.com/embed/kKh2c_YZKDI",
                "privacy_status": "public",
                "embeddable": true,
                "original_url": "https://www.youtube.com/watch?v=kKh2c_YZKDI",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
        
        Response de error:
        {
            "success": false,
            "message": "Este video ya está guardado en tu cuenta",
            "data": null
        }
    """
    try:
        # Guardar el video (incluye validación automática)
        saved_video = await save_validated_video(
            db=db,
            user_id=current_user["user_id"],
            url_or_id=request.url_or_id
        )
        
        return VideoSaveResponse(
            success=True,
            message="¡Perfecto! Tu video de presentación ha sido guardado exitosamente. Los estudiantes podrán verlo en tu perfil.",
            data=VideoResponse.model_validate(saved_video)
        )
        
    except ValueError as e:
        # Error de validación o video duplicado
        raise HTTPException(
            status_code=400,
            detail=f"❌ {str(e)}"
        )
    except Exception as e:
        # Error interno
        raise HTTPException(
            status_code=500,
            detail=f"❌ Error interno al guardar el video. Por favor, intenta nuevamente o contacta soporte si el problema persiste."
        )


@router.get("/my", response_model=VideoListResponse)
async def get_my_videos(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Obtiene todos los videos guardados por el usuario autenticado.
    
    Este endpoint devuelve una lista de todos los videos de YouTube
    que el usuario ha guardado previamente en su cuenta, ordenados
    por fecha de creación (más recientes primero).
    
    Args:
        db (AsyncSession): Sesión de base de datos
        current_user (dict): Usuario autenticado (obtenido del token JWT)
    
    Returns:
        VideoListResponse: Lista de videos del usuario con metadatos completos
        
    Raises:
        HTTPException: Si hay un error al obtener los videos
        
    Example:
        GET /api/videos/my
        
        Response:
        {
            "success": true,
            "message": "Videos obtenidos exitosamente",
            "data": [
                {
                    "id": 1,
                    "youtube_video_id": "kKh2c_YZKDI",
                    "title": "Juan Pérez",
                    "thumbnail_url": "https://i.ytimg.com/vi/kKh2c_YZKDI/mqdefault.jpg",
                    "duration_seconds": 43,
                    "embed_url": "https://www.youtube.com/embed/kKh2c_YZKDI",
                    "privacy_status": "public",
                    "embeddable": true,
                    "original_url": "https://www.youtube.com/watch?v=kKh2c_YZKDI",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                }
            ],
            "total": 1
        }
    """
    try:
        # Obtener videos del usuario
        videos = await get_user_videos(
            db=db,
            user_id=current_user["user_id"]
        )
        
        # Convertir a schema de respuesta
        video_responses = [VideoResponse.model_validate(video) for video in videos]
        
        return VideoListResponse(
            success=True,
            message=f"Se encontraron {len(video_responses)} video(s) en tu perfil",
            data=video_responses,
            total=len(video_responses)
        )
        
    except Exception as e:
        # Error interno
        raise HTTPException(
            status_code=500,
            detail=f"❌ Error interno al obtener los videos. Por favor, intenta nuevamente o contacta soporte si el problema persiste."
        )


@router.get("/my-video-url/", dependencies=[Depends(auth_required)])
async def get_my_video_url(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Consultar solo la URL del video del docente autenticado.
    No requiere parámetros, se obtiene automáticamente del token.
    """
    user_id = current_user["user_id"]
    
    # Buscar el video del docente
    result = await db.execute(
        select(Video).where(Video.user_id == user_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="No tienes video de presentación registrado")
    
    return {
        "success": True,
        "message": "Video obtenido exitosamente",
        "data": {
            "embed_url": video.embed_url,
            "original_url": video.original_url
        }
    }


@router.put("/my", response_model=VideoUpdateResponse)
async def update_my_video(
    request: VideoUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Actualiza el video de presentación del usuario autenticado.
    
    Este endpoint permite a un usuario actualizar su video de presentación
    existente por uno nuevo, manteniendo todas las validaciones pero
    actualizando los datos en lugar de crear un nuevo registro.
    
    Args:
        request (VideoUpdateRequest): Contiene la URL o ID del nuevo video de YouTube
        db (AsyncSession): Sesión de base de datos
        current_user (dict): Usuario autenticado (obtenido del token JWT)
    
    Returns:
        VideoUpdateResponse: Información del video actualizado o mensaje de error
        
    Raises:
        HTTPException: Si el video no es válido, no existe, o hay un error interno
        
    Example:
        PUT /api/videos/my
        {
            "url_or_id": "https://www.youtube.com/watch?v=nuevoVideoID"
        }
        
        Response exitoso:
        {
            "success": true,
            "message": "Video actualizado exitosamente",
            "data": {
                "id": 1,
                "youtube_video_id": "nuevoVideoID",
                "title": "Nueva Presentación del Profesor Juan Pérez",
                "thumbnail_url": "https://i.ytimg.com/vi/nuevoVideoID/mqdefault.jpg",
                "duration_seconds": 50,
                "embed_url": "https://www.youtube.com/embed/nuevoVideoID",
                "privacy_status": "public",
                "embeddable": true,
                "original_url": "https://www.youtube.com/watch?v=nuevoVideoID",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T11:45:00Z"
            }
        }
        
        Response de error:
        {
            "success": false,
            "message": "No tienes un video de presentación para actualizar. Primero debes crear uno.",
            "data": null
        }
    """
    try:
        # Actualizar el video (incluye validación automática)
        updated_video = await update_user_video(
            db=db,
            user_id=current_user["user_id"],
            url_or_id=request.url_or_id
        )
        
        return VideoUpdateResponse(
            success=True,
            message="¡Genial! Tu video de presentación ha sido actualizado exitosamente. Los estudiantes verán tu nueva presentación.",
            data=VideoResponse.model_validate(updated_video)
        )
        
    except ValueError as e:
        # Error de validación o video no encontrado
        raise HTTPException(
            status_code=400,
            detail=f"❌ {str(e)}"
        )
    except Exception as e:
        # Error interno
        raise HTTPException(
            status_code=500,
            detail=f"❌ Error interno al actualizar el video. Por favor, intenta nuevamente o contacta soporte si el problema persiste."
        )