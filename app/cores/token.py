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
REFRESH_TOKEN_EXPIRE_DAYS = 30


""" 
Genera un token JWT codificado con la información proporcionada en `data`.
    - `expires_delta` permite especificar tiempo de expiración personalizado.
    - Si no se pasa, se usa el tiempo por defecto (24 horas).
    - El token incluye la clave de expiración "exp" para validar su vigencia.
"""
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"type": "access", "exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"type": "refresh", "exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")




import random
import string

VERIFICATION_CODE_LENGTH = 6
VERIFICATION_CODE_EXPIRE_MINUTES = 15

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def generate_verification_code(length: int = VERIFICATION_CODE_LENGTH) -> str:
    """Genera un código de verificación aleatorio de dígitos numéricos"""
    return ''.join(random.choices(string.digits, k=length))

def get_verification_expiration() -> datetime:
    """Obtiene la fecha de expiración para un código de verificación"""
    return datetime.now(UTC) + timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES)