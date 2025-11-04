import bleach
from typing import List, Optional


class HTMLSanitizer:
    """Sanitizador de HTML para prevenir ataques XSS."""
    
    # Tags HTML permitidos por defecto (muy restrictivo)
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li',
        'blockquote', 'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
    ]
    
    # Atributos permitidos
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        '*': ['class']
    }
    
    # Protocolos permitidos para links
    ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']
    
    @staticmethod
    def sanitize(
        text: str,
        allowed_tags: Optional[List[str]] = None,
        allowed_attributes: Optional[dict] = None,
        strip: bool = True
    ) -> str:
        """
        Sanitiza HTML eliminando código malicioso.
        
        Args:
            text: Texto a sanitizar
            allowed_tags: Lista de tags permitidos (usa default si None)
            allowed_attributes: Dict de atributos permitidos por tag
            strip: Si True, elimina tags no permitidos; si False, los escapa
            
        Returns:
            Texto sanitizado
        """
        if not text:
            return ""
        
        tags = allowed_tags if allowed_tags is not None else HTMLSanitizer.ALLOWED_TAGS
        attrs = allowed_attributes if allowed_attributes is not None else HTMLSanitizer.ALLOWED_ATTRIBUTES
        
        # Sanitizar con bleach
        cleaned = bleach.clean(
            text,
            tags=tags,
            attributes=attrs,
            protocols=HTMLSanitizer.ALLOWED_PROTOCOLS,
            strip=strip
        )
        
        return cleaned
    
    @staticmethod
    def sanitize_strict(text: str) -> str:
        """
        Sanitización estricta: elimina TODOS los tags HTML.
        Útil para campos de texto plano donde no se permite HTML.
        
        Args:
            text: Texto a sanitizar
            
        Returns:
            Texto sin tags HTML
        """
        if not text:
            return ""
        
        return bleach.clean(text, tags=[], strip=True)
    
    @staticmethod
    def linkify(text: str, skip_pre: bool = True) -> str:
        """
        Convierte URLs en texto a enlaces HTML seguros.
        
        Args:
            text: Texto con URLs
            skip_pre: Si True, no linkifica dentro de tags <pre>
            
        Returns:
            Texto con URLs convertidas a enlaces
        """
        if not text:
            return ""
        
        return bleach.linkify(text, skip_tags=['pre'] if skip_pre else [])
    
    @staticmethod
    def sanitize_and_linkify(text: str) -> str:
        """
        Sanitiza HTML y convierte URLs en enlaces seguros.
        
        Args:
            text: Texto a procesar
            
        Returns:
            Texto sanitizado con URLs convertidas
        """
        if not text:
            return ""
        
        # Primero sanitizar
        cleaned = HTMLSanitizer.sanitize(text)
        
        # Luego linkificar
        return HTMLSanitizer.linkify(cleaned)
    
    @staticmethod
    def is_safe(text: str) -> bool:
        """
        Verifica si el texto contiene HTML potencialmente peligroso.
        
        Args:
            text: Texto a verificar
            
        Returns:
            True si el texto es seguro, False si contiene HTML peligroso
        """
        if not text:
            return True
        
        cleaned = HTMLSanitizer.sanitize_strict(text)
        
        # Si el texto cambia al sanitizarlo, contenía HTML
        return cleaned == text
