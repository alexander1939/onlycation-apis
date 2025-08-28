import hashlib
import secrets
from datetime import datetime

def generate_secure_room_link(booking_id: int, teacher_id: int, user_id: int, start_time: datetime):
    """Genera un link seguro y único para la clase"""
    
    # Crear un hash único basado en booking_id, teacher_id, user_id y timestamp
    unique_data = f"{booking_id}-{teacher_id}-{user_id}-{int(start_time.timestamp())}"
    room_hash = hashlib.md5(unique_data.encode()).hexdigest()[:8]
    
    # Generar token adicional para mayor seguridad
    security_token = secrets.token_hex(4)
    
    # Crear room name más seguro: teacher_id-student_id-hash-token
    room_name = f"onlycation-{teacher_id}x{user_id}-{room_hash}-{security_token}"
    class_link = f"https://meet.jit.si/{room_name}"
    
    print(f"🔗 DEBUG: Room creado: {room_name}")
    print(f"🔗 DEBUG: Link de clase: {class_link}")
    
    return class_link, room_name
