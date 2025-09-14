import re
import httpx
from typing import Optional, Dict, Any
import json
import unicodedata

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.configs.settings import settings
from app.models.teachers.video import Video
from app.models.users.user import User
from app.schemas.teachers.video_schema import VideoMetadata


YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"


def extract_video_id(url_or_id: str) -> str:
    """
    Extrae el ID del video de YouTube desde una URL o devuelve el ID directamente.
    
    Esta función maneja múltiples formatos de URL de YouTube:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - VIDEO_ID (ID directo)
    
    Args:
        url_or_id (str): URL completa de YouTube o ID del video
        
    Returns:
        str: ID del video de YouTube (11 caracteres)
        
    Raises:
        ValueError: Si la URL no es válida o no se puede extraer el ID
        
    Example:
        >>> extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
        >>> extract_video_id("dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
        >>> extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
    """
    # Si es solo un ID (11 caracteres alfanuméricos)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id
    
    # Patrones para diferentes formatos de URL de YouTube
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    raise ValueError("URL de YouTube no válida o no se pudo extraer el ID del video")


async def get_youtube_video_metadata(video_id: str) -> Dict[str, Any]:
    """
    Obtiene los metadatos de un video de YouTube usando la API v3.
    
    Esta función consulta la API de YouTube para obtener información detallada
    del video incluyendo título, duración, restricciones, estado de privacidad
    y capacidad de embebido.
    
    Args:
        video_id (str): ID del video de YouTube (11 caracteres)
        
    Returns:
        Dict[str, Any]: Metadatos del video de YouTube
        
    Raises:
        ValueError: Si hay un error en la API de YouTube o el video no existe
        Exception: Si hay un error de conexión o respuesta inesperada
        
    Note:
        Requiere que YOUTUBE_API_KEY esté configurado en las variables de entorno.
        La API consulta las siguientes partes del video:
        - snippet: título, descripción, thumbnails
        - contentDetails: duración
        - statistics: estadísticas básicas
        - status: estado de privacidad, restricciones
        - player: capacidad de embebido
        
    Example:
        >>> metadata = await get_youtube_video_metadata("dQw4w9WgXcQ")
        >>> print(metadata['snippet']['title'])
        'Rick Astley - Never Gonna Give You Up'
    """
    try:
        if not settings.YOUTUBE_API_KEY:
            raise ValueError("YOUTUBE_API_KEY no configurado en las variables de entorno")
        
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,contentDetails,statistics,status,player",
            "id": video_id,
            "key": settings.YOUTUBE_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                raise ValueError(f"Error en la API de YouTube: {response.status_code}")
            
            data = response.json()
            
            if not isinstance(data, dict):
                raise ValueError(f"Respuesta inesperada de YouTube API: {type(data)}")
            
            if not data.get("items"):
                raise ValueError("Video no encontrado o no accesible")
            
            video_data = data["items"][0]
            
            if not isinstance(video_data, dict):
                raise ValueError(f"Estructura de video inesperada: {type(video_data)}")
            
            # Verificar que tenga las claves necesarias
            required_keys = ["id", "snippet", "contentDetails", "status"]
            missing_keys = [key for key in required_keys if key not in video_data]
            if missing_keys:
                raise ValueError(f"Video no tiene las claves necesarias: {missing_keys}")
            
            return video_data
            
    except Exception as e:
        raise


def parse_duration(duration: str) -> int:
    """
    Convierte la duración ISO 8601 de YouTube a segundos.
    
    YouTube devuelve la duración en formato ISO 8601 (ej: "PT1M30S").
    Esta función parsea ese formato y lo convierte a segundos totales.
    
    Args:
        duration (str): Duración en formato ISO 8601 (ej: "PT1M30S")
        
    Returns:
        int: Duración en segundos
        
    Raises:
        ValueError: Si el formato de duración no es válido
        
    Example:
        >>> parse_duration("PT1M30S")
        90
        >>> parse_duration("PT30S")
        30
        >>> parse_duration("PT2M")
        120
    """
    # Patrón para ISO 8601: PT[horas]H[minutos]M[segundos]S
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration)
    
    if not match:
        raise ValueError(f"Formato de duración no válido: {duration}")
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds


