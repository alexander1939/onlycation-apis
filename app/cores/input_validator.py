"""
Validadores de entrada para prevenir inyección de código y XSS.
Úsalos en tus schemas de Pydantic para sanitizar automáticamente.
"""

from pydantic import field_validator
from app.cores.html_sanitizer import HTMLSanitizer
from typing import Any


def sanitize_string_field(value: Any) -> str:
    """
    Validador para campos de texto que elimina HTML peligroso.
    
    Uso en Pydantic:
        class MySchema(BaseModel):
            nombre: str
            
            _sanitize_nombre = field_validator('nombre')(sanitize_string_field)
    """
    if value is None:
        return ""
    
    if not isinstance(value, str):
        value = str(value)
    
    # Sanitizar eliminando TODO el HTML
    return HTMLSanitizer.sanitize_strict(value)


def sanitize_html_field(value: Any) -> str:
    """
    Validador para campos que SÍ permiten HTML básico (como descripciones).
    Solo permite tags seguros: <p>, <br>, <strong>, <em>, etc.
    
    Uso en Pydantic:
        class MySchema(BaseModel):
            descripcion: str
            
            _sanitize_desc = field_validator('descripcion')(sanitize_html_field)
    """
    if value is None:
        return ""
    
    if not isinstance(value, str):
        value = str(value)
    
    # Sanitizar permitiendo solo HTML básico seguro
    return HTMLSanitizer.sanitize(value)


def validate_no_sql_injection(value: Any) -> str:
    """
    Validador básico para detectar patrones sospechosos de SQL injection.
    NOTA: La protección principal es usar SQLAlchemy con parámetros, 
    pero esto agrega una capa extra.
    """
    if value is None:
        return ""
    
    if not isinstance(value, str):
        value = str(value)
    
    # Patrones sospechosos
    dangerous_patterns = [
        "';", "--", "/*", "*/", "xp_", "sp_", 
        "DROP ", "DELETE ", "INSERT ", "UPDATE ",
        "UNION ", "SELECT ", "EXEC ", "EXECUTE "
    ]
    
    value_upper = value.upper()
    for pattern in dangerous_patterns:
        if pattern in value_upper:
            raise ValueError(f"Entrada inválida: contiene patrón sospechoso '{pattern}'")
    
    return value


class InputValidator:
    """
    Clase helper para validar inputs manualmente en casos especiales.
    """
    
    @staticmethod
    def clean_string(text: str) -> str:
        """Limpia un string eliminando TODO el HTML."""
        return HTMLSanitizer.sanitize_strict(text) if text else ""
    
    @staticmethod
    def clean_html(text: str) -> str:
        """Limpia HTML dejando solo tags seguros."""
        return HTMLSanitizer.sanitize(text) if text else ""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validación básica de formato de email."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_length(text: str, min_len: int = 0, max_len: int = 1000) -> bool:
        """Valida que el texto esté dentro de longitud permitida."""
        if not text:
            return min_len == 0
        return min_len <= len(text) <= max_len
