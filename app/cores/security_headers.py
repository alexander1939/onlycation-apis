from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware que agrega headers de seguridad a todas las respuestas.
    
    Protege contra:
    - XSS (Cross-Site Scripting)
    - Clickjacking
    - MIME type sniffing
    - Información de versión del servidor
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Prevenir MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Protección contra clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Política de referrer (no enviar información sensible en URLs)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Política de permisos del navegador
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # XSS Protection (legacy, pero algunos navegadores antiguos lo usan)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy (CSP) - Configuración básica
        # Ajusta según tus necesidades (especialmente si usas CDNs)
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",  # Ajustar según necesidades
            "style-src 'self' 'unsafe-inline'",   # Ajustar según necesidades
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # Strict Transport Security (HSTS) - Solo para HTTPS
        # Descomentar cuando uses HTTPS en producción
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Ocultar información del servidor
        response.headers["Server"] = "OnlyCation"
        
        return response
