# Public Teacher Profile APIs

Esta guía documenta los endpoints PÚBLICOS relacionados con el perfil de un docente en OnlyCation: video, agenda/disponibilidad, comentarios (reseñas), catálogo y búsqueda pública. Todos los endpoints aquí listados son de acceso público (sin token) y están registrados en la app.

Base URL: depende de tu despliegue (ejemplo local)
- http://localhost:8000

Autenticación
- No requerida para estos endpoints (usan `public_access`).

Rutas y archivos relevantes
- `app/apis/public_videos_api.py`
- `app/apis/availability_api.py`
- `app/apis/assessment_api.py`
- `app/apis/teachers_public_api.py`
- Servicios: `app/services/teachers/teacher_agenda_service.py`, `app/services/teachers/teachers_public_service.py`

---

## 1) Video público del docente
GET /api/public/videos/teacher/{teacher_id}

Devuelve el video de presentación del docente.

Parámetros
- Path: `teacher_id` (int)

Respuesta (200)
- Objeto `VideoResponse` con:
  - `id`, `youtube_video_id`, `title`, `thumbnail_url`, `duration_seconds`, `embed_url`, `privacy_status`, `embeddable`, `original_url`, `created_at`, `updated_at`.

Ejemplo curl
```bash
curl -X GET \
  "http://localhost:8000/api/public/videos/teacher/2"
```

Errores
- 404 si no existe docente o no tiene video.

Lista pública de docentes con video:
GET /api/public/videos/teachers/with-videos

Respuesta (200)
```json
{
  "success": true,
  "message": "Profesores con videos obtenidos exitosamente",
  "data": [
    {
      "teacher_id": 2,
      "teacher_name": "Juan Pérez",
      "video": {
        "id": 1,
        "youtube_video_id": "kKh2c_YZKDI",
        "title": "Presentación - Juan Pérez",
        "thumbnail_url": "https://i.ytimg.com/vi/kKh2c_YZKDI/mqdefault.jpg",
        "duration_seconds": 43,
        "embed_url": "https://www.youtube.com/embed/kKh2c_YZKDI",
        "privacy_status": "public",
        "embeddable": true,
        "created_at": "2025-11-01T10:30:00"
      }
    }
  ],
  "total": 1
}
```

---

## 2) Agenda / Disponibilidad pública
GET /api/availability/docente/{teacher_id}/agenda/

Muestra slots por hora con estado disponible u ocupado para el rango solicitado.

Parámetros (query opcionales)
- `week`: YYYY-MM-DD (inicio de semana) → retorna lunes–domingo
- `start_date`: YYYY-MM-DD y `end_date`: YYYY-MM-DD → rango personalizado

Respuesta (200)
```json
{
  "success": true,
  "message": "Agenda pública del docente obtenida exitosamente",
  "data": {
    "teacher_id": 2,
    "teacher_name": "Juan Pérez",
    "week_start": "2025-11-17",
    "week_end": "2025-11-23",
    "days": [
      {
        "date": "2025-11-18",
        "day_name": "Martes",
        "slots": [
          { "start_time": "09:00", "end_time": "10:00", "status": "available", "availability_id": 101 },
          { "start_time": "10:00", "end_time": "11:00", "status": "occupied",  "availability_id": 102 }
        ],
        "total_slots": 13,
        "available_slots": 12,
        "occupied_slots": 1
      }
    ],
    "summary": {
      "total_days": 7,
      "days_with_availability": 5,
      "total_slots": 65,
      "available_slots": 60,
      "occupied_slots": 5
    }
  }
}
```

Ejemplos curl
```bash
# Semana actual
curl -G "http://localhost:8000/api/availability/docente/2/agenda/"

# Semana que incluye el 2025-11-18
curl -G "http://localhost:8000/api/availability/docente/2/agenda/" --data-urlencode "week=2025-11-18"

# Rango personalizado
curl -G "http://localhost:8000/api/availability/docente/2/agenda/" \
  --data-urlencode "start_date=2025-11-17" \
  --data-urlencode "end_date=2025-11-23"
```

Notas
- Slots por hora exacta (HH:MM).
- `status`: "available" o "occupied".

---

## 3) Comentarios (reseñas) públicos del docente
GET /api/assessments/public/comments/{teacher_id}

Parámetros
- Path: `teacher_id` (int)

Respuesta (200)
```json
{
  "success": true,
  "message": "Comentarios del docente 2 obtenidos correctamente (acceso público)",
  "data": [
    {
      "id": 10,
      "comment": "Excelente clase, muy claro.",
      "qualification": 5,
      "student_id": 9,
      "student_name": "Luis García",
      "created_at": "2025-11-05T09:35:00"
    }
  ]
}
```

Ejemplo curl
```bash
curl -X GET "http://localhost:8000/api/assessments/public/comments/2"
```

---

## 4) Catálogo público de docentes (incluye precio, nivel, materia, puntaje)
GET /api/public/teachers/

Parámetros (query opcionales)
- `min_bookings`: int mínimo de reservas
- `page`: int (default 1)
- `page_size`: int (default 10, máx 100)

Respuesta (200)
```json
{
  "success": true,
  "message": "Se encontraron 3 docente(s). Página 1 de 1",
  "data": [
    {
      "user_id": 2,
      "first_name": "Juan",
      "last_name": "Pérez",
      "educational_level": "Secundaria",
      "expertise_area": "Matemáticas",
      "price_per_hour": 250.0,
      "average_rating": 4.7,
      "video_embed_url": "https://www.youtube.com/embed/kKh2c_YZKDI",
      "video_thumbnail_url": "https://i.ytimg.com/vi/kKh2c_YZKDI/mqdefault.jpg",
      "total_bookings": 12
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

Ejemplos curl
```bash
curl -G "http://localhost:8000/api/public/teachers/"

curl -G "http://localhost:8000/api/public/teachers/" \
  --data-urlencode "min_bookings=5" \
  --data-urlencode "page=1" \
  --data-urlencode "page_size=12"
```

---

## 5) Búsqueda pública de docentes (mismos campos + filtros)
GET /api/public/search-teachers/

Parámetros (query opcionales)
- `name`: buscar en nombre o apellido
- `subject`: materia/área de especialidad
- `educational_level_id`: id de nivel educativo
- `min_price`, `max_price`
- `min_rating` (0–5)
- `page`, `page_size`

Respuesta (200)
```json
{
  "success": true,
  "message": "Se encontraron 1 docente(s). Página 1 de 1",
  "data": [
    {
      "user_id": 2,
      "first_name": "Juan",
      "last_name": "Pérez",
      "educational_level": "Secundaria",
      "expertise_area": "Matemáticas",
      "price_per_hour": 250.0,
      "average_rating": 4.7,
      "video_embed_url": "https://www.youtube.com/embed/kKh2c_YZKDI",
      "video_thumbnail_url": "https://i.ytimg.com/vi/kKh2c_YZKDI/mqdefault.jpg"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

Ejemplos curl
```bash
curl -G "http://localhost:8000/api/public/search-teachers/" \
  --data-urlencode "name=juan" \
  --data-urlencode "subject=matemáticas" \
  --data-urlencode "min_price=200" \
  --data-urlencode "max_price=300" \
  --data-urlencode "min_rating=4.5" \
  --data-urlencode "page=1" \
  --data-urlencode "page_size=10"
```

---

## 6) Perfil público del docente por ID (consolidado)
GET /api/public/teachers/{teacher_id}

Retorna el perfil público consolidado del docente: precio, nivel educativo, materia, puntaje promedio y datos del video.

Parámetros
- Path: `teacher_id` (int)

Respuesta (200)
```json
{
  "user_id": 2,
  "first_name": "Juan",
  "last_name": "Pérez",
  "educational_level": "Secundaria",
  "expertise_area": "Matemáticas",
  "description": "Docente con 5+ años de experiencia en matemáticas para secundaria.",
  "price_per_hour": 250.0,
  "average_rating": 4.7,
  "video_embed_url": "https://www.youtube.com/embed/kKh2c_YZKDI",
  "video_thumbnail_url": "https://i.ytimg.com/vi/kKh2c_YZKDI/mqdefault.jpg"
}
```

Ejemplo curl
```bash
curl -X GET "http://localhost:8000/api/public/teachers/2"
```

Errores
- 404 si no existe o no es un docente activo.
- 500 en caso de error interno.

---

## Campos clave (glosario rápido)
- `price_per_hour`: precio por hora del docente (MXN por defecto).
- `educational_level`: nivel educativo (texto, ej. "Primaria", "Secundaria").
- `expertise_area`: materia o área de especialidad (texto).
- `description`: descripción corta del docente (de `Document.description`).
- `average_rating`: promedio de estrellas (0.0–5.0, ej. 4.7).
- `video_embed_url` / `video_thumbnail_url`: datos públicos del video.
- Agenda → `status` del slot: `available` o `occupied`.

## Notas
- Estos endpoints son públicos y no requieren autenticación.
- La agenda genera slots por horas exactas y marca ocupados cuando existen reservas.
- El promedio de calificación y totales de bookings se calculan a partir de reservas/assessments.
