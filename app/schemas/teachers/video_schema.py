from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional, List
from datetime import datetime

class VideoValidationRequest(BaseModel):
    """
    Esquema para la solicitud de validación de un video de YouTube.
    
    Este modelo define la estructura de datos que debe enviar el frontend
    cuando un docente quiere validar su video de presentación.
    
    Attributes:
        url_or_id (str): URL completa de YouTube o ID del video.
                         Ejemplos:
                         - "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                         - "https://youtu.be/dQw4w9WgXcQ"
                         - "dQw4w9WgXcQ" (ID directo)
    
    Example:
        {
            "url_or_id": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }
    """
    url_or_id: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url_or_id": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            }
        }
    )


class VideoMetadata(BaseModel):
    """
    Esquema para los metadatos de un video de YouTube validado.
    
    Este modelo contiene toda la información necesaria para mostrar
    el video en la interfaz de usuario, incluyendo el reproductor
    embebido y metadatos para la presentación.
    
    Attributes:
        video_id (str): ID único del video de YouTube (11 caracteres)
        title (str): Título del video
        thumbnails (Dict[str, Any]): Diferentes tamaños de miniaturas del video
        duration_seconds (int): Duración del video en segundos
        embed_url (str): URL para embebido del video (iframe)
        privacy_status (str): Estado de privacidad ("public", "unlisted", "private")
        embeddable (bool): Indica si el video puede ser embebido
        url (str): URL completa del video en YouTube
    
    Note:
        Los thumbnails contienen diferentes resoluciones:
        - default: 120x90
        - medium: 320x180
        - high: 480x360
        - standard: 640x480
        - maxres: 1280x720 (si está disponible)
    
    Example:
        {
            "video_id": "dQw4w9WgXcQ",
            "title": "Presentación del Profesor Juan Pérez",
            "thumbnails": {
                "default": {"url": "...", "width": 120, "height": 90},
                "medium": {"url": "...", "width": 320, "height": 180}
            },
            "duration_seconds": 45,
            "embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "privacy_status": "public",
            "embeddable": True,
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }
    """
    video_id: str
    title: str
    thumbnails: Dict[str, Any]
    duration_seconds: int
    embed_url: str
    privacy_status: str
    embeddable: bool
    url: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "video_id": "dQw4w9WgXcQ",
                "title": "Presentación del Profesor Juan Pérez",
                "thumbnails": {
                    "default": {
                        "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg",
                        "width": 120,
                        "height": 90
                    },
                    "medium": {
                        "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
                        "width": 320,
                        "height": 180
                    }
                },
                "duration_seconds": 45,
                "embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                "privacy_status": "public",
                "embeddable": True,
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            }
        }
    )


class VideoValidationResponse(BaseModel):
    """
    Esquema para la respuesta de validación de un video de YouTube.
    
    Este modelo define la estructura de respuesta que recibe el frontend
    después de validar un video, indicando si la validación fue exitosa
    y proporcionando los metadatos del video o un mensaje de error.
    
    Attributes:
        success (bool): Indica si la validación fue exitosa
        message (str): Mensaje descriptivo del resultado de la validación
        data (Optional[VideoMetadata]): Metadatos del video si la validación fue exitosa,
                                       null si hubo un error
    
    Note:
        - Si success = True: data contiene los metadatos del video validado
        - Si success = False: data es null y message contiene el motivo del error
        
    Example de respuesta exitosa:
        {
            "success": True,
            "message": "Video validado exitosamente",
            "data": {
                "video_id": "dQw4w9WgXcQ",
                "title": "Presentación del Profesor Juan Pérez",
                "duration_seconds": 45,
                ...
            }
        }
        
    Example de respuesta de error:
        {
            "success": False,
            "message": "El título del video debe contener tu nombre completo",
            "data": null
        }
    """
    success: bool
    message: str
    data: Optional[VideoMetadata] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Validación exitosa",
                    "value": {
                        "success": True,
                        "message": "Video validado exitosamente",
                        "data": {
                            "video_id": "dQw4w9WgXcQ",
                            "title": "Presentación del Profesor Juan Pérez",
                            "thumbnails": {},
                            "duration_seconds": 45,
                            "embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                            "privacy_status": "public",
                            "embeddable": True,
                            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                        }
                    }
                },
                {
                    "summary": "Error de validación",
                    "value": {
                        "success": False,
                        "message": "El título del video debe contener tu nombre completo",
                        "data": None
                    }
                }
            ]
        }
    )


