from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse


def get_client_ip(request: Request) -> str:
    """
    Obtiene la IP del cliente desde el request.
    Considera proxies y headers de forwarding.
    """
    # Verificar headers de proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # IP directa del cliente
    if request.client:
        return request.client.host
    
    return "unknown"


# Configurar limiter global
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["100/minute"],  # Límite por defecto: 100 peticiones/minuto
    storage_uri="memory://",  # Usar memoria (para producción considerar Redis)
    headers_enabled=True,  # Incluir headers de rate limit en respuestas
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Handler personalizado para cuando se excede el límite de peticiones.
    Devuelve respuesta en formato JSON consistente con el resto de la API.
    """
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "message": "Demasiadas peticiones. Por favor, intenta más tarde.",
            "detail": f"Límite excedido: {exc.detail}",
        },
    )