def normalize_text(text: str) -> str:
    """
    Normaliza texto para comparaciones insensibles a acentos y mayúsculas.
    
    Esta función convierte el texto a minúsculas y remueve acentos
    para facilitar la comparación de nombres en títulos de videos.
    
    Args:
        text (str): Texto a normalizar
        
    Returns:
        str: Texto normalizado (minúsculas, sin acentos)
        
    Example:
        >>> normalize_text("José María Pérez")
        'jose maria perez'
        >>> normalize_text("ÁNGEL GARCÍA")
        'angel garcia'
    """
    # Mapeo de caracteres acentuados a sus equivalentes sin acento
    accent_map = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
        'ä': 'a', 'ë': 'e', 'ï': 'i', 'ö': 'o', 'ü': 'u',
        'ñ': 'n', 'ç': 'c'
    }
    
    text = text.lower()
    for accented, plain in accent_map.items():
        text = text.replace(accented, plain)
    
    return text


async def validate_youtube_video_for_teacher(
    db: AsyncSession, 
    user_id: int, 
    url_or_id: str
) -> VideoMetadata:
    """
    VALIDACIÓN COMPLETA - Valida todos los requisitos del video:
    - Título debe contener nombre completo del docente
    - Duración entre 30-60 segundos
    - Sin restricciones de edad o región
    - Debe ser embebible y público/no listado
    """
    try:
        # 1. Extraer ID del video
        video_id = extract_video_id(url_or_id)
        
        # 2. Obtener metadatos desde YouTube
        video_data = await get_youtube_video_metadata(video_id)
        
        # 3. Obtener datos del usuario
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Usuario no encontrado")
        
        # 4. Validar el título
        video_title = video_data["snippet"]["title"]
        user_full_name = f"{user.first_name} {user.last_name}"
        
        # Normalizar texto para comparación
        normalized_title = normalize_text(video_title)
        normalized_name = normalize_text(user_full_name)
        
        if normalized_name not in normalized_title:
            raise ValueError(
                f"El título del video debe contener tu nombre completo '{user_full_name}'. "
                f"Título actual: '{video_title}'. "
                f"Por favor, sube un video donde el título incluya tu nombre completo."
            )
        
        # 5. Validar duración (30-60 segundos)
        duration_iso = video_data["contentDetails"]["duration"]
        duration_seconds = parse_duration(duration_iso)
        
        if not (30 <= duration_seconds <= 60):
            raise ValueError(
                f"La duración del video debe estar entre 30 y 60 segundos. "
                f"Duración actual: {duration_seconds} segundos. "
                f"Por favor, sube un video de presentación más corto o más largo."
            )
        
        # 6. Validar restricciones de edad
        if video_data.get("status", {}).get("ytAgeRestricted", False):
            raise ValueError("El video no puede tener restricciones de edad. Por favor, sube un video sin restricciones de edad para que todos los estudiantes puedan verlo.")
        
        # 7. Validar restricciones de región
        if video_data.get("status", {}).get("regionRestriction"):
            raise ValueError("El video no puede tener restricciones de región. Por favor, sube un video que sea accesible desde cualquier ubicación.")
        
        # 8. Validar que sea embebible
        if not video_data.get("status", {}).get("embeddable", True):
            raise ValueError("El video debe ser embebible. Por favor, sube un video que permita ser reproducido en nuestra plataforma.")
        
        # 9. Validar estado de privacidad
        privacy_status = video_data["status"]["privacyStatus"]
        if privacy_status not in ["public", "unlisted"]:
            raise ValueError(
                f"El video debe ser público o no listado. Estado actual: {privacy_status}. "
                f"Por favor, cambia la configuración de privacidad de tu video en YouTube."
            )
        
        # 10. Construir respuesta
        metadata = VideoMetadata(
            video_id=video_id,
            title=video_title,
            thumbnails=video_data["snippet"]["thumbnails"],
            duration_seconds=duration_seconds,
            embed_url=f"https://www.youtube.com/embed/{video_id}",
            privacy_status=video_data["status"]["privacyStatus"],
            embeddable=True,
            url=f"https://www.youtube.com/watch?v={video_id}"
        )
        
        return metadata
        
    except Exception as e:
        raise ValueError(f"Error al validar el video: {str(e)}")


