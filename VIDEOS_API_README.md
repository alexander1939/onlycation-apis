# API de Validación de Videos de YouTube

## Descripción General

Esta API permite a los docentes validar videos de YouTube para su presentación personal en la plataforma. El sistema verifica que los videos cumplan con los requisitos establecidos antes de permitir su uso.

## Características Principales

- ✅ **Validación de título**: El video debe contener el nombre completo del docente
- ✅ **Control de duración**: Entre 30 segundos y 1 minuto (inclusive)
- ✅ **Verificación de restricciones**: Sin restricciones de edad o región
- ✅ **Validación de embebido**: El video debe ser embebible
- ✅ **Control de privacidad**: Solo videos públicos o no listados
- 🔒 **Autenticación requerida**: Solo usuarios autenticados pueden validar videos

## Endpoints Disponibles

### POST `/api/videos/validate/`

Valida un video de YouTube según los criterios establecidos.

**Headers requeridos:**
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**Request Body:**
```json
{
    "url_or_id": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response exitoso (200):**
```json
{
    "success": true,
    "message": "Video validado exitosamente",
    "data": {
        "video_id": "dQw4w9WgXcQ",
        "title": "Presentación del Profesor Juan Pérez",
        "thumbnails": {
            "default": {
                "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg",
                "width": 120,
                "height": 90
            },
            "medium": {
                "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
                "width": 320,
                "height": 180
            }
        },
        "duration_seconds": 45,
        "embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "privacy_status": "public",
        "embeddable": true,
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    }
}
```

**Response de error (400):**
```json
{
    "detail": "El título del video debe contener tu nombre completo: 'Juan Pérez'. Título actual: 'Mi Video de Presentación'"
}
```

## Reglas de Validación

### 1. Título del Video
- **Requisito**: Debe contener el nombre completo del docente (nombre + apellido)
- **Validación**: Insensible a mayúsculas/minúsculas y acentos
- **Ejemplo válido**: "Presentación del Profesor José María Pérez"
- **Ejemplo inválido**: "Mi Video de Presentación"

### 2. Duración
- **Rango permitido**: 30-60 segundos (inclusive)
- **Formato**: YouTube devuelve duración en formato ISO 8601 (ej: "PT1M30S")
- **Ejemplo válido**: 45 segundos
- **Ejemplo inválido**: 25 segundos o 65 segundos

### 3. Restricciones
- **Edad**: No debe tener restricciones de edad (`ytAgeRestricted = false`)
- **Región**: No debe tener restricciones de región (`regionRestriction = null`)
- **Embebido**: Debe permitir inserción (`embeddable = true`)

### 4. Privacidad
- **Estados permitidos**: `public` o `unlisted`
- **Estado rechazado**: `private`

## Formatos de URL Soportados

La API acepta múltiples formatos de URL de YouTube:

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- `VIDEO_ID` (ID directo de 11 caracteres)

## Configuración Requerida

### Variables de Entorno

Agregar en el archivo `.env`:

```env
YOUTUBE_API_KEY=tu_clave_api_de_youtube_aqui
```

### Obtener Clave de API de YouTube

1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Crear un nuevo proyecto o seleccionar uno existente
3. Habilitar YouTube Data API v3
4. Crear credenciales (API Key)
5. Copiar la clave al archivo `.env`

## Estructura de Archivos

```
app/
├── apis/
│   └── videos_api.py          # Endpoints de la API
├── schemas/
│   └── teachers/
│       └── video_schema.py    # Esquemas de request/response
├── services/
│   └── externals/
│       └── youtube_service.py # Lógica de validación
└── configs/
    └── settings.py            # Configuración de la API key
```

## Flujo de Uso

### 1. Frontend envía URL del video
```javascript
const response = await fetch('/api/videos/validate/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        url_or_id: 'https://youtube.com/watch?v=abc123'
    })
});
```

### 2. Backend valida el video
- Extrae ID del video desde la URL
- Consulta metadatos desde YouTube API
- Verifica todas las reglas de validación
- Retorna metadatos validados o mensaje de error

### 3. Frontend muestra resultado
- **Éxito**: Renderiza card con reproductor embebido
- **Error**: Muestra mensaje de error específico

## Ejemplos de Uso

### Validación Exitosa
```bash
curl -X POST "http://localhost:8000/api/videos/validate/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url_or_id": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### Video con Título Inválido
```bash
curl -X POST "http://localhost:8000/api/videos/validate/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url_or_id": "https://www.youtube.com/watch?v=invalid_title"}'
```

## Manejo de Errores

### Errores de Validación (400)
- Título no contiene nombre del docente
- Duración fuera del rango permitido
- Video tiene restricciones de edad/región
- Video no es embebible
- Video es privado

### Errores del Servidor (500)
- Problemas de conexión con YouTube API
- API key inválida o expirada
- Errores internos del sistema

## Consideraciones Técnicas

### Rate Limiting
- YouTube Data API v3 tiene límites de cuota
- Recomendado implementar cache para videos ya validados
- Monitorear uso de la API para evitar exceder límites

### Seguridad
- Solo usuarios autenticados pueden validar videos
- No se almacena contenido del video, solo metadatos
- Validación del lado del servidor para evitar bypass

### Performance
- Timeout de 10 segundos para consultas a YouTube API
- Respuesta asíncrona para no bloquear el servidor
- Cache de metadatos para videos recientemente validados

## Próximos Pasos

### Funcionalidades Pendientes
- [ ] Endpoint para guardar video validado en BD
- [ ] Listado de videos del usuario
- [ ] Cache de validaciones recientes
- [ ] Tests unitarios y de integración
- [ ] Monitoreo de uso de YouTube API

### Mejoras Futuras
- [ ] Validación de múltiples videos en lote
- [ ] Notificaciones cuando videos cambien de estado
- [ ] Dashboard de estadísticas de validación
- [ ] Integración con otras plataformas de video

## Soporte

Para dudas o problemas con la API de videos:

1. Revisar logs del servidor
2. Verificar configuración de `YOUTUBE_API_KEY`
3. Comprobar conectividad con YouTube API
4. Validar formato de JWT token

---

**Nota**: Esta API está diseñada para validar videos de presentación de docentes. No se recomienda para uso masivo o automatizado sin considerar los límites de la YouTube Data API v3.
