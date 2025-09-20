# 🌩️ Guía de Pruebas con Thunder Client - Sistema de Chat OnlyCation

## 📋 Prerequisitos

1. **Instalar dependencias faltantes:**
```bash
pip install better-profanity>=0.7.0
```

2. **Iniciar el servidor:**
```bash
uvicorn app.main:app --reload
```

3. **Thunder Client configurado en VS Code**

## 🔐 Autenticación

### 1. Registrar Usuario Estudiante
```http
POST http://localhost:8000/api/auth/register/student/
Content-Type: application/json

{
    "first_name": "Juan",
    "last_name": "Pérez",
    "email": "juan.student@test.com",
    "password": "password123",
    "privacy_policy_accepted": true
}
```

### 2. Registrar Usuario Profesor
```http
POST http://localhost:8000/api/auth/register/teacher/
Content-Type: application/json

{
    "first_name": "María",
    "last_name": "García",
    "email": "maria.teacher@test.com",
    "password": "password123",
    "privacy_policy_accepted": true
}
```

### 3. Login Estudiante
```http
POST http://localhost:8000/api/auth/login/
Content-Type: application/json

{
    "email": "juan.student@test.com",
    "password": "password123"
}
```

**Respuesta esperada:**
```json
{
    "success": true,
    "message": "Login exitoso",
    "data": {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "token_type": "bearer",
        "email": "juan.student@test.com",
        "first_name": "Juan",
        "last_name": "Pérez"
    }
}
```

### 4. Login Profesor
```http
POST http://localhost:8000/api/auth/login/
Content-Type: application/json

{
    "email": "maria.teacher@test.com",
    "password": "password123"
}
```

## 💬 Pruebas del Sistema de Chat

### 5. Crear Chat (Solo Estudiantes)
```http
POST http://localhost:8000/api/chat/chats/create
Authorization: Bearer {student_access_token}
Content-Type: application/json

{
    "teacher_id": 2
}
```

**Respuesta esperada:**
```json
{
    "success": true,
    "message": "Chat creado exitosamente",
    "data": {
        "id": 1,
        "student_id": 1,
        "teacher_id": 2,
        "is_active": true,
        "is_blocked": false,
        "created_at": "2024-01-15T10:30:00Z"
    }
}
```

### 6. Obtener Mis Chats
```http
GET http://localhost:8000/api/chat/chats/my
Authorization: Bearer {access_token}
```

## 🛡️ Pruebas del Filtro de Contenido

### 7. Enviar Mensaje Apropiado
```http
POST http://localhost:8000/api/chat/messages/send
Authorization: Bearer {student_access_token}
Content-Type: application/json

{
    "chat_id": 1,
    "content": "Hola profesor, ¿cómo está? Necesito ayuda con matemáticas"
}
```

**Respuesta esperada: ✅ ÉXITO**
```json
{
    "success": true,
    "message": "Mensaje enviado exitosamente",
    "data": {
        "id": 1,
        "chat_id": 1,
        "sender_id": 1,
        "content": "Hola profesor, ¿cómo está? Necesito ayuda con matemáticas",
        "is_read": false,
        "is_encrypted": true,
        "created_at": "2024-01-15T10:35:00Z"
    }
}
```

### 8. Enviar Mensaje con Lenguaje Inapropiado
```http
POST http://localhost:8000/api/chat/messages/send
Authorization: Bearer {student_access_token}
Content-Type: application/json

{
    "chat_id": 1,
    "content": "Eres un idiota, no entiendes nada"
}
```

**Respuesta esperada: ❌ BLOQUEADO**
```json
{
    "detail": "❌ Mensaje bloqueado: El mensaje contiene lenguaje inapropiado, insultos o palabras ofensivas\n\n💡 Sugerencias: Por favor, mantén un lenguaje respetuoso y profesional, Evita usar insultos, amenazas o contenido inapropiado"
}
```

### 9. Enviar Mensaje con Amenaza
```http
POST http://localhost:8000/api/chat/messages/send
Authorization: Bearer {student_access_token}
Content-Type: application/json

{
    "chat_id": 1,
    "content": "Te voy a matar si no me ayudas"
}
```

**Respuesta esperada: ❌ BLOQUEADO**

### 10. Enviar Mensaje con Información Personal
```http
POST http://localhost:8000/api/chat/messages/send
Authorization: Bearer {student_access_token}
Content-Type: application/json

{
    "chat_id": 1,
    "content": "Mi número de teléfono es 123456789, llámame"
}
```

**Respuesta esperada: ❌ BLOQUEADO**

### 11. Enviar Mensaje con URL
```http
POST http://localhost:8000/api/chat/messages/send
Authorization: Bearer {student_access_token}
Content-Type: application/json

{
    "chat_id": 1,
    "content": "Visita mi página web: www.ejemplo.com"
}
```

**Respuesta esperada: ❌ BLOQUEADO**

