import base64
import secrets
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional
import os

class EncryptionService:
    """
    Servicio de encriptación AES-256 para mensajes de chat.
    
    Utiliza Fernet (AES-256 en modo CBC con HMAC) para encriptar/desencriptar
    mensajes de forma segura. Cada usuario tiene su propia clave de encriptación.
    """
    
    # Clave maestra para derivar claves de usuario (en producción debe estar en .env)
    MASTER_KEY = os.getenv("ENCRYPTION_MASTER_KEY", "onlycation_master_key_2024_secure")
    SALT_LENGTH = 32
    KEY_LENGTH = 32
    
    @staticmethod
    def _derive_key(user_id: int, master_key: str = None) -> bytes:
        """
        Deriva una clave de encriptación única para un usuario específico.
        
        Args:
            user_id: ID del usuario
            master_key: Clave maestra (opcional, usa la del sistema si no se proporciona)
            
        Returns:
            bytes: Clave derivada para el usuario
        """
        if master_key is None:
            master_key = EncryptionService.MASTER_KEY
        
        # Crear salt único basado en el user_id
        salt = hashlib.sha256(f"onlycation_salt_{user_id}".encode()).digest()
        
        # Derivar clave usando PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=EncryptionService.KEY_LENGTH,
            salt=salt,
            iterations=100000,  # 100k iteraciones para seguridad
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(f"{master_key}_{user_id}".encode()))
        return key
    
    @staticmethod
    def generate_user_key(user_id: int) -> str:
        """
        Genera una clave de encriptación para un usuario específico.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            str: Clave de encriptación en base64
        """
        key = EncryptionService._derive_key(user_id)
        return key.decode()
    
    @staticmethod
    def encrypt_message(content: str, user_id: int) -> str:
        """
        Encripta un mensaje usando la clave del usuario.
        
        Args:
            content: Contenido del mensaje a encriptar
            user_id: ID del usuario (para derivar la clave)
            
        Returns:
            str: Mensaje encriptado en base64
            
        Raises:
            ValueError: Si el contenido está vacío o el user_id es inválido
        """
        if not content or not content.strip():
            raise ValueError("El contenido del mensaje no puede estar vacío")
        
        if not user_id or user_id <= 0:
            raise ValueError("ID de usuario inválido")
        
        try:
            # Obtener clave del usuario
            key = EncryptionService._derive_key(user_id)
            
            # Crear instancia de Fernet
            fernet = Fernet(key)
            
            # Encriptar mensaje
            encrypted_bytes = fernet.encrypt(content.encode('utf-8'))
            
            # Convertir a base64 para almacenamiento
            encrypted_content = base64.urlsafe_b64encode(encrypted_bytes).decode()
            
            return encrypted_content
            
        except Exception as e:
            raise ValueError(f"Error al encriptar mensaje: {str(e)}")
    
    @staticmethod
    def decrypt_message(encrypted_content: str, user_id: int) -> str:
        """
        Desencripta un mensaje usando la clave del usuario.
        
        Args:
            encrypted_content: Contenido encriptado en base64
            user_id: ID del usuario (para derivar la clave)
            
        Returns:
            str: Mensaje desencriptado
            
        Raises:
            ValueError: Si el contenido encriptado es inválido o no se puede desencriptar
        """
        if not encrypted_content or not encrypted_content.strip():
            raise ValueError("El contenido encriptado no puede estar vacío")
        
        if not user_id or user_id <= 0:
            raise ValueError("ID de usuario inválido")
        
        try:
            # Obtener clave del usuario
            key = EncryptionService._derive_key(user_id)
            
            # Crear instancia de Fernet
            fernet = Fernet(key)
            
            # Decodificar de base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_content.encode())
            
            # Desencriptar mensaje
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            
            # Convertir a string
            decrypted_content = decrypted_bytes.decode('utf-8')
            
            return decrypted_content
            
        except Exception as e:
            raise ValueError(f"Error al desencriptar mensaje: {str(e)}")
    
    @staticmethod
    def verify_encryption(original_content: str, encrypted_content: str, user_id: int) -> bool:
        """
        Verifica que el contenido encriptado corresponde al contenido original.
        
        Args:
            original_content: Contenido original
            encrypted_content: Contenido encriptado
            user_id: ID del usuario
            
        Returns:
            bool: True si la verificación es exitosa
        """
        try:
            decrypted = EncryptionService.decrypt_message(encrypted_content, user_id)
            return decrypted == original_content
        except:
            return False
    
    @staticmethod
    def get_encryption_info(user_id: int) -> dict:
        """
        Obtiene información sobre la encriptación de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            dict: Información de encriptación
        """
        return {
            "user_id": user_id,
            "algorithm": "AES-256-CBC",
            "key_derivation": "PBKDF2-SHA256",
            "iterations": 100000,
            "salt_length": EncryptionService.SALT_LENGTH,
            "key_length": EncryptionService.KEY_LENGTH
        }
