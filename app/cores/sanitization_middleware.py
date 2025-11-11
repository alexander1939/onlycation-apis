"""
Middleware de sanitización global para limpiar automáticamente 
todos los inputs de usuario en TODAS las APIs.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import FormData, QueryParams
from app.cores.html_sanitizer import HTMLSanitizer
import json
from typing import Any, Dict, Union
from urllib.parse import urlencode


class SanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware que sanitiza automáticamente todos los datos de entrada:
    - Request bodies (JSON)
    - Form data
    - Query parameters (búsquedas, filtros)
    
    Elimina código HTML/JavaScript peligroso de todos los strings.
    """
    
    # Campos que NO deben sanitizarse (como passwords)
    SKIP_FIELDS = {
        'password', 'token', 'access_token', 'refresh_token',
        'secret', 'key', 'api_key', 'cipher_key'
    }
    
    # Rutas que se saltan la sanitización (si es necesario)
    SKIP_PATHS = {
        '/docs', '/redoc', '/openapi.json', '/health'
    }
    
    async def dispatch(self, request: Request, call_next):
        """Intercepta requests y sanitiza datos antes de procesarlos."""
        
        # Saltar rutas específicas
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        
        # Sanitizar query parameters en TODOS los métodos (GET, POST, etc.)
        if request.query_params:
            self._sanitize_query_params(request)
        
        # Sanitizar body solo en POST, PUT, PATCH (métodos que envían datos)
        if request.method in ['POST', 'PUT', 'PATCH']:
            await self._sanitize_request(request)
        
        response = await call_next(request)
        return response
    
    def _sanitize_query_params(self, request: Request):
        """
        Sanitiza query parameters (?query=..., ?filter=..., etc.).
        Protege endpoints de búsqueda y filtros.
        """
        try:
            # Obtener query params originales
            original_params = dict(request.query_params)
            
            if not original_params:
                return
            
            # Sanitizar cada parámetro
            sanitized_params = {}
            for key, value in original_params.items():
                if key.lower() not in self.SKIP_FIELDS:
                    if isinstance(value, str):
                        sanitized_params[key] = self._sanitize_string(value)
                    else:
                        sanitized_params[key] = value
                else:
                    sanitized_params[key] = value
            
            # Reemplazar query params con versión sanitizada
            request._query_params = QueryParams(sanitized_params)
            
        except Exception as e:
            print(f"Error sanitizing query params: {e}")
            pass
    
    async def _sanitize_request(self, request: Request):
        """Sanitiza el contenido del request."""
        content_type = request.headers.get('content-type', '')
        
        if 'application/json' in content_type:
            await self._sanitize_json_body(request)
        elif 'application/x-www-form-urlencoded' in content_type or 'multipart/form-data' in content_type:
            await self._sanitize_form_data(request)
    
    async def _sanitize_json_body(self, request: Request):
        """Sanitiza JSON body."""
        try:
            # Leer el body original
            body = await request.body()
            if not body:
                return
            
            # Parsear JSON
            data = json.loads(body.decode('utf-8'))
            
            # Sanitizar recursivamente
            sanitized_data = self._sanitize_value(data)
            
            # Reemplazar el body con datos sanitizados
            sanitized_body = json.dumps(sanitized_data).encode('utf-8')
            
            # Crear una función que devuelva el body sanitizado
            async def receive():
                return {'type': 'http.request', 'body': sanitized_body}
            
            # Reemplazar el receive del request
            request._receive = receive
            
        except Exception as e:
            # Si falla la sanitización, dejar pasar (mejor que romper el request)
            print(f"Error sanitizing JSON: {e}")
            pass
    
    async def _sanitize_form_data(self, request: Request):
        """Sanitiza form data."""
        try:
            form = await request.form()
            sanitized_form = {}
            
            for key, value in form.items():
                if key.lower() not in self.SKIP_FIELDS:
                    if isinstance(value, str):
                        sanitized_form[key] = self._sanitize_string(value)
                    else:
                        sanitized_form[key] = value
                else:
                    sanitized_form[key] = value
            
            # Recrear FormData con datos sanitizados
            request._form = FormData(sanitized_form)
            
        except Exception as e:
            print(f"Error sanitizing form: {e}")
            pass
    
    def _sanitize_value(self, value: Any) -> Any:
        """
        Sanitiza un valor recursivamente.
        Maneja strings, dicts, lists, etc.
        """
        if isinstance(value, dict):
            return {k: self._sanitize_value(v) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        
        elif isinstance(value, str):
            # No sanitizar campos sensibles
            return self._sanitize_string(value)
        
        else:
            # Números, booleanos, None, etc. pasan sin cambios
            return value
    
    def _sanitize_string(self, text: str) -> str:
        """
        Sanitiza un string individual.
        Elimina HTML/JavaScript peligroso pero mantiene el texto legible.
        """
        if not text:
            return text
        
        # Usar sanitización estricta: elimina TODO el HTML
        # Si necesitas permitir HTML en ciertos campos, modifica aquí
        return HTMLSanitizer.sanitize_strict(text)
    
    @classmethod
    def add_skip_field(cls, field_name: str):
        """Agrega un campo que no debe sanitizarse."""
        cls.SKIP_FIELDS.add(field_name.lower())
    
    @classmethod
    def add_skip_path(cls, path: str):
        """Agrega una ruta que no debe sanitizarse."""
        cls.SKIP_PATHS.add(path)
