# Confirmations API (Alumno y Docente)

Este documento resume las APIs de confirmación para alumnos y docentes: qué hacen, qué reciben y qué responden, con ejemplos sencillos.

Asumimos que el router está registrado con el prefijo base:
- Base: `/api/confirm`

Todas las rutas requieren autenticación por token:
- Header: `Authorization: Bearer <TOKEN>`

Evidencias (archivos):
- Se envían como `multipart/form-data` (imagen `jpeg`/`png`).
- Tamaño máximo recomendado: 5 MB.

Ventanas de confirmación (tiempo permitido después de que termina la clase):
- Alumno: 2 horas
- Docente: 2 horas

En respuestas de historial verás:
- `booking_start`, `booking_end`: inicio/fin de la clase (UTC, ISO 8601)
- `window_status`: `open | expired`
- `confirmable_now`: `true | false`
- `seconds_left`: segundos restantes si la ventana está abierta
- `confirmed_by_student`, `confirmed_by_teacher`: fecha (ISO) o `null`

---

## Alumno

### 1) POST /student/{payment_booking_id}
Registra la confirmación del alumno con evidencia.

- Método: `POST`
- URL: `/api/confirm/student/{payment_booking_id}`
- Headers:
  - `Authorization: Bearer <TOKEN>`
  - `Accept: application/json`
- Content-Type: `multipart/form-data`
- Form fields:
  - `confirmation` (bool)
  - `description_student` (string)
  - `evidence_file` (file: imagen)

Ejemplo curl:
```bash
curl -X POST "https://tu-host/api/confirm/student/123" \
  -H "Authorization: Bearer TU_TOKEN" \
  -H "Accept: application/json" \
  -F "confirmation=true" \
  -F "description_student=Clase completada sin problemas" \
  -F "evidence_file=@/ruta/imagen.jpg;type=image/jpeg"
```

Respuesta 200 (JSON):
```json
{
  "success": true,
  "message": "Confirmación del estudiante registrada exitosamente",
  "data": {
    "id": 456,
    "teacher_id": 78,
    "student_id": 99,
    "payment_booking_id": 123,
    "confirmation_date_student": "2025-11-26T07:34:00Z",
    "description_student": "Clase completada sin problemas"
  }
}
```

Errores comunes: `400` (ventana expirada), `401` (token inválido), `404` (booking/pago no encontrado), `413/422` (archivo inválido), `500`.

---

### 2) GET /student/evidence/{confirmation_id}
Descarga la evidencia del alumno (desencriptada) como imagen.

- Método: `GET`
- URL: `/api/confirmation/student/evidence/{confirmation_id}`
- Headers: `Authorization: Bearer <TOKEN>`
- Acceso: Solo el alumno dueño de la confirmación puede descargar su evidencia.

Ejemplo curl:
```bash
curl -X GET "https://tu-host/api/confirmation/student/evidence/456" \
  -H "Authorization: Bearer TU_TOKEN" \
  -o evidencia.jpg
```

Respuesta: `200 image/jpeg` (o tipo real). Errores: `401/404/500`.

---

### 3) GET /student/history/recent
Devuelve SOLO confirmaciones actualmente confirmables (la clase ya terminó y la ventana de 2h sigue abierta). Ordenadas por fin de clase descendente (más recientes primero).

- Método: `GET`
- URL: `/api/confirm/student/history/recent`
- Headers: `Authorization: Bearer <TOKEN>`

Ejemplo curl:
```bash
curl -X GET "https://tu-host/api/confirm/student/history/recent" \
  -H "Authorization: Bearer TU_TOKEN"
```

Respuesta 200:
```json
{
  "success": true,
  "items": [
    {
      "id": 456,
      "teacher_id": 78,
      "student_id": 99,
      "payment_booking_id": 123,
      "booking_start": "2025-11-26T06:00:00Z",
      "booking_end": "2025-11-26T07:00:00Z",
      "confirmed_by_student": null,
      "confirmed_by_teacher": "2025-11-26T07:15:00Z",
      "window_status": "open",
      "confirmable_now": true,
      "seconds_left": 3599
    }
  ]
}
```

---

### 4) GET /student/history/all?offset=0&limit=10
Devuelve TODO el historial de confirmaciones del alumno paginado (offset/limit). Incluye metadatos `total` y `has_more`.