class VideoSaveRequest(BaseModel):
    """
    Esquema para guardar un video de YouTube validado en la base de datos.
    
    Este modelo se utiliza después de que un video ha sido validado exitosamente
    para persistirlo en la base de datos del usuario.
    
    Attributes:
        url_or_id (str): URL completa de YouTube o ID del video a guardar
        
    Note:
        El video debe haber sido validado previamente antes de intentar guardarlo.
        La validación se realiza automáticamente durante el proceso de guardado.
    
    Example:
        {
            "url_or_id": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }
    """
    url_or_id: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url_or_id": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            }
        }
    )


class VideoResponse(BaseModel):
    """
    Esquema para la respuesta de un video guardado en la base de datos.
    
    Este modelo representa la información de un video tal como se almacena
    y se devuelve al consultar los videos del usuario.
    
    Attributes:
        id (int): ID único del video en la base de datos
        youtube_video_id (str): ID del video de YouTube
        title (str): Título del video
        thumbnail_url (Optional[str]): URL de la miniatura del video
        duration_seconds (int): Duración del video en segundos
        embed_url (str): URL para embebido del video
        privacy_status (str): Estado de privacidad del video
        embeddable (bool): Si el video puede ser embebido
        original_url (str): URL original proporcionada por el usuario
        created_at (datetime): Fecha y hora de creación
        updated_at (datetime): Fecha y hora de última actualización
    
    Example:
        {
            "id": 1,
            "youtube_video_id": "dQw4w9WgXcQ",
            "title": "Presentación del Profesor Juan Pérez",
            "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
            "duration_seconds": 45,
            "embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "privacy_status": "public",
            "embeddable": true,
            "original_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    """
    id: int
    youtube_video_id: str
    title: str
    thumbnail_url: Optional[str] = None
    duration_seconds: int
    embed_url: str
    privacy_status: str
    embeddable: bool
    original_url: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,  # Para convertir desde objetos SQLAlchemy
        json_schema_extra={
            "example": {
                "id": 1,
                "youtube_video_id": "dQw4w9WgXcQ",
                "title": "Presentación del Profesor Juan Pérez",
                "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
                "duration_seconds": 45,
                "embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                "privacy_status": "public",
                "embeddable": True,
                "original_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class VideoSaveResponse(BaseModel):
    """
    Esquema para la respuesta al guardar un video de YouTube.
    
    Este modelo define la estructura de respuesta que recibe el frontend
    después de guardar un video en la base de datos.
    
    Attributes:
        success (bool): Indica si el guardado fue exitoso
        message (str): Mensaje descriptivo del resultado
        data (Optional[VideoResponse]): Datos del video guardado si fue exitoso
        
    Example de respuesta exitosa:
        {
            "success": true,
            "message": "Video guardado exitosamente",
            "data": {
                "id": 1,
                "youtube_video_id": "dQw4w9WgXcQ",
                "title": "Presentación del Profesor Juan Pérez",
                ...
            }
        }
        
    Example de respuesta de error:
        {
            "success": false,
            "message": "El video ya existe en tu cuenta",
            "data": null
        }
    """
    success: bool
    message: str
    data: Optional[VideoResponse] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Guardado exitoso",
                    "value": {
                        "success": True,
                        "message": "Video guardado exitosamente",
                        "data": {
                            "id": 1,
                            "youtube_video_id": "dQw4w9WgXcQ",
                            "title": "Presentación del Profesor Juan Pérez",
                            "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
                            "duration_seconds": 45,
                            "embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                            "privacy_status": "public",
                            "embeddable": True,
                            "original_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z"
                        }
                    }
                },
                {
                    "summary": "Error al guardar",
                    "value": {
                        "success": False,
                        "message": "El video ya existe en tu cuenta",
                        "data": None
                    }
                }
            ]
        }
    )


