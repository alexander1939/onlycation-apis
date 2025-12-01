from app.configs.settings import settings
from passlib.context import CryptContext
import hashlib, os
from cryptography.fernet import Fernet, InvalidToken

SECRET_KEY = settings.SECRET_KEY


""" 
Configura el contexto de hashing usando el algoritmo BCrypt.
Este contexto se usa internamente para hashear y verificar contraseñas.
"""
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__default_rounds=12  
)


""" 
Genera un hash seguro de la contraseña usando BCrypt.
Se utiliza al registrar o actualizar contraseñas antes de guardarlas en la base de datos.
"""
def get_password_hash(password: str) -> str:
    """Genera hash BCrypt seguro (soporta todos los caracteres)"""
    return pwd_context.hash(password)


""" 
Verifica si una contraseña en texto plano coincide con un hash previamente generado.
Se usa principalmente durante el login para validar credenciales del usuario.
"""

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica contraseña contra hash almacenado"""
    return pwd_context.verify(plain_password, hashed_password)




def get_fernet() -> Fernet:
    key = os.getenv("DOC_CIPHER_KEY")
    if not key:
        raise RuntimeError("Falta DOC_CIPHER_KEY en variables de entorno")
    return Fernet(key)

import re

def validate_rfc(rfc: str) -> bool:
    """
    Valida que el RFC cumpla con el formato correcto.
    
    Formatos aceptados:
    - Persona Física: 4 letras, 6 dígitos, 3 caracteres alfanuméricos (ej. ABCD123456XYZ)
    - Persona Moral: 3 letras, 6 dígitos, 3 caracteres alfanuméricos (ej. ABC123456XYZ)
    """
    rfc = rfc.strip().upper()
    
    # Expresión regular para validar RFC
    # ^                 # Inicio de la cadena
    # [A-Z&Ñ]{3,4}      # 3-4 letras (incluyendo Ñ) o &
    # \d{6}             # 6 dígitos
    # [A-Z0-9]{3}       # 3 caracteres alfanuméricos
    # $                 # Fin de la cadena
    pattern = r'^[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}$'
    
    # Verificar longitud (13 o 12 caracteres)
    if len(rfc) not in (12, 13):
        return False
    
    # Verificar patrón
    if not re.match(pattern, rfc):
        return False
    
    # Validar que los primeros caracteres sean letras (excepto el cuarto que puede ser un dígito para RFC de persona física con homoclave)
    if not rfc[0:3].isalpha():
        return False
    
    # Si es persona moral (12 caracteres), el cuarto carácter debe ser un dígito
    if len(rfc) == 12 and not rfc[3].isdigit():
        return False
    
    # Si es persona física (13 caracteres), el cuarto carácter debe ser una letra
    if len(rfc) == 13 and not rfc[3].isalpha():
        return False
    
    # Validar que los siguientes 6 caracteres sean dígitos (fecha)
    if len(rfc) == 12:
        fecha = rfc[3:9]  # Para persona moral
    else:
        fecha = rfc[4:10]  # Para persona física
    
    if not fecha.isdigit():
        return False
    
    # Validar fecha (aunque no es perfecto, es una validación básica)
    try:
        anio = int(fecha[0:2]) + (2000 if int(fecha[0:2]) < 50 else 1900)
        mes = int(fecha[2:4])
        dia = int(fecha[4:6])
        
        # Validar mes y día
        if mes < 1 or mes > 12:
            return False
        if dia < 1 or dia > 31:
            return False
        
        # Validar días por mes (sin considerar años bisiestos para simplificar)
        dias_por_mes = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if dia > dias_por_mes[mes - 1]:
            return False
            
    except (ValueError, IndexError):
        return False
    
    return True

def rfc_hash_plain(rfc: str) -> str:
    """Genera un hash seguro del RFC para búsquedas."""
    if not validate_rfc(rfc):
        raise ValueError("El RFC no tiene un formato válido")
    return hashlib.sha256(rfc.strip().upper().encode("utf-8")).hexdigest()

def encrypt_text(text: str) -> str:
    f = get_fernet()
    return f.encrypt(text.encode("utf-8")).decode("utf-8")  # str base64

def decrypt_text(token_b64: str) -> str:
    f = get_fernet()
    return f.decrypt(token_b64.encode("utf-8")).decode("utf-8")

def encrypt_bytes(data: bytes) -> bytes:
    f = get_fernet()
    return f.encrypt(data)

def decrypt_bytes(data: bytes) -> bytes:
    f = get_fernet()
    return f.decrypt(data)