- Método: `GET`
- URL: `/api/confirm/student/history/all?offset=0&limit=10`
- Headers: `Authorization: Bearer <TOKEN>`
- Query params: `offset` (int, default 0), `limit` (int, default 10)

Ejemplo curl:
```bash
curl -X GET "https://tu-host/api/confirm/student/history/all?offset=0&limit=10" \
  -H "Authorization: Bearer TU_TOKEN"
```

Respuesta 200:
```json
{
  "success": true,
  "offset": 0,
  "limit": 10,
  "total": 23,
  "has_more": true,
  "items": [
    {
      "id": 456,
      "teacher_id": 78,
      "student_id": 99,
      "payment_booking_id": 123,
      "booking_start": "2025-11-26T06:00:00Z",
      "booking_end": "2025-11-26T07:00:00Z",
      "confirmed_by_student": "2025-11-26T07:10:00Z",
      "confirmed_by_teacher": "2025-11-26T07:05:00Z",
      "window_status": "expired",
      "confirmable_now": false,
      "seconds_left": 0
    }
  ]
}
```

---

## Docente

### 1) POST /teacher/{payment_booking_id}
Registra la confirmación del docente con evidencia.

- Método: `POST`
- URL: `/api/confirm/teacher/{payment_booking_id}`
- Headers:
  - `Authorization: Bearer <TOKEN>`
  - `Accept: application/json`
- Content-Type: `multipart/form-data`
- Form fields:
  - `confirmation` (bool)
  - `description_teacher` (string)
  - `evidence_file` (file: imagen)

Ejemplo curl:
```bash
curl -X POST "https://tu-host/api/confirm/teacher/123" \
  -H "Authorization: Bearer TU_TOKEN" \
  -H "Accept: application/json" \
  -F "confirmation=true" \
  -F "description_teacher=Clase impartida correctamente" \
  -F "evidence_file=@/ruta/imagen.jpg;type=image/jpeg"
```

Respuesta 200 (JSON):
```json
{
  "success": true,
  "message": "Confirmación del docente registrada exitosamente",
  "data": {
    "id": 789,
    "teacher_id": 78,
    "student_id": 99,
    "payment_booking_id": 123,
    "confirmation_date_teacher": "2025-11-26T07:20:00Z",
    "evidence_teacher": "evidence/teacher/...",
    "description_teacher": "Clase impartida correctamente"
  }
}
```

---

### 2) GET /teacher/evidence/{confirmation_id}
Descarga la evidencia del docente como imagen.

- Método: `GET`
- URL: `/api/confirmation/teacher/evidence/{confirmation_id}`
- Headers: `Authorization: Bearer <TOKEN>`
- Acceso: Solo el docente dueño de la confirmación puede descargar su evidencia.

Ejemplo curl:
```bash
curl -X GET "https://tu-host/api/confirmation/teacher/evidence/789" \
  -H "Authorization: Bearer TU_TOKEN" \
  -o evidencia_docente.jpg
```

---

### 3) GET /teacher/history/recent
Devuelve SOLO confirmaciones confirmables ahora (clase terminó y ventana abierta). Ordenadas por fin de clase (desc). La ventana actual del docente es de 2 horas.

- Método: `GET`
- URL: `/api/confirm/teacher/history/recent`
- Headers: `Authorization: Bearer <TOKEN>`

Ejemplo curl:
```bash
curl -X GET "https://tu-host/api/confirm/teacher/history/recent" \
  -H "Authorization: Bearer TU_TOKEN"
```

Respuesta 200:
```json
{
  "success": true,
  "items": [
    {
      "id": 789,
      "teacher_id": 78,
      "student_id": 99,
      "payment_booking_id": 123,
      "booking_start": "2025-11-26T06:00:00Z",
      "booking_end": "2025-11-26T07:00:00Z",
      "confirmed_by_student": "2025-11-26T07:10:00Z",
      "confirmed_by_teacher": null,
      "window_status": "open",
      "confirmable_now": true,
      "seconds_left": 7199
    }
  ]
}
```

---

### 4) GET /teacher/history/all?offset=0&limit=10
Devuelve TODO el historial de confirmaciones del docente paginado.

- Método: `GET`
- URL: `/api/confirm/teacher/history/all?offset=0&limit=10`
- Headers: `Authorization: Bearer <TOKEN>`