class VideoUpdateRequest(BaseModel):
    """
    Esquema para actualizar un video de YouTube existente.
    
    Este modelo se utiliza cuando un usuario quiere actualizar su video
    de presentación por uno nuevo, manteniendo la misma funcionalidad
    de validación pero actualizando los datos existentes.
    
    Attributes:
        url_or_id (str): URL completa de YouTube o ID del nuevo video
        
    Note:
        El nuevo video debe pasar todas las validaciones (título, duración,
        restricciones, etc.) antes de ser actualizado.
    
    Example:
        {
            "url_or_id": "https://www.youtube.com/watch?v=nuevoVideoID"
        }
    """
    url_or_id: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url_or_id": "https://www.youtube.com/watch?v=nuevoVideoID"
            }
        }
    )


class VideoUpdateResponse(BaseModel):
    """
    Esquema para la respuesta al actualizar un video de YouTube.
    
    Este modelo define la estructura de respuesta que recibe el frontend
    después de actualizar un video existente.
    
    Attributes:
        success (bool): Indica si la actualización fue exitosa
        message (str): Mensaje descriptivo del resultado
        data (Optional[VideoResponse]): Datos del video actualizado si fue exitoso
        
    Example de respuesta exitosa:
        {
            "success": true,
            "message": "Video actualizado exitosamente",
            "data": {
                "id": 1,
                "youtube_video_id": "nuevoVideoID",
                "title": "Nueva Presentación del Profesor Juan Pérez",
                ...
            }
        }
        
    Example de respuesta de error:
        {
            "success": false,
            "message": "El título del nuevo video debe contener tu nombre completo",
            "data": null
        }
    """
    success: bool
    message: str
    data: Optional[VideoResponse] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Actualización exitosa",
                    "value": {
                        "success": True,
                        "message": "Video actualizado exitosamente",
                        "data": {
                            "id": 1,
                            "youtube_video_id": "nuevoVideoID",
                            "title": "Nueva Presentación del Profesor Juan Pérez",
                            "thumbnail_url": "https://i.ytimg.com/vi/nuevoVideoID/mqdefault.jpg",
                            "duration_seconds": 50,
                            "embed_url": "https://www.youtube.com/embed/nuevoVideoID",
                            "privacy_status": "public",
                            "embeddable": True,
                            "original_url": "https://www.youtube.com/watch?v=nuevoVideoID",
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T11:45:00Z"
                        }
                    }
                },
                {
                    "summary": "Error de validación",
                    "value": {
                        "success": False,
                        "message": "El título del nuevo video debe contener tu nombre completo",
                        "data": None
                    }
                }
            ]
        }
    )


class VideoListResponse(BaseModel):
    """
    Esquema para la respuesta al listar videos del usuario.
    
    Este modelo define la estructura de respuesta para obtener todos
    los videos guardados por un usuario.
    
    Attributes:
        success (bool): Indica si la consulta fue exitosa
        message (str): Mensaje descriptivo del resultado
        data (List[VideoResponse]): Lista de videos del usuario
        total (int): Número total de videos
        
    Example:
        {
            "success": true,
            "message": "Videos obtenidos exitosamente",
            "data": [
                {
                    "id": 1,
                    "youtube_video_id": "dQw4w9WgXcQ",
                    "title": "Presentación del Profesor Juan Pérez",
                    ...
                }
            ],
            "total": 1
        }
    """
    success: bool
    message: str
    data: List[VideoResponse]
    total: int
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Videos obtenidos exitosamente",
                "data": [
                    {
                        "id": 1,
                        "youtube_video_id": "dQw4w9WgXcQ",
                        "title": "Presentación del Profesor Juan Pérez",
                        "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
                        "duration_seconds": 45,
                        "embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                        "privacy_status": "public",
                        "embeddable": True,
                        "original_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }
    )