async def save_validated_video(db: AsyncSession, user_id: int, url_or_id: str) -> Video:
    """
    Guarda un video de YouTube validado en la base de datos.
    
    Esta función valida el video y luego lo guarda en la base de datos
    con todos sus metadatos para el usuario especificado.
    
    Args:
        db (AsyncSession): Sesión de base de datos
        user_id (int): ID del usuario (debe ser docente)
        url_or_id (str): URL de YouTube o ID del video
        
    Returns:
        Video: Objeto del video guardado con todos sus datos
        
    Raises:
        ValueError: Si el video no es válido o ya existe
        HTTPException: Si hay problemas con la API de YouTube
        
    Example:
        >>> video = await save_validated_video(db, 1, "https://youtu.be/dQw4w9WgXcQ")
        >>> print(video.title)
        'Presentación del Profesor Juan Pérez'
    """
    try:
        # Extraer ID del video
        video_id = extract_video_id(url_or_id)
        
        # Verificar si el usuario ya tiene un video (restricción UNIQUE por usuario)
        existing_video_query = select(Video).where(Video.user_id == user_id)
        result = await db.execute(existing_video_query)
        existing_video = result.scalar_one_or_none()
        
        if existing_video:
            raise ValueError("Ya tienes un video de presentación. Si quieres cambiarlo, usa la opción de actualizar video en lugar de crear uno nuevo.")
        
        # Validar el video (esto incluye todas las reglas de negocio)
        metadata = await validate_youtube_video_for_teacher(db, user_id, url_or_id)
        
        # Crear nuevo registro en la base de datos
        new_video = Video(
            user_id=user_id,
            youtube_video_id=video_id,
            title=metadata.title,
            thumbnail_url=metadata.thumbnails.get("medium", {}).get("url"),
            duration_seconds=metadata.duration_seconds,
            embed_url=metadata.embed_url,
            privacy_status=metadata.privacy_status,
            embeddable=metadata.embeddable,
            original_url=url_or_id
        )
        
        db.add(new_video)
        await db.commit()
        await db.refresh(new_video)
        
        return new_video
        
    except ValueError as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise ValueError(f"Error al guardar el video: {str(e)}")


async def get_user_videos(db: AsyncSession, user_id: int) -> list[Video]:
    """
    Obtiene todos los videos guardados por un usuario.
    
    Esta función recupera todos los videos de YouTube que un usuario
    ha guardado previamente en su cuenta, ordenados por fecha de creación.
    
    Args:
        db (AsyncSession): Sesión de base de datos
        user_id (int): ID del usuario
        
    Returns:
        list[Video]: Lista de videos del usuario ordenados por fecha de creación (más recientes primero)
        
    Example:
        >>> videos = await get_user_videos(db, 1)
        >>> for video in videos:
        ...     print(f"{video.title} - {video.duration_seconds}s")
        'Presentación del Profesor Juan Pérez - 45s'
    """
    try:
        query = select(Video).where(Video.user_id == user_id).order_by(Video.created_at.desc())
        result = await db.execute(query)
        videos = result.scalars().all()
        
        return list(videos)
        
    except Exception as e:
        raise ValueError(f"Error al obtener los videos: {str(e)}")


async def update_user_video(db: AsyncSession, user_id: int, url_or_id: str) -> Video:
    """
    Actualiza el video de presentación del usuario por uno nuevo.
    
    Esta función permite a un usuario actualizar su video de presentación
    existente por uno nuevo, manteniendo todas las validaciones pero
    actualizando los datos en lugar de crear un nuevo registro.
    
    Args:
        db (AsyncSession): Sesión de base de datos
        user_id (int): ID del usuario
        url_or_id (str): URL o ID del nuevo video de YouTube
        
    Returns:
        Video: Video actualizado con los nuevos metadatos
        
    Raises:
        ValueError: Si hay problemas durante la validación o actualización
        
    Example:
        >>> updated_video = await update_user_video(db, 1, "https://youtube.com/watch?v=nuevoID")
        >>> print(f"Video actualizado: {updated_video.title}")
        'Video actualizado: Nueva Presentación del Profesor Juan Pérez'
    """
    try:
        # 1. Buscar video existente del usuario
        query = select(Video).where(Video.user_id == user_id)
        result = await db.execute(query)
        existing_video = result.scalar_one_or_none()
        
        if not existing_video:
            raise ValueError("No tienes un video de presentación para actualizar. Primero debes crear un video usando la opción de crear video.")
        
        # 2. Validar el nuevo video (misma lógica que en validate_youtube_video_for_teacher)
        video_metadata = await validate_youtube_video_for_teacher(db, user_id, url_or_id)
        
        # 3. Extraer ID del nuevo video
        new_video_id = extract_video_id(url_or_id)
        
        # 4. Actualizar los campos del video existente
        existing_video.youtube_video_id = new_video_id
        existing_video.title = video_metadata.title
        existing_video.thumbnail_url = video_metadata.thumbnails.get("medium", {}).get("url")
        existing_video.duration_seconds = video_metadata.duration_seconds
        existing_video.embed_url = video_metadata.embed_url
        existing_video.privacy_status = video_metadata.privacy_status
        existing_video.embeddable = video_metadata.embeddable
        existing_video.original_url = url_or_id
        # updated_at se actualiza automáticamente por SQLAlchemy
        
        # 5. Guardar cambios en la base de datos
        await db.commit()
        await db.refresh(existing_video)
        
        return existing_video
        
    except ValueError as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise ValueError(f"Error al actualizar el video: {str(e)}")