Ejemplo curl:
```bash
curl -X GET "https://tu-host/api/confirm/teacher/history/all?offset=0&limit=10" \
  -H "Authorization: Bearer TU_TOKEN"
```

Respuesta 200:
```json
{
  "success": true,
  "offset": 0,
  "limit": 10,
  "total": 14,
  "has_more": false,
  "items": [
    {
      "id": 789,
      "teacher_id": 78,
      "student_id": 99,
      "payment_booking_id": 123,
      "booking_start": "2025-11-26T06:00:00Z",
      "booking_end": "2025-11-26T07:00:00Z",
      "confirmed_by_student": "2025-11-26T07:10:00Z",
      "confirmed_by_teacher": "2025-11-26T07:20:00Z",
      "window_status": "expired",
      "confirmable_now": false,
      "seconds_left": 0
    }
  ]
}
```

---

## Evidencia unificada (Docente o Alumno)

### GET /evidence/{confirmation_id}
Devuelve la evidencia correspondiente al usuario autenticado:
- Si el viewer es el docente dueño, retorna la evidencia del docente.
- Si el viewer es el alumno dueño, retorna la evidencia del alumno.
- En otro caso, `403 Forbidden`.

- Método: `GET`
- URL: `/api/confirmation/evidence/{confirmation_id}`
- Headers: `Authorization: Bearer <TOKEN>`
- Query: `download` (bool, opcional). Si es `true`, fuerza descarga (`attachment`). Por defecto `inline`.

Ejemplos curl:
```bash
# Ver en navegador (inline)
curl -X GET "https://tu-host/api/confirmation/evidence/789" \
  -H "Authorization: Bearer TU_TOKEN"

# Forzar descarga
curl -X GET "https://tu-host/api/confirmation/evidence/789?download=true" \
  -H "Authorization: Bearer TU_TOKEN" \
  -o evidencia.jpg
```

Posibles errores:
- `401`: token inválido/ausente
- `403`: no eres docente/alumno dueño de la confirmación
- `404`: confirmación o evidencia no encontrada
- `500`: error al desencriptar

---

## Detalle de confirmación (Docente/Alumno)

### GET /detail/{confirmation_id}
Devuelve el detalle de una confirmación específica. Solo puede acceder el docente o el alumno dueño de la confirmación.

- Método: `GET`
- URL: `/api/confirm/detail/{confirmation_id}`
- Headers: `Authorization: Bearer <TOKEN>`

Ejemplo curl:
```bash
curl -X GET "https://tu-host/api/confirm/detail/789" \
  -H "Authorization: Bearer TU_TOKEN"
```

Respuesta 200:
```json
{
  "success": true,
  "data": {
    "id": 789,
    "teacher_id": 78,
    "student_id": 99,
    "payment_booking_id": 123,
    "booking_start": "2025-11-26T06:00:00Z",
    "booking_end": "2025-11-26T07:00:00Z",
    "confirmed_by_student": "2025-11-26T07:10:00Z",
    "confirmed_by_teacher": null,
    "evidence_student": "evidence/student/...",
    "evidence_teacher": "evidence/teacher/...",
    "description_student": "Clase completada sin problemas",
    "description_teacher": "Clase impartida correctamente"
  }
}
```

Errores:
- `401`: token inválido/ausente
- `403`: no tienes acceso a esta confirmación (ni docente ni alumno dueño)
- `404`: confirmación no encontrada

---

## Códigos de estado y errores comunes
- `200 OK`: Operación exitosa.
- `400 Bad Request`: ventana de confirmación expirada u otros errores de validación.
- `401 Unauthorized`: token inválido/ausente.
- `404 Not Found`: booking, pago, evidencia o confirmación inexistente.
- `413/422`: archivo muy grande o inválido.
- `500 Internal Server Error`: error no controlado.

---

## Notas
- Los endpoints `recent` solo retornan ítems confirmables en este momento.
- Los endpoints `all` usan paginación por `offset/limit` y devuelven `total` y `has_more`.
- El endpoint `/detail/{confirmation_id}` solo devuelve metadatos (incluye nombres de archivo). Para obtener el archivo real usa `/teacher/evidence/{id}`, `/student/evidence/{id}` o el unificado `/evidence/{id}`.
