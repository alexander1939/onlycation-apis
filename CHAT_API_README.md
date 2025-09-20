# 🗨️ **API de Chat - Sistema de Comunicación Privada**

## 📋 **Descripción General**

El sistema de chat permite a los **estudiantes** y **profesores** comunicarse de forma privada y segura. Los estudiantes pueden crear chats con profesores que hayan contratado, y ambos pueden intercambiar mensajes, bloquear conversaciones y gestionar su historial de mensajes.

## 🏗️ **Arquitectura del Sistema**

### **Modelos de Base de Datos**

- **`Chat`**: Representa una conversación entre un estudiante y un profesor
- **`Message`**: Representa un mensaje individual dentro de un chat

### **Características Principales**

- ✅ **Chats privados** entre estudiantes y profesores
- ✅ **Sistema de bloqueo** para gestionar conversaciones no deseadas
- ✅ **Mensajes con estado** (leído/no leído, eliminado)
- ✅ **Paginación** para historial de mensajes
- ✅ **Contadores de mensajes no leídos**
- ✅ **Soft delete** para mensajes (no se eliminan permanentemente)

## 🔐 **Autenticación y Autorización**

- **JWT Token** requerido en el header `Authorization: Bearer <token>`
- **Estudiantes** pueden crear chats con profesores
- **Ambos roles** pueden enviar mensajes y gestionar sus chats
- **Solo propietarios** pueden bloquear/desbloquear chats

## 📡 **Endpoints Disponibles**

### **1. Gestión de Chats**

#### **POST** `/api/chat/chats/create`
Crea un nuevo chat entre un estudiante y un profesor.

**Solo estudiantes pueden crear chats.**

```json
{
  "teacher_id": 123
}
```

**Respuesta exitosa:**
```json
{
  "id": 1,
  "student_id": 456,
  "teacher_id": 123,
  "is_active": true,
  "is_blocked": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### **GET** `/api/chat/chats/my`
Obtiene todos los chats del usuario autenticado con resúmenes.

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "Se encontraron 2 chat(s) en tu cuenta",
  "data": [
    {
      "chat_id": 1,
      "student_id": 456,
      "teacher_id": 123,
      "last_message": {
        "id": 15,
        "content": "¿Cuándo podemos programar la próxima clase?",
        "sender_id": 456,
        "created_at": "2024-01-15T14:30:00Z"
      },
      "unread_count": 2,
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T14:30:00Z"
    }
  ],
  "total": 2
}
```

#### **POST** `/api/chat/chats/{chat_id}/block`
Bloquea un chat (solo el propietario puede hacerlo).

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "✅ Chat bloqueado exitosamente",
  "data": {
    "id": 1,
    "is_blocked": true
  }
}
```

#### **POST** `/api/chat/chats/{chat_id}/unblock`
Desbloquea un chat (solo el propietario puede hacerlo).

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "✅ Chat desbloqueado exitosamente",
  "data": {
    "id": 1,
    "is_blocked": false
  }
}
```

### **2. Gestión de Mensajes**

#### **POST** `/api/chat/messages/send`
Envía un nuevo mensaje en un chat.

```json
{
  "chat_id": 1,
  "content": "Hola, ¿cómo estás? ¿Podemos programar una clase para mañana?"
}
```

**Respuesta exitosa:**
```json
{
  "id": 16,
  "chat_id": 1,
  "sender_id": 456,
  "content": "Hola, ¿cómo estás? ¿Podemos programar una clase para mañana?",
  "is_read": false,
  "is_deleted": false,
  "created_at": "2024-01-15T15:00:00Z",
  "updated_at": "2024-01-15T15:00:00Z"
}
```

#### **GET** `/api/chat/messages/{chat_id}`
Obtiene los mensajes de un chat con paginación.

**Parámetros de query:**
- `limit`: Número máximo de mensajes (1-100, por defecto 50)
- `offset`: Número de mensajes a omitir (por defecto 0)