### 12. Enviar Mensaje con Mayúsculas Excesivas
```http
POST http://localhost:8000/api/chat/messages/send
Authorization: Bearer {student_access_token}
Content-Type: application/json

{
    "chat_id": 1,
    "content": "ESTO ES SPAM!!! AYÚDAME AHORA!!!"
}
```

**Respuesta esperada: ❌ BLOQUEADO**

### 13. Mensaje Vacío
```http
POST http://localhost:8000/api/chat/messages/send
Authorization: Bearer {student_access_token}
Content-Type: application/json

{
    "chat_id": 1,
    "content": ""
}
```

**Respuesta esperada: ❌ BLOQUEADO**

## 📨 Pruebas de Gestión de Mensajes

### 14. Obtener Mensajes del Chat
```http
GET http://localhost:8000/api/chat/messages/1?limit=10&offset=0
Authorization: Bearer {access_token}
```

### 15. Marcar Mensajes como Leídos
```http
POST http://localhost:8000/api/chat/messages/mark-read
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "message_ids": [1, 2, 3]
}
```

### 16. Obtener Contador de No Leídos
```http
GET http://localhost:8000/api/chat/messages/1/unread-count
Authorization: Bearer {access_token}
```

### 17. Eliminar Mensaje (Soft Delete)
```http
DELETE http://localhost:8000/api/chat/messages/1
Authorization: Bearer {access_token}
```

## 🔒 Pruebas de Bloqueo de Chat

### 18. Bloquear Chat
```http
POST http://localhost:8000/api/chat/chats/1/block
Authorization: Bearer {access_token}
```

### 19. Desbloquear Chat
```http
POST http://localhost:8000/api/chat/chats/1/unblock
Authorization: Bearer {access_token}
```

### 20. Intentar Enviar Mensaje en Chat Bloqueado
```http
POST http://localhost:8000/api/chat/messages/send
Authorization: Bearer {student_access_token}
Content-Type: application/json

{
    "chat_id": 1,
    "content": "Mensaje en chat bloqueado"
}
```

**Respuesta esperada: ❌ ERROR**
```json
{
    "detail": "❌ Este chat está bloqueado"
}
```

## 🧪 Casos de Prueba Específicos del Filtro

### Contexto Educativo (Debería Pasar)
```json
{
    "chat_id": 1,
    "content": "Estoy estudiando para el examen de matemáticas, ¿puede explicar la tarea?"
}
```

### Falsos Positivos Educativos
```json
{
    "chat_id": 1,
    "content": "El profesor explicó sobre la reproducción sexual en biología"
}
```

### Palabras en Español
```json
{
    "chat_id": 1,
    "content": "Esto es una mierda de explicación"
}
```

### Combinación de Problemas
```json
{
    "chat_id": 1,
    "content": "Eres un IDIOTA!!! Mi teléfono es 987654321, visita www.spam.com"
}
```

## 🔍 Verificación de Encriptación

Los mensajes se almacenan encriptados en la base de datos. Para verificar:

1. **Envía un mensaje exitoso**
2. **Consulta la base de datos directamente:**
```sql
SELECT encrypted_content, is_encrypted FROM messages WHERE id = 1;
```
3. **Verifica que el contenido esté encriptado y no sea legible**

## 📊 Códigos de Respuesta Esperados

| Escenario | Código HTTP | Resultado |
|-----------|-------------|-----------|
| Mensaje apropiado | 200 | ✅ Enviado |
| Mensaje inapropiado | 400 | ❌ Bloqueado |
| Chat no encontrado | 400 | ❌ Error |
| Usuario no autorizado | 401 | ❌ No autorizado |
| Usuario no participante | 400 | ❌ Sin acceso |
| Chat bloqueado | 400 | ❌ Bloqueado |
| Servidor error | 500 | ❌ Error interno |

## 🐛 Problemas Comunes y Soluciones

### Error: "better-profanity not found"
```bash
pip install better-profanity>=0.7.0
```

### Error: "EncryptionService not found"
- Verificar que el servicio de encriptación esté implementado
- Revisar imports en message_service.py

### Error: "Token inválido"
- Verificar que el token esté en el header Authorization
- Formato: `Bearer {token}`
- Token debe ser válido y no expirado

### Error: "Chat no encontrado"
- Verificar que el chat_id exista
- Usuario debe ser participante del chat

## ✅ Checklist de Pruebas

- [ ] Registro de usuarios (estudiante y profesor)
- [ ] Login exitoso
- [ ] Creación de chat
- [ ] Mensaje apropiado enviado
- [ ] Mensaje inapropiado bloqueado
- [ ] Amenazas bloqueadas
- [ ] URLs bloqueadas
- [ ] Información personal bloqueada
- [ ] Mayúsculas excesivas bloqueadas
- [ ] Mensajes vacíos bloqueados
- [ ] Contexto educativo permitido
- [ ] Encriptación funcionando
- [ ] Marcar como leído
- [ ] Eliminar mensaje
- [ ] Bloquear/desbloquear chat
- [ ] Contador de no leídos
