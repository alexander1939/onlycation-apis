from datetime import datetime, timedelta, UTC
from jose import JWTError, jwt
import os

SECRET_KEY = os.getenv("SECRET_KEY", "clave_supersecreta")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 


""" 
Genera un token JWT codificado con la información proporcionada en `data`.
    - `expires_delta` permite especificar tiempo de expiración personalizado.
    - Si no se pasa, se usa el tiempo por defecto (24 horas).
    - El token incluye la clave de expiración "exp" para validar su vigencia.
"""
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