**Ejemplo:** `/api/chat/messages/1?limit=20&offset=0`

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "Se encontraron 20 mensaje(s) en el chat",
  "data": [
    {
      "id": 16,
      "content": "Hola, ¿cómo estás?",
      "sender_id": 456,
      "is_read": true,
      "created_at": "2024-01-15T15:00:00Z"
    }
  ],
  "total": 20,
  "chat_id": 1
}
```

#### **POST** `/api/chat/messages/mark-read`
Marca mensajes como leídos.

```json
{
  "message_ids": [16, 17, 18]
}
```

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "✅ 3 mensaje(s) marcado(s) como leído(s)",
  "data": {
    "marked_count": 3
  }
}
```

#### **DELETE** `/api/chat/messages/{message_id}`
Elimina un mensaje (soft delete - solo el remitente puede hacerlo).

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "✅ Mensaje eliminado exitosamente",
  "data": {
    "deleted": true
  }
}
```

#### **GET** `/api/chat/messages/{chat_id}/unread-count`
Obtiene el número de mensajes no leídos en un chat.

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "Tienes 5 mensaje(s) no leído(s)",
  "data": {
    "unread_count": 5
  }
}
```

## 🚨 **Códigos de Error Comunes**

### **400 Bad Request**
- `❌ Ya existe un chat activo entre el estudiante X y el profesor Y`
- `❌ No puedes crear un chat contigo mismo`
- `❌ Chat no encontrado`
- `❌ Este chat no está activo`
- `❌ Este chat está bloqueado`
- `❌ No eres participante de este chat`

### **403 Forbidden**
- `❌ Solo los estudiantes pueden crear chats con profesores`
- `❌ No tienes permisos para bloquear este chat`

### **500 Internal Server Error**
- `❌ Error interno al crear el chat. Por favor, intenta nuevamente.`
- `❌ Error interno al enviar el mensaje. Por favor, intenta nuevamente.`

## 💡 **Casos de Uso Típicos**

### **Para Estudiantes:**
1. **Crear chat** con un profesor contratado
2. **Enviar mensajes** para consultas sobre clases
3. **Recibir notificaciones** de respuestas del profesor
4. **Bloquear chat** si hay problemas de comunicación

### **Para Profesores:**
1. **Recibir mensajes** de estudiantes contratados
2. **Responder consultas** sobre horarios y contenido
3. **Gestionar múltiples chats** con diferentes estudiantes
4. **Mantener historial** de conversaciones

## 🔄 **Flujo de Conversación Típico**

1. **Estudiante** crea chat con profesor → `POST /api/chat/chats/create`
2. **Estudiante** envía primer mensaje → `POST /api/chat/messages/send`
3. **Profesor** recibe notificación y responde → `POST /api/chat/messages/send`
4. **Ambos** pueden ver historial → `GET /api/chat/messages/{chat_id}`
5. **Mensajes** se marcan como leídos automáticamente o manualmente
6. **Chat** se puede bloquear si es necesario → `POST /api/chat/chats/{chat_id}/block`

## 🛡️ **Seguridad y Privacidad**

- **Autenticación JWT** requerida para todas las operaciones
- **Verificación de participación** en chat antes de acceder a mensajes
- **Soft delete** para mensajes (no se eliminan permanentemente)
- **Solo propietarios** pueden bloquear/desbloquear chats
- **Validación de roles** para operaciones específicas

## 📱 **Integración con Frontend**

### **Notificaciones en Tiempo Real:**
- **Contador de mensajes no leídos** en tiempo real
- **Actualización automática** de chats activos
- **Indicadores visuales** para mensajes nuevos

### **Gestión de Estado:**
- **Lista de chats** con resúmenes
- **Historial de mensajes** con paginación
- **Estado de mensajes** (enviado, entregado, leído)

## 🚀 **Próximas Funcionalidades**

- [ ] **WebSockets** para mensajes en tiempo real
- [ ] **Notificaciones push** para mensajes nuevos
- [ ] **Archivos adjuntos** en mensajes
- [ ] **Búsqueda** en historial de mensajes
- [ ] **Grupos de chat** para clases múltiples
- [ ] **Encuestas** y feedback en chat

---

## 📞 **Soporte y Contacto**

Para dudas sobre la implementación o reportar problemas:
- **Desarrollador:** Equipo de Desarrollo
- **Documentación:** Este archivo
- **API Base:** `http://localhost:8000/api/chat`
