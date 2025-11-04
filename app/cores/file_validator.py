import magic
import uuid
import os
from fastapi import UploadFile, HTTPException
from typing import List, Optional
from pathlib import Path


class FileValidator:
    """Validador de archivos subidos con verificación de MIME, extensión y tamaño."""
    
    # Configuración de tipos permitidos
    ALLOWED_MIME_TYPES = {
        "pdf": ["application/pdf"],
        "image": ["image/jpeg", "image/jpg", "image/png", "image/webp"],
        "document": ["application/pdf", "application/msword", 
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
        "video": ["video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo"],
    }
    
    ALLOWED_EXTENSIONS = {
        "pdf": [".pdf"],
        "image": [".jpg", ".jpeg", ".png", ".webp"],
        "document": [".pdf", ".doc", ".docx"],
        "video": [".mp4", ".mpeg", ".mov", ".avi"],
    }
    
    # Tamaños máximos en bytes
    MAX_FILE_SIZES = {
        "pdf": 10 * 1024 * 1024,      # 10 MB
        "image": 5 * 1024 * 1024,      # 5 MB
        "document": 10 * 1024 * 1024,  # 10 MB
        "video": 100 * 1024 * 1024,    # 100 MB
    }
    
    @staticmethod
    async def validate_file(
        file: UploadFile,
        file_type: str = "document",
        max_size: Optional[int] = None
    ) -> dict:
        """
        Valida un archivo subido.
        
        Args:
            file: Archivo subido de FastAPI
            file_type: Tipo esperado (pdf, image, document, video)
            max_size: Tamaño máximo en bytes (opcional, usa default si no se especifica)
            
        Returns:
            dict con información del archivo validado
            
        Raises:
            HTTPException si la validación falla
        """
        if not file:
            raise HTTPException(status_code=400, detail="No se proporcionó ningún archivo")
        
        # Validar extensión
        file_ext = Path(file.filename).suffix.lower()
        allowed_extensions = FileValidator.ALLOWED_EXTENSIONS.get(file_type, [])
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Extensión no permitida. Extensiones válidas: {', '.join(allowed_extensions)}"
            )
        
        # Leer contenido del archivo
        content = await file.read()
        await file.seek(0)  # Reset para uso posterior
        
        # Validar tamaño
        file_size = len(content)
        max_allowed = max_size or FileValidator.MAX_FILE_SIZES.get(file_type, 10 * 1024 * 1024)
        
        if file_size > max_allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo demasiado grande. Tamaño máximo: {max_allowed / (1024*1024):.1f} MB"
            )
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="El archivo está vacío")
        
        # Validar MIME type usando python-magic
        try:
            mime = magic.from_buffer(content, mime=True)
            allowed_mimes = FileValidator.ALLOWED_MIME_TYPES.get(file_type, [])
            
            if mime not in allowed_mimes:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de archivo no permitido. MIME detectado: {mime}. Permitidos: {', '.join(allowed_mimes)}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error al validar tipo de archivo: {str(e)}"
            )
        
        # Generar nombre único con UUID
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        return {
            "original_filename": file.filename,
            "unique_filename": unique_filename,
            "file_size": file_size,
            "mime_type": mime,
            "extension": file_ext,
            "validated": True
        }
    
    @staticmethod
    async def save_validated_file(
        file: UploadFile,
        destination_dir: str,
        file_type: str = "document",
        max_size: Optional[int] = None
    ) -> dict:
        """
        Valida y guarda un archivo con nombre UUID.
        
        Args:
            file: Archivo a guardar
            destination_dir: Directorio destino
            file_type: Tipo de archivo esperado
            max_size: Tamaño máximo opcional
            
        Returns:
            dict con información del archivo guardado (path, metadata)
        """
        # Validar archivo
        validation_result = await FileValidator.validate_file(file, file_type, max_size)
        
        # Crear directorio si no existe
        os.makedirs(destination_dir, exist_ok=True)
        
        # Guardar archivo con nombre UUID
        file_path = os.path.join(destination_dir, validation_result["unique_filename"])
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        return {
            **validation_result,
            "file_path": file_path,
        }
    
    @staticmethod
    def get_safe_filename(original_filename: str) -> str:
        """Genera un nombre de archivo seguro usando UUID."""
        ext = Path(original_filename).suffix.lower()
        return f"{uuid.uuid4()}{ext}"
