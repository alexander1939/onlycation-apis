from datetime import datetime, timedelta, UTC
from fastapi import HTTPException
from jose import JWTError, jwt
import os
import secrets
from typing import Optional


SECRET_KEY = os.getenv("SECRET_KEY", "UUr09BTA_9ZGHjl6Mz75FuUn-ftJli7yN2XMyt1myeA")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
RESET_TOKEN_EXPIRE_MINUTES = 30  # 30 minutos para el token de recuperación


""" 
Genera un token JWT codificado con la información proporcionada en `data`.
    - `expires_delta` permite especificar tiempo de expiración personalizado.
    - Si no se pasa, se usa el tiempo por defecto (24 horas).
    - El token incluye la clave de expiración "exp" para validar su vigencia.
"""
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt



def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_reset_token(email: str) -> str:
    """Crea un token JWT para recuperación de contraseña"""
    expire = datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": email, "exp": expire, "type": "reset"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_reset_token(token: str) -> Optional[str]:
    """Verifica un token de recuperación y devuelve el email si es válido"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "reset":
            return None
        email: str = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None

def generate_random_token(length: int = 32) -> str:
    """Genera un token aleatorio seguro para URLs"""
    return secrets.token_urlsafe(length)
